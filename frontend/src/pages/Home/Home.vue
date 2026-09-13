<template>
	<div class="w-full p-5">
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<h1 class="text-2xl-bold text-ink-gray-9">
					{{ __('Hey') }}, {{ user.data?.full_name }} 👋
				</h1>
				<div>
					<button
						v-if="!isAdmin"
						type="button"
						@click="showStreakModal = true"
						:aria-label="
							__('View learning streak: {0} days').format(
								streakInfo.data?.current_streak || 0
							)
						"
						class="bg-surface-amber-2 px-2 py-1 rounded-md cursor-pointer"
					>
						<span> 🔥 </span>
						<span class="text-ink-gray-9">
							{{ streakInfo.data?.current_streak }}
						</span>
					</button>
				</div>
			</div>

			<div class="text-lg text-ink-gray-6 leading-6">
				{{ subtitle }}
			</div>
		</div>

		<div
			v-if="isHomeLoading"
			class="flex flex-1 items-center justify-center py-20"
		>
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>
		<StudentHome v-else :myLiveClasses="myLiveClasses" />
	</div>
	<Streak v-model="showStreakModal" :streakInfo="streakInfo" />
</template>
<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import { call, createResource, LoadingIndicator, usePageMeta } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import StudentHome from '@/pages/Home/StudentHome.vue'
import Streak from '@/pages/Home/Streak.vue'

const user = inject<any>('$user')
const router = useRouter()
const { brand } = sessionStore()
const evalCount = ref(0)
const showStreakModal = ref(false)

const fetchEvalCount = () => {
	call('frappe.client.get_count', {
		doctype: 'LMS Certificate Request',
		filters: {
			member: user?.data?.name,
			status: 'Upcoming',
			date: ['>=', inject<any>('$dayjs')().format('YYYY-MM-DD')],
		},
	}).then((data: any) => {
		evalCount.value = data
	})
}

// Admin roles get their own dedicated landing pages now (Dashboard for
// analytics, Overview for the courses/batches/evaluations list this page
// used to show them directly) - redirect there instead of rendering
// anything here, so an admin never sees a half-built student page flash by.
const isAdmin = computed(() => {
	return (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
})

const isHomeLoading = computed(() => {
	return myLiveClasses.loading && !myLiveClasses.data
})

onMounted(() => {
	if (isAdmin.value) {
		router.replace({ name: 'Dashboard' })
		return
	}
	fetchEvalCount()
})

const myLiveClasses = createResource({
	url: 'lms.lms.api.get_my_live_classes',
	auto: !isAdmin.value,
})

const streakInfo = createResource({
	url: 'lms.lms.api.get_streak_info',
	auto: true,
})

const subtitle = computed(() => {
	let liveClassSuffix =
		myLiveClasses.data?.length > 1 ? __('live classes') : __('live class')
	let evalSuffix = evalCount.value > 1 ? __('evaluations') : __('evaluation')
	if (myLiveClasses.data?.length > 0 && evalCount.value > 0) {
		return __('You have {0} upcoming {1} and {2} {3} scheduled.').format(
			myLiveClasses.data.length,
			liveClassSuffix,
			evalCount.value,
			evalSuffix
		)
	} else if (myLiveClasses.data?.length > 0) {
		return __('You have {0} upcoming {1}.').format(
			myLiveClasses.data.length,
			liveClassSuffix
		)
	} else if (evalCount.value > 0) {
		return __('You have {0} {1} scheduled.').format(
			evalCount.value,
			evalSuffix
		)
	}
	return __('Resume where you left off')
})

usePageMeta(() => {
	return {
		title: __('Home'),
		icon: brand.favicon,
	}
})
</script>
