/**
 * The Users page (pages/Members.vue) goes through lms.lms.api.get_members
 * rather than a list resource, so its search and paging correctness is its
 * own: the term has to reach the server, the offset has to go back to zero,
 * and a response has to be dropped once the query it was issued for is gone.
 *
 * The mock resolves reload() from a queue the test controls, so two requests
 * can be held open at once and landed in either order.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'

const { paramsSeen, pending, routeState } = vi.hoisted(() => ({
	paramsSeen: [] as any[],
	pending: [] as Array<(rows: any[]) => void>,
	routeState: { query: {} as Record<string, string> },
}))

vi.mock('frappe-ui', () => ({
	call: vi.fn(() => Promise.resolve()),
	// reload() returns the rows, because Members awaits it and token-checks the
	// result. A mock that returned undefined would make every paging assertion
	// below pass without the component ever appending anything.
	createResource: (options: any) => ({
		loading: false,
		reload: () => {
			paramsSeen.push(options.makeParams())
			return new Promise((resolve) => pending.push(resolve as any))
		},
		submit: vi.fn(),
	}),
	toast: { success: vi.fn(), error: vi.fn() },
	usePageMeta: vi.fn(),
	Dialog: { template: '<div />' },
	Select: { template: '<select />' },
	Avatar: { template: '<div />' },
	Badge: { template: '<div><slot /></div>' },
	Button: { template: '<button><slot /></button>' },
	Dropdown: { template: '<div><slot /></div>' },
}))

vi.mock('frappe-ui/frappe', () => ({
	useOnboarding: () => ({ updateOnboardingStep: vi.fn() }),
	useTelemetry: () => ({ capture: vi.fn() }),
}))

vi.mock('vue-router', () => ({
	useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
	useRoute: () => routeState,
}))

vi.mock('@/stores/session', () => ({ sessionStore: () => ({ brand: {} }) }))

vi.mock('@/utils', () => ({
	cleanError: (e: unknown) => e,
}))

vi.stubGlobal('__', (text: string) => text)

// frappe's translation layer patches String.prototype.format onto the page at
// runtime; the toasts and dialog text these components build rely on it.
;(String.prototype as any).format = function (this: string, ...args: unknown[]): string {
	return this.replace(/{(\d+)}/g, (_match, index) => String(args[Number(index)]))
}

import { call } from 'frappe-ui'
import Members from '@/pages/Members.vue'

// Matches MEMBERS_PAGE_LENGTH in lms/lms/api.py (and the same-named constant
// in Members.vue), which pages `start` by this.
const MEMBERS_PAGE_LENGTH = 13

const rows = (count: number, prefix = 'user') =>
	Array.from({ length: count }, (_, i) => ({ name: `${prefix}${i}@x.com` }))

/** Lands the oldest outstanding request with `data`. */
const land = async (data: any[]) => {
	pending.shift()?.(data)
	await flushPromises()
}

const mountMembers = () =>
	shallowMount(Members, {
		global: {
			// The page now gates itself on mount (a real route needs its own
			// refusal, unlike the old settings-dialog panel no URL could reach) —
			// without is_moderator here every fetch below would be skipped.
			provide: { $user: { data: { is_moderator: true } } },
			mocks: { __: (text: string) => text },
		},
	})

