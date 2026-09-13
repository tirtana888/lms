<template>
	<div>
		<PageHeader :title="__('Gradebook')" />
		<div class="p-5 space-y-4">
			<div class="flex flex-wrap items-center gap-3">
				<FormControl
					type="select"
					v-model="mode"
					:options="[
						{ label: __('By Course'), value: 'course' },
						{ label: __('By Batch'), value: 'batch' },
					]"
					class="w-36"
				/>
				<Link
					v-if="mode === 'course'"
					doctype="LMS Course"
					v-model="selectedCourse"
					:placeholder="__('Select a course')"
					class="w-64"
				/>
				<Link
					v-else
					doctype="LMS Batch"
					v-model="selectedBatch"
					:placeholder="__('Select a batch')"
					class="w-64"
				/>
			</div>

			<div
				v-if="gradebook.loading"
				class="flex justify-center p-10"
			>
				<LoadingIndicator class="size-6 text-ink-gray-5" />
			</div>

			<div
				v-else-if="!selectedCourse && !selectedBatch"
				class="p-10 text-center text-sm italic text-ink-gray-5"
			>
				{{ __('Select a course or a batch to see its gradebook.') }}
			</div>

			<div v-else-if="gradebook.data" class="overflow-x-auto border rounded-lg">
				<table class="w-full text-sm whitespace-nowrap">
					<thead>
						<tr class="border-b bg-surface-gray-1">
							<th class="sticky left-0 bg-surface-gray-1 text-left p-2">
								{{ __('Student') }}
							</th>
							<th
								v-for="quiz in gradebook.data.quizzes"
								:key="'qh-' + quiz.name"
								class="text-center p-2 min-w-[9rem]"
							>
								{{ quiz.title }}
							</th>
							<th
								v-for="assignment in gradebook.data.assignments"
								:key="'ah-' + assignment.name"
								class="text-center p-2 min-w-[9rem]"
							>
								{{ assignment.title }}
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="member in gradebook.data.members"
							:key="member.member"
							class="border-b last:border-0"
						>
							<td class="sticky left-0 bg-surface-base p-2 font-medium">
								{{ member.member_name || member.member }}
							</td>
							<td
								v-for="quiz in gradebook.data.quizzes"
								:key="'qc-' + quiz.name"
								class="text-center p-2"
							>
								<template v-if="quizCell(member.member, quiz.name)">
									{{ quizCell(member.member, quiz.name).percentage }}%
								</template>
								<span v-else class="text-ink-gray-4">—</span>
							</td>
							<td
								v-for="assignment in gradebook.data.assignments"
								:key="'ac-' + assignment.name"
								class="text-center p-2"
							>
								<Badge
									v-if="assignmentCell(member.member, assignment.name)"
									:label="assignmentCell(member.member, assignment.name).status"
									:theme="
										statusTheme(
											assignmentCell(member.member, assignment.name).status
										)
									"
								/>
								<span v-else class="text-ink-gray-4">—</span>
							</td>
						</tr>
					</tbody>
				</table>
				<div
					v-if="!gradebook.data.members?.length"
					class="p-6 text-center text-sm italic text-ink-gray-5"
				>
					{{ __('No students enrolled yet.') }}
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import {
	Badge,
	createResource,
	FormControl,
	LoadingIndicator,
	usePageMeta,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import Link from '@/components/Controls/Link.vue'
import { sessionStore } from '@/stores/session'

const { brand } = sessionStore()
const route = useRoute()

// Deep-linkable from CourseDashboard/AdminBatchDashboard via ?course=/?batch=.
const mode = ref(route.query.batch ? 'batch' : 'course')
const selectedCourse = ref(route.query.course || '')
const selectedBatch = ref(route.query.batch || '')

const gradebook = createResource({
	url: 'lms.lms.api.get_gradebook',
	makeParams() {
		return mode.value === 'batch'
			? { batch: selectedBatch.value }
			: { course: selectedCourse.value }
	},
})

watch(
	[mode, selectedCourse, selectedBatch],
	() => {
		const value = mode.value === 'batch' ? selectedBatch.value : selectedCourse.value
		if (value) gradebook.reload()
	},
	{ immediate: true }
)

const quizResultsByKey = computed(() => {
	const map = {}
	for (const row of gradebook.data?.quiz_results || []) {
		map[`${row.member}::${row.quiz}`] = row
	}
	return map
})
const assignmentResultsByKey = computed(() => {
	const map = {}
	for (const row of gradebook.data?.assignment_results || []) {
		map[`${row.member}::${row.assignment}`] = row
	}
	return map
})

const quizCell = (member, quiz) => quizResultsByKey.value[`${member}::${quiz}`]
const assignmentCell = (member, assignment) =>
	assignmentResultsByKey.value[`${member}::${assignment}`]

const statusTheme = (status) => {
	if (status === 'Pass') return 'green'
	if (status === 'Fail') return 'red'
	return 'gray'
}

usePageMeta(() => {
	return {
		title: __('Gradebook'),
		icon: brand.favicon,
	}
})
</script>
