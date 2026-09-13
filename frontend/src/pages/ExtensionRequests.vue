<template>
	<div>
		<PageHeader :title="__('Extension Requests')" />
		<div class="p-5 space-y-4">
			<div class="flex flex-wrap items-center gap-3">
				<Link
					doctype="LMS Course"
					v-model="selectedCourse"
					:placeholder="__('Select a course')"
					class="w-64"
				/>
				<FormControl
					type="select"
					v-model="status"
					:options="[
						{ label: __('Pending'), value: 'Pending' },
						{ label: __('Approved'), value: 'Approved' },
						{ label: __('Rejected'), value: 'Rejected' },
						{ label: __('All'), value: '' },
					]"
					class="w-40"
				/>
			</div>

			<div v-if="requests.loading" class="flex justify-center p-10">
				<LoadingIndicator class="size-6 text-ink-gray-5" />
			</div>

			<div
				v-else-if="!selectedCourse && !canReviewAnyCourse"
				class="p-10 text-center text-sm italic text-ink-gray-5"
			>
				{{ __('Select a course to see its extension requests.') }}
			</div>

			<div
				v-else-if="!requests.data?.length"
				class="p-10 text-center text-sm italic text-ink-gray-5"
			>
				{{ __('No extension requests found.') }}
			</div>

			<div v-else class="border rounded-lg overflow-hidden">
				<table class="w-full text-sm">
					<thead class="bg-surface-gray-1">
						<tr>
							<th class="text-left p-2 font-medium text-ink-gray-6">{{ __('Student') }}</th>
							<th class="text-left p-2 font-medium text-ink-gray-6">{{ __('Course') }}</th>
							<th class="text-left p-2 font-medium text-ink-gray-6">{{ __('Item') }}</th>
							<th class="text-left p-2 font-medium text-ink-gray-6">{{ __('Reason') }}</th>
							<th class="text-left p-2 font-medium text-ink-gray-6">{{ __('Requested') }}</th>
							<th class="text-left p-2 font-medium text-ink-gray-6">{{ __('Status') }}</th>
							<th class="p-2"></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in requests.data" :key="row.name" class="border-t">
							<td class="p-2">{{ row.member_name }}</td>
							<td class="p-2">{{ row.course_title }}</td>
							<td class="p-2">
								{{ row.reference_title }}
								<span class="text-ink-gray-5">
									({{ row.reference_type === 'LMS Quiz' ? __('Quiz') : __('Assignment') }})
								</span>
							</td>
							<td class="p-2">{{ reasonLabel(row.reason_category) }}</td>
							<td class="p-2 whitespace-nowrap">{{ dayjs(row.creation).fromNow() }}</td>
							<td class="p-2">
								<Badge :theme="statusTheme(row.status)">{{ row.status }}</Badge>
							</td>
							<td class="p-2 text-right">
								<Button variant="outline" size="sm" @click="openReview(row)">
									{{ row.status === 'Pending' ? __('Review') : __('View') }}
								</Button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<Dialog
			v-model:open="showReview"
			:title="reviewing?.status === 'Pending' ? __('Review Request') : __('Request Details')"
			size="lg"
			:actions="reviewActions"
		>
			<template #default>
				<div v-if="reviewing" class="flex flex-col gap-4">
					<div class="grid grid-cols-2 gap-3 text-sm">
						<div>
							<div class="text-ink-gray-5">{{ __('Student') }}</div>
							<div class="text-ink-gray-9">{{ reviewing.member_name }}</div>
						</div>
						<div>
							<div class="text-ink-gray-5">{{ __('Item') }}</div>
							<div class="text-ink-gray-9">{{ reviewing.reference_title }}</div>
						</div>
						<div>
							<div class="text-ink-gray-5">{{ __('Deadline at time of request') }}</div>
							<div class="text-ink-gray-9">
								{{ reviewing.current_deadline ? dayjs(reviewing.current_deadline).format('lll') : '-' }}
							</div>
						</div>
						<div>
							<div class="text-ink-gray-5">{{ __('Reason') }}</div>
							<div class="text-ink-gray-9">{{ reasonLabel(reviewing.reason_category) }}</div>
						</div>
					</div>
					<div>
						<div class="text-ink-gray-5 text-sm mb-1">{{ __('Explanation') }}</div>
						<div class="text-ink-gray-9 text-sm whitespace-pre-wrap">
							{{ reviewing.explanation }}
						</div>
					</div>
					<a
						v-if="reviewing.evidence"
						:href="safeUrl(reviewing.evidence)"
						target="_blank"
						rel="noopener"
						class="text-ink-blue-3 text-sm underline w-fit"
					>
						{{ __('View evidence') }}
					</a>

					<template v-if="reviewing.status === 'Pending'">
						<div class="border-t -mx-5" />
						<FormControl
							type="datetime-local"
							:model-value="toDatetimeLocal(grantedUntil)"
							@update:model-value="(val) => (grantedUntil = fromDatetimeLocal(val))"
							:label="__('Grant access until')"
							variant="outline"
							:required="true"
						/>
						<FormControl
							v-if="reviewing.reference_type === 'LMS Quiz'"
							type="number"
							v-model="grantedExtraAttempts"
							min="0"
							:label="__('Extra attempts to grant (optional)')"
							variant="outline"
						/>
						<FormControl
							type="textarea"
							v-model="reviewNote"
							:label="__('Note to student (optional)')"
							variant="outline"
						/>
					</template>
					<template v-else>
						<div class="grid grid-cols-2 gap-3 text-sm">
							<div v-if="reviewing.granted_until">
								<div class="text-ink-gray-5">{{ __('Granted until') }}</div>
								<div class="text-ink-gray-9">{{ dayjs(reviewing.granted_until).format('lll') }}</div>
							</div>
							<div v-if="reviewing.reviewed_by">
								<div class="text-ink-gray-5">{{ __('Reviewed by') }}</div>
								<div class="text-ink-gray-9">{{ reviewing.reviewed_by }}</div>
							</div>
						</div>
						<div v-if="reviewing.review_note">
							<div class="text-ink-gray-5 text-sm mb-1">{{ __('Review note') }}</div>
							<div class="text-ink-gray-9 text-sm whitespace-pre-wrap">
								{{ reviewing.review_note }}
							</div>
						</div>
					</template>
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup>
import { Badge, Button, Dialog, FormControl, LoadingIndicator, createResource, toast, usePageMeta } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import Link from '@/components/Controls/Link.vue'
import { sessionStore } from '@/stores/session'
import { resourceErrorMessage, submitResource } from '@/utils/resource'
import { toDatetimeLocal, fromDatetimeLocal } from '@/utils/schedule'
import { safeUrl } from '@/utils/safeUrl'

