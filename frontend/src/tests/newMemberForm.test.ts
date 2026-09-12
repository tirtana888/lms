import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import {
	createMemoryHistory,
	createRouter,
	RouterView,
	type Router,
} from 'vue-router'
import { defineComponent, h } from 'vue'

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)

// frappe-ui's ESM build doesn't resolve under vitest (see chapterForm.test.ts),
// so every export the page and FormShell reach for is stubbed by hand.
const { callMock, toastMock } = vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return {
		callMock: vi.fn(),
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
	toast: toastMock,
	Dialog: {
		name: 'Dialog',
		props: ['open', 'title', 'size'],
		emits: ['update:open'],
		template: `<div v-if="open" role="dialog"><h2>{{ title }}</h2><slot /><slot name="actions" /></div>`,
	},
	FormControl: {
		props: ['modelValue', 'label', 'type', 'placeholder', 'required', 'disabled'],
		emits: ['update:modelValue'],
		template: `<label :data-testid="'field-' + label">{{ label }}
			<input :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />
		</label>`,
	},
}))

vi.mock('frappe-ui/frappe', () => ({
	useOnboarding: () => ({ updateOnboardingStep: vi.fn() }),
	useTelemetry: () => ({ capture: vi.fn() }),
}))

vi.mock('@/utils', () => ({ cleanError: (msg: string) => msg }))

vi.mock('@/components/Controls/BooleanSwitch.vue', () => ({
	default: {
		props: ['modelValue', 'label', 'size'],
		emits: ['update:modelValue'],
		template: `<button :data-testid="'role-' + label" :data-on="String(modelValue)" @click="$emit('update:modelValue', !modelValue)">{{ label }}</button>`,
	},
}))

import NewMemberForm from '@/pages/Forms/NewMemberForm.vue'
import { openFormRoute } from '@/composables/useFormRoute'
import { membersRevision } from '@/stores/members'
// The REAL route table, not a copy.
import { routes } from '@/routes'

const MEMBER = 'jane@doe.com'
const moderator = { name: 'mod@example.com', is_moderator: true }
const outsider = { name: 'someone@example.com' }

const makeRouter = (): Router =>
	createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: '/', name: 'Home', component: { template: '<div>HOME</div>' } },
			{
				path: '/users',
				name: 'Members',
				component: defineComponent({
					render: () => [h('div', 'MEMBERS'), h(RouterView)],
				}),
				children: [
					{ path: 'new', name: 'NewMemberForm', component: NewMemberForm },
				],
			},
		],
	})

const mountRoot = async (
	router: Router,
	user: Record<string, unknown> | null = moderator
) => {
	const wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
		global: {
			plugins: [router],
			provide: { $user: { data: user } },
			stubs: { teleport: true },
			mocks: { __: (text: string) => text },
		},
	})
	await flushPromises()
	return wrapper
}

const fields = (wrapper: ReturnType<typeof mount>) =>
	wrapper.find('[data-testid="member-fields"]')

const save = (wrapper: ReturnType<typeof mount>) =>
	wrapper.find('[data-testid="member-save"]')

describe('the new member form', () => {
	beforeEach(() => {
		Object.defineProperty(window, 'innerWidth', {
			value: 1024,
			writable: true,
			configurable: true,
		})
		callMock.mockReset()
		toastMock.success.mockClear()
		toastMock.error.mockClear()
	})

	it('is nested under Members, one static child route', () => {
		const router = createRouter({ history: createMemoryHistory(), routes })

		const resolved = router.resolve('/users/new')
		expect(resolved.name).toBe('NewMemberForm')
		expect(resolved.matched.map((r) => r.name)).toEqual(['Members', 'NewMemberForm'])
	})

	describe('the permission gate', () => {
		it('refuses a non-moderator', async () => {
			const router = makeRouter()
			await router.push('/users/new')
			const wrapper = await mountRoot(router, outsider)

			expect(fields(wrapper).exists()).toBe(false)
			expect(wrapper.text()).toContain('You are not permitted to manage members.')
		})

		it('refuses a signed-out visitor', async () => {
			const router = makeRouter()
			await router.push('/users/new')
			const wrapper = await mountRoot(router, null)

			expect(fields(wrapper).exists()).toBe(false)
		})

		it('shows the fields to a moderator', async () => {
			const router = makeRouter()
			await router.push('/users/new')
			const wrapper = await mountRoot(router)

			expect(fields(wrapper).exists()).toBe(true)
		})
	})

	it('adds the member, assigns the checked roles, and closes back to Members', async () => {
		const router = makeRouter()
		await router.push('/')
		await openFormRoute(router, { name: 'NewMemberForm' })
		const wrapper = await mountRoot(router)
		callMock.mockResolvedValue({ name: MEMBER })

		await wrapper.find('[data-testid="field-Email"] input').setValue('  jane@doe.com  ')
		await wrapper.find('[data-testid="role-Student"]').trigger('click')
		await save(wrapper).trigger('click')
		await flushPromises()

		expect(callMock).toHaveBeenCalledWith('frappe.client.insert', {
			doc: {
				doctype: 'User',
				email: MEMBER,
				first_name: undefined,
				last_name: undefined,
			},
		})
		expect(callMock).toHaveBeenCalledWith('lms.lms.api.save_role', {
			user: MEMBER,
			role: 'LMS Student',
			value: 1,
		})
		expect(toastMock.success).toHaveBeenCalled()
		// Opened via openFormRoute from '/', not a cold deep link — closes by
		// popping back to it rather than replacing onto Members.
		expect(router.currentRoute.value.name).toBe('Home')
	})

	it('bumps the signal a mounted Members list watches', async () => {
		const before = membersRevision.value
		const router = makeRouter()
		await router.push('/users/new')
		const wrapper = await mountRoot(router)
		callMock.mockResolvedValue({ name: MEMBER })

		await wrapper.find('[data-testid="field-Email"] input').setValue(MEMBER)
		await save(wrapper).trigger('click')
		await flushPromises()

		expect(membersRevision.value).toBeGreaterThan(before)
	})

	it('requires an email before submitting', async () => {
		const router = makeRouter()
		await router.push('/users/new')
		const wrapper = await mountRoot(router)

		await save(wrapper).trigger('click')
		await flushPromises()

		expect(callMock).not.toHaveBeenCalled()
		expect(toastMock.error).toHaveBeenCalledWith('Email is required')
	})
})
