<template>
	<div data-testid="member-study-time">
		<div class="text-p-sm-medium text-ink-gray-7 mb-2">{{ __('Study time') }}</div>
		<div v-if="study.loading && !study.data" class="text-p-sm text-ink-gray-5">
			{{ __('Loading...') }}
		</div>
		<template v-else-if="study.data">
			<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
				<div
					v-for="stat in stats"
					:key="stat.label"
					class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3"
				>
					<div class="text-xl-semibold text-ink-gray-9 tabular-nums">{{ stat.value }}</div>
					<div class="text-p-sm text-ink-gray-6">{{ stat.label }}</div>
				</div>
			</div>

			<div
				class="mt-3 flex h-16 items-end gap-px"
				role="img"
				:aria-label="__('Study time per day, last {0} days').format(study.data.days.length)"
				data-testid="study-bars"
			>
				<div
					v-for="day in bars"
					:key="day.date"
					class="flex-1 rounded-t-sm"
					:class="day.isToday ? 'bg-surface-blue-3' : day.seconds ? 'bg-surface-gray-5' : 'bg-surface-gray-2'"
					:style="{ height: day.height }"
					:title="day.title"
				/>
			</div>
			<div class="mt-1 flex justify-between text-p-xs text-ink-gray-5">
				<span>{{ firstLabel }}</span>
				<span>{{ __('Today') }}</span>
			</div>

			<p class="mt-2 text-p-xs text-ink-gray-5">
				{{ caption }}
			</p>
		</template>
	</div>
</template>
<script setup>
import { createResource } from 'frappe-ui'
import { computed, inject, watch } from 'vue'
import { formatOnlineFor } from '@/utils/presence'

const props = defineProps({
	member: { type: String, required: true },
})

const dayjs = inject('$dayjs')
const DAYS = 30

const study = createResource({
	url: 'lms.lms.presence.get_study_time',
	params: { member: props.member, days: DAYS },
	auto: true,
})

watch(
	() => props.member,
	(member) => {
		study.update({ params: { member, days: DAYS } })
		study.reload()
	}
)

const fmt = (seconds) => (seconds > 0 ? formatOnlineFor(seconds) : '—')

const stats = computed(() => {
	const d = study.data
	return [
		{ label: __('Today'), value: fmt(d.today_seconds) },
		{ label: __('Last 7 days'), value: fmt(d.last_7_days_seconds) },
		{ label: __('Last {0} days').format(d.days.length), value: fmt(d.period_seconds) },
		{ label: __('All time'), value: fmt(d.total_seconds) },
	]
})

const bars = computed(() => {
	const days = study.data.days
	const max = Math.max(...days.map((d) => d.seconds), 1)
	return days.map((d, i) => ({
		date: d.date,
		seconds: d.seconds,
		isToday: i === days.length - 1,
		// A day with any study time stays visible even when it is dwarfed by a long one.
		height: d.seconds > 0 ? `${Math.max(8, Math.round((d.seconds / max) * 100))}%` : '2px',
		title: `${dayjs(d.date).format('D MMM')}: ${fmt(d.seconds)}`,
	}))
})

const firstLabel = computed(() => dayjs(study.data.days[0].date).format('D MMM'))

const caption = computed(() => {
	const d = study.data
	if (!d.total_seconds) {
		return __('No study time recorded yet. Time is counted while the LMS is open in a visible tab.')
	}
	return __('Active on {0} of the last {1} days, {2} days in total. Time is counted while the LMS is open in a visible tab.')
		.format(d.active_days, d.days.length, d.total_days)
})
</script>
