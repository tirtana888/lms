import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick, reactive } from 'vue'

const call = vi.fn()
vi.mock('frappe-ui', () => ({ call: (...args: unknown[]) => call(...args) }))

const route = reactive<{ name: string | null; params: Record<string, string> }>({
	name: 'Courses',
	params: {},
})
vi.mock('vue-router', () => ({ useRoute: () => route }))

const session = reactive({ isLoggedIn: true })
vi.mock('@/stores/session', () => ({ sessionStore: () => session }))

import { PING_INTERVAL_MS, usePresence } from '@/utils/presence'

const Host = defineComponent({
	setup() {
		usePresence()
		return () => h('div')
	},
})

function setVisibility(state: 'visible' | 'hidden') {
	Object.defineProperty(document, 'visibilityState', { value: state, configurable: true })
	document.dispatchEvent(new Event('visibilitychange'))
}

const pings = () => call.mock.calls.filter(([method]) => method === 'lms.lms.presence.ping')

describe('usePresence', () => {
	beforeEach(() => {
		vi.useFakeTimers()
		vi.setSystemTime(new Date('2026-09-21T10:00:00Z'))
		call.mockReset()
		call.mockResolvedValue({ tracked: true })
		route.name = 'Courses'
		route.params = {}
		session.isLoggedIn = true
		setVisibility('visible')
	})

	afterEach(() => {
		vi.useRealTimers()
	})

	it('pings as soon as the app mounts', () => {
		const wrapper = mount(Host)
		expect(pings()).toHaveLength(1)
		wrapper.unmount()
	})

	it('keeps pinging every interval while the tab stays visible', async () => {
		const wrapper = mount(Host)
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 3)
		expect(pings()).toHaveLength(4)
		wrapper.unmount()
	})

	it('sends the current page and course', () => {
		route.name = 'CourseDetail'
		route.params = { courseName: 'ekonomi-kreatif' }
		const wrapper = mount(Host)
		expect(call).toHaveBeenCalledWith('lms.lms.presence.ping', {
			page: 'CourseDetail',
			course: 'ekonomi-kreatif',
		})
		wrapper.unmount()
	})

	it('sends a null course outside course pages', () => {
		const wrapper = mount(Host)
		expect(call).toHaveBeenCalledWith('lms.lms.presence.ping', { page: 'Courses', course: null })
		wrapper.unmount()
	})

	it('stops pinging while the tab is hidden and resumes when it is shown', async () => {
		const wrapper = mount(Host)
		expect(pings()).toHaveLength(1)

		setVisibility('hidden')
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 4)
		expect(pings()).toHaveLength(1)

		setVisibility('visible')
		expect(pings()).toHaveLength(2)
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS)
		expect(pings()).toHaveLength(3)
		wrapper.unmount()
	})

	it('does not start when the tab is hidden on load', async () => {
		setVisibility('hidden')
		const wrapper = mount(Host)
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 2)
		expect(pings()).toHaveLength(0)
		wrapper.unmount()
	})

	it('reports a new location straight away on navigation', async () => {
		const wrapper = mount(Host)
		await vi.advanceTimersByTimeAsync(5000)
		route.name = 'CourseDetail'
		route.params = { courseName: 'a' }
		await nextTick()
		expect(pings()).toHaveLength(2)
		expect(pings()[1][1]).toEqual({ page: 'CourseDetail', course: 'a' })
		wrapper.unmount()
	})

	it('collapses a burst of navigations into one ping', async () => {
		const wrapper = mount(Host)
		await vi.advanceTimersByTimeAsync(5000)
		for (const name of ['A', 'B', 'C']) {
			route.name = name
			await nextTick()
		}
		expect(pings()).toHaveLength(2)
		wrapper.unmount()
	})

	it('never pings for a logged-out visitor', async () => {
		session.isLoggedIn = false
		const wrapper = mount(Host)
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 2)
		expect(pings()).toHaveLength(0)
		wrapper.unmount()
	})

	it('starts once the visitor signs in, and stops when they sign out', async () => {
		session.isLoggedIn = false
		const wrapper = mount(Host)
		expect(pings()).toHaveLength(0)

		session.isLoggedIn = true
		await nextTick()
		expect(pings()).toHaveLength(1)

		session.isLoggedIn = false
		await nextTick()
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 2)
		expect(pings()).toHaveLength(1)
		wrapper.unmount()
	})

	it('swallows request failures and keeps going', async () => {
		call.mockRejectedValue(new Error('offline'))
		const wrapper = mount(Host)
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 2)
		expect(pings()).toHaveLength(3)
		wrapper.unmount()
	})

	it('stops for good when the app unmounts', async () => {
		const wrapper = mount(Host)
		wrapper.unmount()
		await vi.advanceTimersByTimeAsync(PING_INTERVAL_MS * 3)
		expect(pings()).toHaveLength(1)
		setVisibility('hidden')
		setVisibility('visible')
		expect(pings()).toHaveLength(1)
	})
})