describe('Users page search', () => {
	beforeEach(() => {
		paramsSeen.length = 0
		pending.length = 0
		routeState.query = {}
		vi.mocked(call).mockReset()
		vi.mocked(call).mockResolvedValue(undefined)
	})

	it('fetches the first page on mount', () => {
		mountMembers()

		expect(paramsSeen.at(-1)).toMatchObject({ start: 0, search: '' })
	})

	it('sends the term to the server', async () => {
		const vm = mountMembers().vm as any

		vm.search = 'ada'
		await flushPromises()

		expect(paramsSeen.at(-1)).toMatchObject({ search: 'ada', start: 0 })
	})

	it('restarts at the first page when searching after Load More', async () => {
		const vm = mountMembers().vm as any
		await land(rows(MEMBERS_PAGE_LENGTH))
		expect(vm.start).toBe(MEMBERS_PAGE_LENGTH)

		vm.search = 'ada'
		await flushPromises()

		expect(paramsSeen.at(-1).start).toBe(0)
	})

	it('drops the rows it had before re-querying', async () => {
		const vm = mountMembers().vm as any
		await land(rows(3))
		expect(vm.memberList).toHaveLength(3)

		vm.search = 'ada'
		await flushPromises()

		expect(vm.memberList).toEqual([])
	})

	// The SettingsList-specific column-width regression this used to guard
	// against (a `width: 'auto'` header drifting from its row in a shared CSS
	// grid) does not apply here: ListPage's columns take numeric widths and
	// render through ResponsiveListView, a different mechanism, already
	// exercised by other ListPage-based pages' own tests.

	it('offers Load More only on a full page', async () => {
		const vm = mountMembers().vm as any

		await land(rows(MEMBERS_PAGE_LENGTH - 1))

		expect(vm.hasNextPage).toBe(false)
	})

	// Load More vanished from Users when the server paged at a different size
	// than the client constant: an exact-equality check reads a full page as a
	// last page. A full page is a full page whatever its size.
	it('keeps Load More when the server pages larger than the constant', async () => {
		const vm = mountMembers().vm as any

		await land(rows(MEMBERS_PAGE_LENGTH + 7))

		expect(vm.hasNextPage).toBe(true)
	})

	it('pages by the rows returned, not by the constant', async () => {
		const vm = mountMembers().vm as any

		await land(rows(MEMBERS_PAGE_LENGTH + 7))

		expect(vm.start).toBe(MEMBERS_PAGE_LENGTH + 7)
	})

	it('appends the next page onto the rows already shown', async () => {
		const vm = mountMembers().vm as any
		await land(rows(MEMBERS_PAGE_LENGTH, 'first'))

		vm.fetchMembers()
		await land(rows(4, 'second'))

		expect(vm.memberList).toHaveLength(MEMBERS_PAGE_LENGTH + 4)
		expect(vm.start).toBe(MEMBERS_PAGE_LENGTH + 4)
	})

	// createResource aborts nothing and carries no sequence number, so both
	// responses to a mid-flight filter change used to resolve and both append:
	// one filter's page under another's, with `start` advanced past rows nobody
	// ever saw.
	it('drops a response whose query has already been replaced', async () => {
		const vm = mountMembers().vm as any
		await land(rows(3, 'initial'))

		vm.currentRole = 'Moderator'
		await flushPromises()
		vm.currentRole = 'Course Creator'
		await flushPromises()

		// The Moderator page lands after the Instructor query was issued.
		await land(rows(MEMBERS_PAGE_LENGTH, 'moderator'))
		await land(rows(2, 'instructor'))

		expect(vm.memberList).toHaveLength(2)
		expect(
			vm.memberList.every((m: any) => m.name.startsWith('instructor'))
		).toBe(true)
		expect(vm.start).toBe(2)
	})

	describe('tags', () => {
		it('sends no tag filter by default', () => {
			mountMembers()

			expect(paramsSeen.at(-1).tag).toBeUndefined()
		})

		it('sends the chosen tag to the server, starting over at the first page', async () => {
			const vm = mountMembers().vm as any
			await land(rows(MEMBERS_PAGE_LENGTH))

			vm.currentTag = 'Beasiswa'
			await flushPromises()

			expect(paramsSeen.at(-1)).toMatchObject({ tag: 'Beasiswa', start: 0 })
		})

		it('starts on the tag named in the address', () => {
			routeState.query = { tag: 'Tritunggal' }

			mountMembers()

			expect(paramsSeen.at(-1)).toMatchObject({ tag: 'Tritunggal' })
		})

		it('loads the tag list for the filter without touching the member paging', async () => {
			vi.mocked(call).mockResolvedValue([{ tag: 'Beasiswa', count: 2 }])
			const vm = mountMembers().vm as any
			await flushPromises()

			expect(call).toHaveBeenCalledWith('lms.lms.api.get_member_tags')
			expect(vm.tagFilterOptions.map((o: any) => o.value)).toEqual(['All', 'Beasiswa'])
			// only the member fetch is waiting on the queue
			expect(pending).toHaveLength(1)
		})

		it('keeps an active filter selectable even when its tag is not in the list', () => {
			routeState.query = { tag: 'Gone' }

			const vm = mountMembers().vm as any

			expect(vm.tagFilterOptions.map((o: any) => o.value)).toContain('Gone')
		})

		it('sends the selected members and the tag for a bulk add, then clears the selection', async () => {
			const vm = mountMembers().vm as any
			await land(rows(2))
			const unselectAll = vi.fn()
			vi.mocked(call).mockResolvedValue({ tag: 'Beasiswa', updated: 2, total: 2 })

			vm.openBulkTag('add', new Set(['user0@x.com', 'user1@x.com']), unselectAll)
			const change = vm.confirmBulkTag('Beasiswa')
			await flushPromises()

			expect(call).toHaveBeenCalledWith('lms.lms.api.bulk_add_member_tag', {
				members: ['user0@x.com', 'user1@x.com'],
				tag: 'Beasiswa',
			})
			expect(unselectAll).toHaveBeenCalled()
			await land([])
			await change
		})

		it('leaves out selected members that are no longer on screen', async () => {
			const vm = mountMembers().vm as any
			await land(rows(2))
			vi.mocked(call).mockResolvedValue({ tag: 'Beasiswa', updated: 1, total: 1 })

			// user9 was ticked under an earlier filter and is no longer listed
			vm.openBulkTag('add', new Set(['user0@x.com', 'user9@x.com']), vi.fn())
			const change = vm.confirmBulkTag('Beasiswa')
			await flushPromises()

			expect(call).toHaveBeenCalledWith('lms.lms.api.bulk_add_member_tag', {
				members: ['user0@x.com'],
				tag: 'Beasiswa',
			})
			await land([])
			await change
		})

		it('uses the remove endpoint in remove mode', async () => {
			const vm = mountMembers().vm as any
			await land(rows(1))
			vi.mocked(call).mockResolvedValue({ tag: 'Alumni', updated: 1, total: 1 })

			vm.openBulkTag('remove', new Set(['user0@x.com']), vi.fn())
			const change = vm.confirmBulkTag('Alumni')
			await flushPromises()

			expect(call).toHaveBeenCalledWith('lms.lms.api.bulk_remove_member_tag', {
				members: ['user0@x.com'],
				tag: 'Alumni',
			})
			await land([])
			await change
		})
	})
})