const { brand } = sessionStore()
const route = useRoute()
const user = inject('$user')
const dayjs = inject('$dayjs')

const selectedCourse = ref(route.query.course || '')
const status = ref('Pending')

const canReviewAnyCourse = computed(
	() => Boolean(user.data?.is_moderator) || Boolean(user.data?.is_system_manager)
)

const requests = createResource({
	url: 'lms.lms.api.get_extension_requests',
	makeParams() {
		return {
			course: selectedCourse.value || undefined,
			status: status.value || undefined,
		}
	},
})

const reload = () => {
	if (selectedCourse.value || canReviewAnyCourse.value) requests.reload()
}

watch([selectedCourse, status], reload, { immediate: true })

const REASON_LABELS = {
	Sakit: __('Illness'),
	'Kendala Teknis': __('Technical Issue'),
	'Keperluan Keluarga atau Darurat': __('Family or Personal Emergency'),
	Lainnya: __('Other'),
}
const reasonLabel = (value) => REASON_LABELS[value] || value

const statusTheme = (value) => {
	if (value === 'Approved') return 'green'
	if (value === 'Rejected') return 'red'
	return 'orange'
}

const showReview = ref(false)
const reviewing = ref(null)
const grantedUntil = ref('')
const grantedExtraAttempts = ref(0)
const reviewNote = ref('')

const openReview = (row) => {
	reviewing.value = row
	grantedUntil.value = ''
	grantedExtraAttempts.value = 0
	reviewNote.value = ''
	showReview.value = true
}

const approveResource = createResource({ url: 'lms.lms.api.approve_extension_request', auto: false })
const rejectResource = createResource({ url: 'lms.lms.api.reject_extension_request', auto: false })

const approve = () =>
	submitResource(
		approveResource,
		{
			name: reviewing.value.name,
			granted_until: grantedUntil.value,
			granted_extra_attempts: grantedExtraAttempts.value || 0,
			review_note: reviewNote.value,
		},
		{
			validate() {
				if (!grantedUntil.value) return __('Please set a new deadline to grant.')
			},
			onSuccess() {
				toast.success(__('Extension request approved.'))
				showReview.value = false
				requests.reload()
			},
			onError(err) {
				toast.error(resourceErrorMessage(err))
			},
		}
	)

const reject = () =>
	submitResource(
		rejectResource,
		{ name: reviewing.value.name, review_note: reviewNote.value },
		{
			onSuccess() {
				toast.success(__('Extension request rejected.'))
				showReview.value = false
				requests.reload()
			},
			onError(err) {
				toast.error(resourceErrorMessage(err))
			},
		}
	)

const reviewActions = computed(() => {
	if (!reviewing.value || reviewing.value.status !== 'Pending') return []
	return [
		{
			label: __('Reject'),
			variant: 'outline',
			theme: 'red',
			loading: rejectResource.loading,
			onClick: reject,
		},
		{
			label: __('Approve'),
			variant: 'solid',
			loading: approveResource.loading,
			onClick: approve,
		},
	]
})

usePageMeta(() => {
	return {
		title: __('Extension Requests'),
		icon: brand.favicon,
	}
})
</script>
