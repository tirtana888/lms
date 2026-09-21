import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)
;(String.prototype as any).format = function (this: string, ...args: unknown[]): string {
	return this.replace(/{(\d+)}/g, (_match, index) => String(args[Number(index)]))
}

const { createResourceMock } = vi.hoisted(() => ({ createResourceMock: vi.fn() }))
vi.mock('frappe-ui', () => ({ createResource: createResourceMock }))

import MemberStudyTime from '@/components/MemberStudyTime.vue'

// dayjs is provided by the app; a formatter with the one call this component makes is enough.
const dayjs = (date: string) => ({
	format: (fmt: string) => {
		const d = new Date(`${date}T00:00:00Z`)
		const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		return fmt === 'D MMM' ? `${d.getUTCDate()} ${months[d.getUTCMonth()]}` : date
	},
})

function series(seconds: number[]) {
	// Ends on 2026-09-21.
	return seconds.map((s, i) => {
		const d = new Date(Date.UTC(2026, 8, 21 - (seconds.length - 1 - i)))
		return { date: d.toISOString().slice(0, 10), seconds: s }
	})
}

let resource: { data: any; loading: boolean; update: any; reload: any }

function mountIt(member = 'ayu@x.id') {
	return mount(MemberStudyTime, {
		props: { member },
		global: { provide: { $dayjs: dayjs }, mocks: { __: (text: string) => text } },
	})
}

describe('MemberStudyTime', () => {
	beforeEach(() => {
		resource = reactive({ data: null, loading: false, update: vi.fn(), reload: vi.fn() }) as any
		createResourceMock.mockReset()
		createResourceMock.mockReturnValue(resource)
	})

	it('asks for the last 30 days of the member', () => {
		mountIt('ayu@x.id')
		expect(createResourceMock).toHaveBeenCalledWith({
			url: 'lms.lms.presence.get_study_time',
			params: { member: 'ayu@x.id', days: 30 },
			auto: true,
		})
	})

	it('shows a loading line until data arrives', () => {
		resource.loading = true
		const w = mountIt()
		expect(w.text()).toContain('Loading...')
		expect(w.find('[data-testid="study-bars"]').exists()).toBe(false)
	})

	it('renders the four totals in readable durations', async () => {
		resource.data = {
			days: series([0, 3600, 7800]),
			today_seconds: 7800,
			last_7_days_seconds: 11400,
			period_seconds: 11400,
			total_seconds: 90000,
			active_days: 2,
			total_days: 9,
		}
		const w = mountIt()
		await nextTick()
		const text = w.text()
		expect(text).toContain('2 h 10 min')
		expect(text).toContain('3 h 10 min')
		expect(text).toContain('25 h')
		for (const label of ['Today', 'Last 7 days', 'Last 3 days', 'All time']) expect(text).toContain(label)
	})

	it('draws one bar per day, scaled to the longest day, today highlighted', async () => {
		resource.data = {
			days: series([0, 3600, 7200]),
			today_seconds: 7200,
			last_7_days_seconds: 10800,
			period_seconds: 10800,
			total_seconds: 10800,
			active_days: 2,
			total_days: 2,
		}
		const w = mountIt()
		await nextTick()
		const bars = w.findAll('[data-testid="study-bars"] > div')
		expect(bars).toHaveLength(3)
		expect(bars[2].attributes('style')).toContain('height: 100%')
		expect(bars[1].attributes('style')).toContain('height: 50%')
		expect(bars[0].attributes('style')).toContain('height: 2px')
		expect(bars[2].classes()).toContain('bg-surface-blue-2')
		expect(bars[0].classes()).not.toContain('bg-surface-blue-2')
	})

	it('keeps a short day visible next to a very long one', async () => {
		resource.data = {
			days: series([60, 36000]),
			today_seconds: 36000,
			last_7_days_seconds: 36060,
			period_seconds: 36060,
			total_seconds: 36060,
			active_days: 2,
			total_days: 2,
		}
		const w = mountIt()
		await nextTick()
		const first = w.findAll('[data-testid="study-bars"] > div')[0].attributes('style')
		expect(first).toContain('height: 8%')
	})

	it('gives each bar a tooltip with the date and the time', async () => {
		resource.data = {
			days: series([0, 5400]),
			today_seconds: 5400,
			last_7_days_seconds: 5400,
			period_seconds: 5400,
			total_seconds: 5400,
			active_days: 1,
			total_days: 1,
		}
		const w = mountIt()
		await nextTick()
		const bars = w.findAll('[data-testid="study-bars"] > div')
		expect(bars[1].attributes('title')).toBe('21 Sep: 1 h 30 min')
		expect(bars[0].attributes('title')).toBe('20 Sep: —')
	})

	it('says so when nothing has been recorded yet', async () => {
		resource.data = {
			days: series([0, 0, 0]),
			today_seconds: 0,
			last_7_days_seconds: 0,
			period_seconds: 0,
			total_seconds: 0,
			active_days: 0,
			total_days: 0,
		}
		const w = mountIt()
		await nextTick()
		expect(w.text()).toContain('No study time recorded yet.')
		expect(w.text()).toContain('—')
	})

	it('explains active days once there is data', async () => {
		resource.data = {
			days: series(Array(30).fill(0).map((_, i) => (i % 3 === 0 ? 600 : 0))),
			today_seconds: 600,
			last_7_days_seconds: 1800,
			period_seconds: 6000,
			total_seconds: 9000,
			active_days: 10,
			total_days: 15,
		}
		const w = mountIt()
		await nextTick()
		expect(w.text()).toContain('Active on 10 of the last 30 days, 15 days in total.')
	})

	it('reloads for another member when the prop changes', async () => {
		const w = mountIt('ayu@x.id')
		await w.setProps({ member: 'budi@x.id' })
		await flushPromises()
		expect(resource.update).toHaveBeenCalledWith({ params: { member: 'budi@x.id', days: 30 } })
		expect(resource.reload).toHaveBeenCalled()
	})
})
