<template>
	<div class="mt-7 mb-10 space-y-8">
		<div v-if="grades.data?.avg_quiz_score != null" class="flex items-center gap-2">
			<span class="text-lg-semibold text-ink-gray-9">
				{{ __('Average Quiz Score') }}
			</span>
			<Badge :label="`${grades.data.avg_quiz_score}%`" theme="blue" />
		</div>

		<div>
			<h2 class="mb-3 text-lg-semibold text-ink-gray-9">
				{{ __('Quizzes') }}
			</h2>
			<div
				v-if="grades.data?.quiz_submissions?.length"
				class="divide-y border rounded-lg"
			>
				<div
					v-for="submission in grades.data.quiz_submissions"
					:key="submission.name"
					class="flex items-center justify-between gap-4 p-3"
				>
					<div class="min-w-0">
						<div class="font-medium text-ink-gray-9 truncate">
							{{ submission.quiz_title || submission.quiz }}
						</div>
						<div class="text-sm text-ink-gray-6 truncate">
							{{ submission.course_title }}
						</div>
					</div>
					<div class="text-right shrink-0">
						<div class="font-medium text-ink-gray-9">
							{{ submission.percentage }}%
						</div>
						<div class="text-sm text-ink-gray-6">
							{{ dayjs(submission.creation).format('DD MMM YYYY') }}
						</div>
					</div>
				</div>
			</div>
			<div v-else class="text-sm italic text-ink-gray-5">
				{{ __('No quiz attempts yet.') }}
			</div>
		</div>

		<div>
			<h2 class="mb-3 text-lg-semibold text-ink-gray-9">
				{{ __('Assignments') }}
			</h2>
			<div
				v-if="grades.data?.assignment_submissions?.length"
				class="divide-y border rounded-lg"
			>
				<div
					v-for="submission in grades.data.assignment_submissions"
					:key="submission.name"
					class="flex items-center justify-between gap-4 p-3"
				>
					<div class="min-w-0">
						<div class="font-medium text-ink-gray-9 truncate">
							{{ submission.assignment_title || submission.assignment }}
						</div>
						<div class="text-sm text-ink-gray-6 truncate">
							{{ submission.course_title }}
						</div>
					</div>
					<Badge
						:label="submission.status"
						:theme="statusTheme(submission.status)"
					/>
				</div>
			</div>
			<div v-else class="text-sm italic text-ink-gray-5">
				{{ __('No assignment submissions yet.') }}
			</div>
		</div>

		<div>
			<h2 class="mb-3 text-lg-semibold text-ink-gray-9">
				{{ __('Certificates') }}
			</h2>
			<div
				v-if="grades.data?.certificates?.length"
				class="divide-y border rounded-lg"
			>
				<div
					v-for="certificate in grades.data.certificates"
					:key="certificate.course + certificate.issue_date"
					class="flex items-center justify-between gap-4 p-3"
				>
					<div class="min-w-0 truncate font-medium text-ink-gray-9">
						{{ certificate.course_title }}
					</div>
					<div class="text-sm text-ink-gray-6 shrink-0">
						{{ dayjs(certificate.issue_date).format('DD MMM YYYY') }}
					</div>
				</div>
			</div>
			<div v-else class="text-sm italic text-ink-gray-5">
				{{ __('No certificates yet.') }}
			</div>
		</div>
	</div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui'
import { inject } from 'vue'

const dayjs = inject('$dayjs')

// Never a `profile` prop's username: the backend is scoped to the calling
// user's own session regardless of whose profile page this is rendered
// under, so there is nothing to leak even if this route is reached from
// someone else's profile URL.
const grades = createResource({
	url: 'lms.lms.api.get_my_grades',
	auto: true,
	cache: ['my_grades'],
})

const statusTheme = (status) => {
	if (status === 'Pass') return 'green'
	if (status === 'Fail') return 'red'
	return 'gray'
}
</script>
