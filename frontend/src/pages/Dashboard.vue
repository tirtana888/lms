<template>
	<div>
		<PageHeader :title="__('Dashboard')" />
		<div class="p-5 space-y-5">
			<div class="border rounded-lg overflow-hidden">
				<div class="p-4 border-b flex items-center gap-2">
					<span class="lucide-school size-4 text-ink-gray-6" />
					<span class="font-medium text-ink-gray-9">{{ __('Your school') }}</span>
				</div>
				<div class="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-5 p-4">
					<div>
						<div class="flex items-center justify-between mb-3">
							<div class="font-medium text-ink-gray-9">
								{{ __('New Signups') }}
							</div>
							<FormControl
								type="select"
								v-model="range"
								:options="rangeOptions"
								class="w-40"
							/>
						</div>
						<div class="min-h-64 border rounded-md">
							<AxisChart
								v-if="signupsChart.data"
								:config="{
									data: signupsChart.data,
									title: '',
									subtitle: '',
									xAxis: {
										key: 'date',
										type: 'time',
										title: __('Date'),
										timeGrain: 'day',
									},
									yAxis: {
										title: __('Signups'),
									},
									series: [
										{ name: 'signups', type: 'line', showDataPoints: true },
									],
								}"
							/>
							<div
								v-else
								class="flex h-64 items-center justify-center"
							>
								<LoadingIndicator class="size-5 text-ink-gray-5" />
							</div>
						</div>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<NumberChart
							class="border rounded-md"
							:config="{ title: __('All users'), value: chartDetails.data?.users }"
						/>
						<NumberChart
							class="border rounded-md"
							:config="{ title: __('Courses'), value: chartDetails.data?.courses }"
						/>
						<NumberChart
							class="border rounded-md"
							:config="{
								title: __('Enrollments'),
								value: chartDetails.data?.enrollments,
							}"
						/>
						<NumberChart
							class="border rounded-md"
							:config="{
								title: __('Certifications'),
								value: chartDetails.data?.certifications,
							}"
						/>
						<NumberChart
							class="border rounded-md"
							:config="{
								title: __('Completions'),
								value: chartDetails.data?.completions,
							}"
						/>
						<NumberChart
							class="border rounded-md"
							:config="{
								title: __('Course categories'),
								value: overview.data?.categories,
							}"
						/>
					</div>
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
				<div class="border rounded-lg p-4">
					<div class="flex items-center justify-between mb-3">
						<div class="font-medium text-ink-gray-9">{{ __('New users') }}</div>
						<router-link
							:to="{ name: 'Members' }"
							class="text-p-sm text-ink-gray-6 hover:text-ink-gray-8"
						>
							{{ __('See all') }}
						</router-link>
					</div>
					<div v-if="overview.loading" class="flex justify-center py-6">
						<LoadingIndicator class="size-4 text-ink-gray-5" />
					</div>
					<div v-else-if="overview.data?.new_users?.length" class="space-y-3">
						<div
							v-for="u in overview.data.new_users"
							:key="u.name"
							class="flex items-center gap-2.5"
						>
							<Avatar size="md" :image="u.user_image" :label="u.full_name" />
							<div class="min-w-0">
								<div class="text-p-sm text-ink-gray-9 truncate">
									{{ u.full_name }}
								</div>
								<div class="text-p-xs text-ink-gray-5">
									{{ dayjs(u.creation).fromNow() }}
								</div>
							</div>
						</div>
					</div>
					<div v-else class="text-p-sm italic text-ink-gray-5">
						{{ __('No new users yet.') }}
					</div>
				</div>

				<div class="border rounded-lg p-4">
					<div class="font-medium text-ink-gray-9 mb-3">
						{{ __('Events Log') }}
					</div>
					<div v-if="overview.loading" class="flex justify-center py-6">
						<LoadingIndicator class="size-4 text-ink-gray-5" />
					</div>
					<div v-else-if="overview.data?.events_log?.length" class="space-y-3">
						<div
							v-for="(event, idx) in overview.data.events_log"
							:key="idx"
							class="flex items-center gap-2.5"
						>
							<Avatar size="md" :image="event.user_image" :label="event.full_name" />
							<div class="min-w-0">
								<div class="text-p-sm text-ink-gray-9 truncate">
									{{ event.full_name }}
								</div>
								<div class="text-p-xs text-ink-gray-5">
									{{ __('Logged in') }} &middot;
									{{ dayjs(event.creation).fromNow() }}
								</div>
							</div>
						</div>
					</div>
					<div v-else class="text-p-sm italic text-ink-gray-5">
						{{ __('No recent activity.') }}
					</div>
				</div>

				<div class="border rounded-lg p-4">
					<div class="font-medium text-ink-gray-9 mb-3">
						{{ __('Online users ({0})').format(overview.data?.online_count ?? 0) }}
					</div>
					<div v-if="overview.loading" class="flex justify-center py-6">
						<LoadingIndicator class="size-4 text-ink-gray-5" />
					</div>
					<div v-else-if="overview.data?.online_users?.length" class="space-y-3">
						<div
							v-for="u in overview.data.online_users"
							:key="u.name"
							class="flex items-center gap-2.5"
						>
							<div class="relative shrink-0">
								<Avatar size="md" :image="u.user_image" :label="u.full_name" />
								<span
									class="absolute -bottom-0.5 -end-0.5 size-2.5 rounded-full bg-surface-green-7 border-2 border-surface-base"
								/>
							</div>
							<div class="text-p-sm text-ink-gray-9 truncate">
								{{ u.full_name }}
							</div>
						</div>
					</div>
					<div v-else class="text-p-sm italic text-ink-gray-5">
						{{ __('No online users found.') }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import {
	Avatar,
	AxisChart,
	createResource,
	FormControl,
	LoadingIndicator,
	NumberChart,
	usePageMeta,
} from 'frappe-ui'
import { inject, ref, watch } from 'vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import { sessionStore } from '@/stores/session'

const { brand } = sessionStore()
const dayjs = inject('$dayjs')

const range = ref('7')
const rangeOptions = [
	{ label: __('Last 7 days'), value: '7' },
	{ label: __('Last 30 days'), value: '30' },
	{ label: __('Last 3 months'), value: '90' },
]

const chartDetails = createResource({
	url: 'lms.lms.api.get_chart_details',
	cache: ['dashboard_chart_details'],
	auto: true,
})

const overview = createResource({
	url: 'lms.lms.api.get_dashboard_overview',
	cache: ['dashboard_overview'],
	auto: true,
})

const signupsChart = createResource({
	url: 'lms.lms.utils.get_chart_data',
	params: {
		chart_name: 'New Signups',
		from_date: dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
	},
	auto: true,
	transform(data) {
		return data.map((item) => ({
			date: new Date(item.date),
			signups: item.count,
		}))
	},
})

watch(range, () => {
	signupsChart.update({
		params: {
			chart_name: 'New Signups',
			from_date: dayjs().subtract(Number(range.value), 'day').format('YYYY-MM-DD'),
		},
	})
	signupsChart.reload()
})

usePageMeta(() => {
	return {
		title: __('Dashboard'),
		icon: brand.favicon,
	}
})
</script>
