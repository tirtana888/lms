import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import {
	createMemoryHistory,
	createRouter,
	RouterView,
	type Router,
} from 'vue-router'
import { defineComponent, h, reactive } from 'vue'

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)

// frappe's translation layer patches String.prototype.format onto the page at
// runtime; the toasts and dialog text these components build rely on it.
;(String.prototype as any).format = function (this: string, ...args: unknown[]): string {
	return this.replace(/{(\d+)}/g, (_match, index) => String(args[Number(index)]))
}

// frappe-ui's ESM build doesn't resolve under vitest (see chapterForm.test.ts),
// so every export the page reaches for is stubbed by hand.
const { callMock, createResourceMock, toastMock } = vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return {
		callMock: vi.fn(),
		createResourceMock: vi.fn(),
		toastMock: { success: vi.fn(), error: vi.fn() },
	}
})

vi.mock('@/components/HeaderButton.vue', () => ({
	default: {
		inheritAttrs: false,
		template: `<button v-bind="$attrs" />`,
	},
}))

// Study time has its own data source and tests (memberStudyTime.test.ts); here it would
// only compete for the shared createResource mock below.
vi.mock('@/components/MemberStudyTime.vue', () => ({
	default: { template: `<div data-testid="member-study-time" />` },
}))

vi.mock('frappe-ui', () => ({
	call: callMock,
	createResource: createResourceMock,
	toast: toastMock,
	Avatar: { props: ['image', 'label', 'size'], template: `<div />` },
	Badge: { template: `<span><slot /></span>` },
	// MemberDetail wraps hidden-badge overflow in a Tooltip; without a stub every
	// render past the header throws "No Tooltip export is defined".
	Tooltip: { props: ['text'], template: `<span><slot /></span>` },
	Breadcrumbs: { props: ['items'], template: `<nav><slot /></nav>` },
	Button: {
		props: ['variant', 'label', 'loading', 'theme'],
		emits: ['click'],
		template: `<button :disabled="loading" @click="$emit('click')"><slot name="prefix" /><slot name="suffix" />{{ label }}<slot /></button>`,
	},
	// Flattened, not a real popover: renders every option as its own button so
	// a test can click one directly, the same simplification TabButtons below
	// already makes for its own options.
	Dropdown: {
		props: ['options', 'placement'],
		template: `
			<div>
				<slot />
				<button
					v-for="opt in options"
					:key="opt.label"
					:data-testid="'menu-' + opt.label"
					@click="opt.onClick && opt.onClick()"
				>{{ opt.label }}</button>
			</div>
		`,
	},
	FormControl: {
		props: ['modelValue', 'type', 'placeholder', 'label'],
		emits: ['update:modelValue'],
		template: `<input :data-testid="'field-' + (placeholder || label)" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" @keyup.enter="$emit('keyup-enter')" />`,
	},
	TabButtons: {
		props: ['options', 'modelValue'],
		emits: ['update:modelValue'],
		template: `
			<div>
				<button
					v-for="opt in options"
					:key="opt.value"
					:data-testid="'tab-' + opt.value"
					@click="$emit('update:modelValue', opt.value)"
				>{{ opt.label }}</button>
			</div>
		`,
	},
}))

vi.mock('@/components/Controls/BooleanSwitch.vue', () => ({
	default: {
		props: ['modelValue', 'label', 'size'],
		emits: ['update:modelValue'],
		template: `<button :data-testid="'role-' + label" :data-on="String(modelValue)" @click="$emit('update:modelValue', !modelValue)">{{ label }}</button>`,
	},
}))

import MemberDetail from '@/pages/MemberDetail.vue'
// The REAL route table, not a copy: a reimplemented table would only prove
// that vue-router matches what you tell it to match.
import { routes } from '@/routes'

const MEMBER = 'jane@doe.com'

// One shared resource per mount, standing in for whichever createResource call
// is issued next: get_member and get_member_overview both go through this, so
// each test tells them apart by the params it was called with.
const lookup = reactive({
	data: null as Record<string, unknown> | null,
	loading: false,
	fetch: vi.fn(),
})
const overview = reactive({
	data: null as Record<string, unknown> | null,
	loading: false,
	fetch: vi.fn(),
})
createResourceMock.mockImplementation((options: { url: string }) =>
	options.url === 'lms.lms.api.get_member_overview' ? overview : lookup
)

