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

			<div v-else-if="gradebook.data" class="border rounded-lg overflow-hidden">
				<div class="bg-surface-gray-7 text-white px-4 py-2 text-base font-medium">
					{{ __('Gradebook') }}
				</div>
				<div class="overflow-x-auto">
					<table class="border-collapse text-sm">
						<thead>
							<tr>
								<th
									class="sticky left-0 z-10 bg-surface-base text-left p-2 align-bottom w-36 border-b"
								>
									{{ __('Student') }}
								</th>
								<th
									v-for="quiz in gradebook.data.quizzes"
									:key="'qh-' + quiz.name"
									class="relative p-0 w-10 border-b"
									style="height: 6.5rem"
								>
									<div
										class="absolute bottom-1.5 left-1/2 whitespace-nowrap text-xs font-medium text-ink-gray-6"
										style="transform: translateX(-4px) rotate(-40deg); transform-origin: left bottom"
									>
										{{ quiz.title }}
									</div>
								</th>
								<th
									v-for="assignment in gradebook.data.assignments"
									:key="'ah-' + assignment.name"
									class="relative p-0 w-10 border-b"
									style="height: 6.5rem"
								>
									<div
										class="absolute bottom-1.5 left-1/2 whitespace-nowrap text-xs font-medium text-ink-gray-6"
										style="transform: translateX(-4px) rotate(-40deg); transform-origin: left bottom"
									>
										{{ assignment.title }}
									</div>
								</th>
								<th class="text-center p-2 align-bottom w-14 border-b font-medium">
									{{ __('Average') }}
								</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="member in gradebook.data.members"
								:key="member.member"
								class="border-b last:border-0"
							>
								<td
									class="sticky left-0 bg-surface-base p-2 font-medium text-ink-gray-9"
								>
									{{ member.member_name || member.member }}
								</td>
								<td
									v-for="quiz in gradebook.data.quizzes"
									:key="'qc-' + quiz.name"
									class="text-center p-1"
								>
									<FormControl
										v-if="editingKey === cellKey(member.member, quiz.name)"
										type="number"
										:model-value="editValue"
										autofocus
										class="w-14 mx-auto"
										@update:model-value="(v) => (editValue = v)"
										@blur="saveScore(member.member, quiz.name)"
										@keyup.enter="$event.target.blur()"
									/>
									<span
										v-else-if="quizCell(member.member, quiz.name)"
										class="cursor-pointer hover:underline"
										:title="__('Click to edit')"
										@click="startEdit(member.member, quiz.name)"
									>
										<span
											v-if="quizPassed(quizCell(member.member, quiz.name)) != null"
											class="inline-block size-1.5 rounded-full me-1"
											:class="
												quizPassed(quizCell(member.member, quiz.name))
													? 'bg-surface-green-7'
													: 'bg-surface-red-7'
											"
										/>
										{{ quizCell(member.member, quiz.name).percentage }}
									</span>
									<span v-else class="text-ink-gray-4">—</span>
								</td>
								<td
									v-for="assignment in gradebook.data.assignments"
									:key="'ac-' + assignment.name"
									class="text-center p-1"
								>
									<template v-if="assignmentCell(member.member, assignment.name)">
										<span
											v-if="
												['Pass', 'Fail'].includes(
													assignmentCell(member.member, assignment.name).status
												)
											"
											class="inline-block size-1.5 rounded-full me-1"
											:class="
												assignmentCell(member.member, assignment.name).status ===
												'Pass'
													? 'bg-surface-green-7'
													: 'bg-surface-red-7'
											"
										/>
										{{ assignmentCell(member.member, assignment.name).status }}
									</template>
									<span v-else class="text-ink-gray-4">—</span>
								</td>
								<td class="text-center p-1 font-medium text-ink-gray-9">
									<template v-if="averageFor(member.member) != null">
										{{ averageFor(member.member) }}
									</template>
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
	</div>
</template>
<script setup>
import {
	createResource,
	FormControl,
	LoadingIndicator,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { ref, watch } from 'vue'
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

const cellKey = (member, item) => `${member}::${item}`

const quizCell = (member, quiz) =>
	gradebook.data?.quiz_results?.find((r) => r.member === member && r.quiz === quiz)
const assignmentCell = (member, assignment) =>
	gradebook.data?.assignment_results?.find(
		(r) => r.member === member && r.assignment === assignment
	)

// null = no pass/fail threshold set on the quiz, so no dot is shown at all
// rather than an arbitrary color.
const quizPassed = (result) => {
	if (!result || result.passing_percentage == null) return null
	return result.percentage >= result.passing_percentage
}

const averageFor = (member) => {
	const scores = (gradebook.data?.quizzes || [])
		.map((quiz) => quizCell(member, quiz.name)?.percentage)
		.filter((p) => p != null)
	if (!scores.length) return null
	return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
}

// Editing one quiz score at a time - click a cell to turn it into a number
// input, blur/enter to save. Assignment grading stays on its own existing
// page (linked from the submission, not editable inline here) since it
// already has a full grading UI (feedback, attachments) a single cell can't
// hold.
const editingKey = ref(null)
const editValue = ref('')

const startEdit = (member, quiz) => {
	const cell = quizCell(member, quiz)
	if (!cell) return
	editingKey.value = cellKey(member, quiz)
	editValue.value = cell.percentage
}

const updateScore = createResource({
	url: 'lms.lms.api.update_quiz_score',
	auto: false,
})

const saveScore = async (member, quiz) => {
	const key = cellKey(member, quiz)
	if (editingKey.value !== key) return
	editingKey.value = null
	const cell = quizCell(member, quiz)
	const newPercentage = Number(editValue.value)
	if (!cell || Number.isNaN(newPercentage) || newPercentage === cell.percentage) return
	try {
		const result = await updateScore.submit({
			submission: cell.name,
			percentage: newPercentage,
		})
		cell.percentage = result.percentage
		cell.score = result.score
	} catch (err) {
		toast.error(err.messages?.[0] || __('Could not update the score'))
	}
}

usePageMeta(() => {
	return {
		title: __('Gradebook'),
		icon: brand.favicon,
	}
})
</script>
