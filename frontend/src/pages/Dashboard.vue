<template>
	<div>
		<PageHeader :title="__('Dashboard')" />
		<div class="px-5 pt-4">
			<TabButtons
				:options="[
					{ label: __('Dashboard'), value: 'dashboard' },
					{ label: __('Overview'), value: 'overview' },
				]"
				v-model="activeTab"
			/>
		</div>

		<div v-if="activeTab === 'dashboard'" class="p-5 space-y-5">
			<div
				class="border rounded-lg p-4 flex flex-wrap items-center gap-x-8 gap-y-3"
				data-testid="active-now"
			>
				<div class="flex items-center gap-3">
					<span class="relative flex size-3 shrink-0">
						<span
							v-if="activeNow.data?.learners"
							class="absolute inline-flex size-full rounded-full bg-surface-green-7 opacity-60 animate-ping motion-reduce:animate-none"
						/>
						<span
							class="relative inline-flex size-3 rounded-full"
							:class="activeNow.data?.learners ? 'bg-surface-green-7' : 'bg-surface-gray-4'"
						/>
					</span>
					<div>
						<div class="text-2xl-bold text-ink-gray-9 tabular-nums leading-none">
							{{ activeNow.data?.learners ?? 0 }}
						</div>
						<div class="text-p-sm text-ink-gray-6 mt-1">
							{{ __('Active learners now') }}
						</div>
					</div>
				</div>
				<div class="text-p-sm text-ink-gray-5 max-w-xs">
					{{ __('Learners with the LMS open in a visible tab. Refreshes every 30 seconds.') }}
					<span v-if="activeNow.data?.staff">
						{{ __('{0} staff also online.').format(activeNow.data.staff) }}
					</span>
				</div>
				<div
					v-if="activeNow.data?.courses?.length || activeNow.data?.elsewhere"
					class="flex flex-wrap gap-2 sm:ms-auto"
				>
					<span
						v-for="c in activeNow.data.courses"
						:key="c.course"
						class="inline-flex items-center gap-1.5 rounded-full bg-surface-gray-2 px-2.5 py-1 text-p-sm text-ink-gray-8"
					>
						<span class="truncate max-w-56">{{ c.title }}</span>
						<span class="font-medium tabular-nums">{{ c.count }}</span>
					</span>
					<span
						v-if="activeNow.data.elsewhere"
						class="inline-flex items-center gap-1.5 rounded-full bg-surface-gray-2 px-2.5 py-1 text-p-sm text-ink-gray-6"
					>
						{{ __('Elsewhere') }}
						<span class="font-medium tabular-nums">{{ activeNow.data.elsewhere }}</span>
					</span>
				</div>
			</div>

			<div class="border rounded-lg overflow-hidden">
				<div class="p-4 border-b flex items-center gap-2">
					<span class="lucide-school size-4 text-ink-gray-6" />
					<span class="font-medium text-ink-gray-9">{{ __('Your school') }}</span>
				</div>
				<div class="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-5 p-4">
					<div>
						<div class="flex items-center justify-between mb-3">
							<TabButtons
								:options="[
									{ label: __('New signups'), value: 'signups' },
									{ label: __('Active learners'), value: 'active_learners' },
								]"
								v-model="chartTab"
							/>
							<FormControl
								type="select"
								v-model="range"
								:options="rangeOptions"
								class="w-40"
							/>
						</div>
						<div class="min-h-64 border rounded-md">
							<AxisChart
								v-if="chartTab === 'signups' && signupsChart.data"
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
							<AxisChart
								v-else-if="chartTab === 'active_learners' && activeLearnersChart.data"
								:config="{
									data: activeLearnersChart.data,
									title: '',
									subtitle: '',
									xAxis: {
										key: 'date',
										type: 'time',
										title: __('Date'),
										timeGrain: 'day',
									},
									yAxis: {
										title: __('Active learners'),
									},
									series: [
										{ name: 'active_learners', type: 'line', showDataPoints: true },
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

		<div v-else class="w-full p-5">
			<div class="space-y-2">
				<h1 class="text-2xl-bold text-ink-gray-9">
					{{ __('Hey') }}, {{ user.data?.full_name }} 👋
				</h1>
				<div class="text-lg text-ink-gray-6 leading-6">
					{{ overviewSubtitle }}
				</div>
			</div>

			<div
				v-if="isOverviewLoading"
				class="flex flex-1 items-center justify-center py-20"
			>
				<LoadingIndicator class="size-5 text-ink-gray-5" />
			</div>
			<AdminHome
				v-else
				:liveClasses="adminLiveClasses"
				:evals="adminEvals"
			/>
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
	TabButtons,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import AdminHome from '@/pages/Home/AdminHome.vue'
import { sessionStore } from '@/stores/session'

const { brand } = sessionStore()
const dayjs = inject('$dayjs')
const user = inject('$user')

const activeTab = ref('dashboard')

// Which chart the "Your school" card's tab switcher is showing. Both charts
// still load eagerly below (the active-learners query is a single cheap
// GROUP BY) so switching tabs never needs to wait on a fetch.
const chartTab = ref('signups')

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

// Who has the LMS open right now (heartbeat-based, see lms/lms/presence.py). Unlike the
// resources above it is not cached and is polled, because a stale number defeats the point.
const ACTIVE_NOW_REFRESH_MS = 30000
const activeNow = createResource({
	url: 'lms.lms.presence.get_active_now',
	auto: true,
})
let activeNowTimer = null
onMounted(() => {
	activeNowTimer = setInterval(() => {
		if (activeTab.value === 'dashboard' && document.visibilityState === 'visible') {
			activeNow.reload()
		}
	}, ACTIVE_NOW_REFRESH_MS)
})
onBeforeUnmount(() => clearInterval(activeNowTimer))

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

// Distinct daily logins from Activity Log, not a Dashboard Chart like
// signupsChart: Dashboard Chart's own aggregations (Count/Sum/Average/...)
// have no "distinct" option, so built that way this would count login
// *events* rather than learners - a student logging in twice in a day would
// be counted twice. lms.lms.utils.get_active_learners_chart does the
// distinct-by-day count directly and returns the same {date, count} shape
// get_chart_data does, so it drops into the same transform/chart config.
const activeLearnersChart = createResource({
	url: 'lms.lms.utils.get_active_learners_chart',
	params: {
		from_date: dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
	},
	auto: true,
	transform(data) {
		return data.map((item) => ({
			date: new Date(item.date),
			active_learners: item.count,
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
	activeLearnersChart.update({
		params: {
			from_date: dayjs().subtract(Number(range.value), 'day').format('YYYY-MM-DD'),
		},
	})
	activeLearnersChart.reload()
})

// The "Overview" tab: the same content this page used to show admins
// directly before Dashboard existed - unchanged, just folded in as a second
// tab here instead of AdminHome.vue's own separate route.
const adminLiveClasses = createResource({
	url: 'lms.lms.api.get_admin_live_classes',
	auto: true,
})

const adminEvals = createResource({
	url: 'lms.lms.api.get_admin_evals',
	auto: true,
})

const isOverviewLoading = computed(() => {
	return (
		(adminLiveClasses.loading && !adminLiveClasses.data) ||
		(adminEvals.loading && !adminEvals.data)
	)
})

const overviewSubtitle = computed(() => {
	let liveClassSuffix =
		adminLiveClasses.data?.length > 1 ? __('live classes') : __('live class')
	let evalSuffix =
		adminEvals.data?.length > 1 ? __('evaluations') : __('evaluation')
	if (adminLiveClasses.data?.length > 0 && adminEvals.data?.length > 0) {
		return __('You have {0} upcoming {1} and {2} {3} scheduled.').format(
			adminLiveClasses.data.length,
			liveClassSuffix,
			adminEvals.data.length,
			evalSuffix
		)
	} else if (adminLiveClasses.data?.length > 0) {
		return __('You have {0} upcoming {1}.').format(
			adminLiveClasses.data.length,
			liveClassSuffix
		)
	} else if (adminEvals.data?.length > 0) {
		return __('You have {0} {1} scheduled.').format(
			adminEvals.data.length,
			evalSuffix
		)
	}
	return __('Manage your courses and batches at a glance')
})

usePageMeta(() => {
	return {
		title: __('Dashboard'),
		icon: brand.favicon,
	}
})
</script>
