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

vi.mock('frappe-ui', () => ({
	call: callMock,
	createResource: createResourceMock,
	toast: toastMock,
	Avatar: { props: ['image', 'label', 'size'], template: `<div />` },
	Badge: { template: `<span><slot /></span>` },
	Breadcrumbs: { props: ['items'], template: `<nav><slot /></nav>` },
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
})
