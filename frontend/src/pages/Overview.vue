<template>
	<div class="w-full p-5">
		<div class="space-y-2">
			<h1 class="text-2xl-bold text-ink-gray-9">
				{{ __('Hey') }}, {{ user.data?.full_name }} 👋
			</h1>
			<div class="text-lg text-ink-gray-6 leading-6">
				{{ subtitle }}
			</div>
		</div>

		<div
			v-if="isOverviewLoading"
			class="flex flex-1 items-center justify-center py-20"
		>
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>
		<AdminHome v-else :liveClasses="adminLiveClasses" :evals="adminEvals" />
	</div>
</template>
<script setup>
import { computed, inject } from 'vue'
import { createResource, LoadingIndicator, usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import AdminHome from '@/pages/Home/AdminHome.vue'

const user = inject('$user')
const { brand } = sessionStore()

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

const subtitle = computed(() => {
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
		title: __('Overview'),
		icon: brand.favicon,
	}
})
</script>