const moderator = { name: 'mod@example.com', is_moderator: true }
const outsider = { name: 'someone@example.com' }

const makeRouter = (): Router =>
	createRouter({
		history: createMemoryHistory(),
		routes: [
			{
				path: '/users',
				name: 'Members',
				component: { template: '<div>MEMBERS</div>' },
			},
			{ path: '/users/:memberID', name: 'MemberForm', component: MemberDetail, props: true },
		],
	})

const mountDetail = async (
	router: Router,
	user: Record<string, unknown> | null = moderator
) => {
	const wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
		global: {
			plugins: [router],
			provide: { $user: { data: user } },
			mocks: { __: (text: string) => text },
		},
	})
	await flushPromises()
	return wrapper
}

const overviewPane = (wrapper: ReturnType<typeof mount>) =>
	wrapper.find('[data-testid="member-overview"]')

const rolesPane = (wrapper: ReturnType<typeof mount>) =>
	wrapper.find('[data-testid="member-roles"]')

const save = (wrapper: ReturnType<typeof mount>) =>
	wrapper.find('[data-testid="member-save"]')

describe('the member detail page', () => {
	beforeEach(() => {
		lookup.data = null
		lookup.fetch.mockClear()
		overview.data = null
		overview.fetch.mockClear()
		callMock.mockReset()
		toastMock.success.mockClear()
		toastMock.error.mockClear()
	})

	describe('route grammar', () => {
		it('is a top-level page, not nested under Members', () => {
			const router = createRouter({ history: createMemoryHistory(), routes })

			const resolved = router.resolve(`/users/${MEMBER}`)
			expect(resolved.name).toBe('MemberForm')
			expect(resolved.params.memberID).toBe(MEMBER)
			// A page, not an overlay: its own matched record, not a child of Members'.
			expect(resolved.matched).toHaveLength(1)
		})

		it('points that route at MemberDetail', async () => {
			type LazyRecord = { name?: unknown; component?: () => Promise<unknown> }
			const record = (routes as LazyRecord[]).find(
				(route) => route.name === 'MemberForm'
			)
			expect(record?.component).toBeTypeOf('function')
			await expect(record!.component!()).resolves.toMatchObject({
				default: MemberDetail,
			})
		})
	})

	describe('the permission gate', () => {
		it('refuses a non-moderator', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			const wrapper = await mountDetail(router, outsider)

			expect(overviewPane(wrapper).exists()).toBe(false)
			expect(wrapper.text()).toContain('You are not permitted to manage members.')
			expect(lookup.fetch).not.toHaveBeenCalled()
		})

		it('refuses a signed-out visitor', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			const wrapper = await mountDetail(router, null)

			expect(overviewPane(wrapper).exists()).toBe(false)
			expect(lookup.fetch).not.toHaveBeenCalled()
		})

		it('fetches the member for a moderator', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			await mountDetail(router)

			expect(lookup.fetch).toHaveBeenCalled()
			expect(createResourceMock.mock.calls[0][0].url).toBe('lms.lms.api.get_member')
			expect(createResourceMock.mock.calls[0][0].makeParams()).toEqual({
				member: MEMBER,
			})
		})
	})

	describe('which tab it opens onto', () => {
		it('defaults to Overview, and fetches it immediately', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			const wrapper = await mountDetail(router)

			// Not overviewPane specifically: all six non-Roles tabs share one
			// loading state, so which one resolves is unknown until the fetch
			// this assertion is itself confirming has even happened.
			expect(wrapper.find('[data-testid="member-tab-panel"]').exists()).toBe(true)
			expect(rolesPane(wrapper).exists()).toBe(false)
			expect(overview.fetch).toHaveBeenCalled()
		})

		it('opens onto Roles when the query says so, and does not fetch Overview yet', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}?tab=Roles`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			const wrapper = await mountDetail(router)

			expect(rolesPane(wrapper).exists()).toBe(true)
			expect(overviewPane(wrapper).exists()).toBe(false)
			expect(overview.fetch).not.toHaveBeenCalled()
		})
	})

	describe('editing roles', () => {
		it('seeds the switches from the fetched roles and disables Save until they land', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}?tab=Roles`)
			const wrapper = await mountDetail(router)

			expect(save(wrapper).attributes('disabled')).toBeDefined()

			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: ['LMS Student', 'Moderator'] }
			await flushPromises()

			expect(save(wrapper).attributes('disabled')).toBeUndefined()
			expect(wrapper.find('[data-testid="role-Student"]').attributes('data-on')).toBe(
				'true'
			)
			expect(wrapper.find('[data-testid="role-Moderator"]').attributes('data-on')).toBe(
				'true'
			)
			expect(
				wrapper.find('[data-testid="role-Course Creator"]').attributes('data-on')
			).toBe('false')
		})

		it('saves only the roles that actually changed', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}?tab=Roles`)
			const wrapper = await mountDetail(router)

			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: ['LMS Student'] }
			await flushPromises()

			await wrapper.find('[data-testid="role-Moderator"]').trigger('click')
			callMock.mockResolvedValue(true)
			await save(wrapper).trigger('click')
			await flushPromises()

			expect(callMock).toHaveBeenCalledTimes(1)
			expect(callMock).toHaveBeenCalledWith('lms.lms.api.save_role', {
				user: MEMBER,
				role: 'Moderator',
				value: 1,
			})
			expect(toastMock.success).toHaveBeenCalled()
			// Stays on the page — this is a real page now, not a modal that
			// dismisses itself on save.
			expect(router.currentRoute.value.name).toBe('MemberForm')
		})
	})

	// The Overview tab used to hold every section at once; it's now split
	// across Overview/Courses/Quizzes/Certificates/Programs/Activity, each
	// reading its own slice of the SAME `overview` object.
	describe('the categorized tabs', () => {
		const overviewData = {
			last_login: null,
			last_active: null,
			last_ip: null,
			tags: [],
			notes: [],
			enrollments: [{ course: 'c1', course_title: 'Course One', progress: 50 }],
			quiz_submissions: [],
			avg_quiz_score: null,
			certificates: [],
			programs: [],
			recent_logins: [],
		}

		it('switches to Courses and shows only that slice of the data', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			overview.data = overviewData
			const wrapper = await mountDetail(router)

			await wrapper.find('[data-testid="tab-Courses"]').trigger('click')
			await flushPromises()

			expect(wrapper.find('[data-testid="member-courses"]').text()).toContain(
				'Course One'
			)
			expect(wrapper.find('[data-testid="member-overview"]').exists()).toBe(false)
		})

		it('shows the empty state for a tab with nothing in it', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			overview.data = overviewData
			const wrapper = await mountDetail(router)

			await wrapper.find('[data-testid="tab-Certificates"]').trigger('click')
			await flushPromises()

			expect(wrapper.find('[data-testid="member-certificates"]').text()).toContain(
				'No certificates yet.'
			)
		})

		it('only fetches the overview data once across every tab switch', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			const wrapper = await mountDetail(router)
			// Landing on Overview already triggered the one fetch this test
			// guards; a real fetch would resolve into overviewFetch.data — the
			// mock doesn't, so it's set by hand once here to unblock the
			// tabs below, the way the earlier response would have.
			expect(overview.fetch).toHaveBeenCalledTimes(1)
			overview.data = overviewData
			await flushPromises()

			await wrapper.find('[data-testid="tab-Courses"]').trigger('click')
			await wrapper.find('[data-testid="tab-Quizzes"]').trigger('click')
			await wrapper.find('[data-testid="tab-Activity"]').trigger('click')
			await flushPromises()

			expect(overview.fetch).toHaveBeenCalledTimes(1)
		})
	})

	describe('the Manage menu', () => {
		it('offers Suspend for an enabled member and Unsuspend for a suspended one', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [], enabled: 1 }
			const wrapper = await mountDetail(router)
			await flushPromises()

			expect(wrapper.find('[data-testid="menu-Suspend user"]').exists()).toBe(true)
			expect(wrapper.find('[data-testid="menu-Unsuspend user"]').exists()).toBe(false)

			lookup.data = { ...lookup.data, enabled: 0 }
			await flushPromises()

			expect(wrapper.find('[data-testid="menu-Suspend user"]').exists()).toBe(false)
			expect(wrapper.find('[data-testid="menu-Unsuspend user"]').exists()).toBe(true)
		})

		it('suspends the member and flips the menu without a refetch', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [], enabled: 1 }
			const wrapper = await mountDetail(router)
			callMock.mockResolvedValue(undefined)

			await wrapper.find('[data-testid="menu-Suspend user"]').trigger('click')
			await flushPromises()

			expect(callMock).toHaveBeenCalledWith('lms.lms.api.suspend_member', { member: MEMBER })
			expect(wrapper.find('[data-testid="menu-Unsuspend user"]').exists()).toBe(true)
		})

		it('resends the invitation through the public reset_password endpoint', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [], enabled: 1 }
			const wrapper = await mountDetail(router)
			callMock.mockResolvedValue(undefined)

			await wrapper.find('[data-testid="menu-Resend invitation"]').trigger('click')
			await flushPromises()

			expect(callMock).toHaveBeenCalledWith('frappe.core.doctype.user.user.reset_password', {
				user: MEMBER,
			})
			expect(toastMock.success).toHaveBeenCalled()
		})
	})

	describe('tags and notes', () => {
		const baseOverview = {
			last_login: null,
			last_active: null,
			last_ip: null,
			tags: ['vip'],
			notes: [],
			enrollments: [],
			quiz_submissions: [],
			avg_quiz_score: null,
			certificates: [],
			programs: [],
			recent_logins: [],
		}

		it('adds a tag and re-renders the badge list from the response', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			overview.data = { ...baseOverview }
			const wrapper = await mountDetail(router)
			callMock.mockResolvedValue(['vip', 'scholarship'])

			await wrapper.find('[data-testid="field-Add a tag"]').setValue('scholarship')
			await wrapper.find('[data-testid="add-tag"]').trigger('click')
			await flushPromises()

			expect(callMock).toHaveBeenCalledWith('lms.lms.api.add_member_tag', {
				member: MEMBER,
				tag: 'scholarship',
			})
			expect(overview.data.tags).toEqual(['vip', 'scholarship'])
		})

		it('offers existing tags on focus and adds one with a click', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			overview.data = { ...baseOverview }
			const wrapper = await mountDetail(router)
			// Opening the member costs no request for the suggestion list.
			expect(callMock).not.toHaveBeenCalledWith('lms.lms.api.get_member_tags')
			callMock.mockImplementation(async (url: string) =>
				url === 'lms.lms.api.get_member_tags'
					? [
							{ tag: 'vip', count: 4 },
							{ tag: 'scholarship', count: 3 },
					  ]
					: ['vip', 'scholarship']
			)

			await wrapper.find('[data-testid="field-Add a tag"]').trigger('focusin')
			await flushPromises()

			const suggestions = wrapper.find('[data-testid="tag-suggestions"]')
			// 'vip' is already on this member, so only the other one is offered.
			expect(suggestions.text()).toContain('scholarship')
			expect(suggestions.text()).not.toContain('vip')

			await suggestions.find('button').trigger('click')
			await flushPromises()

			expect(callMock).toHaveBeenCalledWith('lms.lms.api.add_member_tag', {
				member: MEMBER,
				tag: 'scholarship',
			})
			expect(overview.data.tags).toEqual(['vip', 'scholarship'])
		})

		it('does not send a tag containing a comma', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			overview.data = { ...baseOverview }
			const wrapper = await mountDetail(router)

			await wrapper.find('[data-testid="field-Add a tag"]').setValue('a,b')
			await wrapper.find('[data-testid="add-tag"]').trigger('click')
			await flushPromises()

			expect(callMock).not.toHaveBeenCalledWith('lms.lms.api.add_member_tag', expect.anything())
			expect(wrapper.text()).toContain('A tag cannot contain a comma.')
		})

		it('adds a note and clears the textarea', async () => {
			const router = makeRouter()
			await router.push(`/users/${MEMBER}`)
			lookup.data = { name: MEMBER, full_name: 'Jane Doe', roles: [] }
			overview.data = { ...baseOverview }
			const wrapper = await mountDetail(router)
			const newNote = { name: 'c1', content: 'Great progress', comment_by: 'mod@example.com', creation: '2026-01-01' }
			callMock.mockResolvedValue([newNote])

			await wrapper.find('[data-testid="field-Add a note"]').setValue('Great progress')
			await wrapper.find('[data-testid="add-note"]').trigger('click')
			await flushPromises()

			expect(callMock).toHaveBeenCalledWith('lms.lms.api.add_member_note', {
				member: MEMBER,
				content: 'Great progress',
			})
			expect(overview.data.notes).toEqual([newNote])
		})
	})
})
