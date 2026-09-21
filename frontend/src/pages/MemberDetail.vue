<template>
	<div v-if="refusal" class="p-4 text-base text-ink-gray-6">
		{{ refusal }}
	</div>
	<template v-else>
		<PageHeader :breadcrumbs="breadcrumbs">
			<template #actions>
				<Dropdown v-if="memberRow" :options="manageOptions" placement="left">
					<Button variant="outline" :label="__('Manage')">
						<template #suffix>
							<span class="lucide-chevron-down size-4" aria-hidden="true" />
						</template>
					</Button>
				</Dropdown>
				<HeaderButton
					v-if="activeTab === 'Roles'"
					data-testid="member-save"
					:label="__('Save')"
					variant="solid"
					:loading="submitting"
					:disabled="!memberRow"
					@click="saveRoles()"
				/>
			</template>
		</PageHeader>

		<SkeletonLoader v-if="!memberRow" variant="form" class="mx-auto max-w-4xl px-5" />
		<div v-else class="mx-auto max-w-4xl px-5 pb-10">
			<div class="flex items-center gap-4">
				<Avatar size="xl" :image="memberRow.user_image" :label="memberRow.full_name" />
				<div>
					<h1 class="text-3xl-semibold text-ink-gray-9">
						{{ memberRow.full_name }}
					</h1>
					<div class="text-p-base text-ink-gray-6">{{ memberID }}</div>
				</div>
			</div>

			<div class="mb-6 mt-8 overflow-x-auto">
				<TabButtons :options="tabOptions" v-model="activeTab" class="w-fit" />
			</div>

			<div v-if="activeTab === 'Roles'" data-testid="member-roles" class="flex flex-col gap-2">
				<div class="grid md:grid-cols-2 gap-x-6 gap-y-3">
					<BooleanSwitch size="sm" :label="__('Student')" v-model="roles.lms_student" />
					<BooleanSwitch
						size="sm"
						:label="__('Course Creator')"
						v-model="roles.course_creator"
					/>
					<BooleanSwitch
						size="sm"
						:label="__('Evaluator')"
						v-model="roles.batch_evaluator"
					/>
					<BooleanSwitch size="sm" :label="__('Moderator')" v-model="roles.moderator" />
				</div>
			</div>

			<!-- Every other tab shares one loading state — there's a single
			     get_member_overview fetch behind all six of them, not one per
			     tab, so "loading" isn't a per-tab thing to represent separately. -->
			<div v-else data-testid="member-tab-panel">
				<div v-if="overviewFetch.loading" class="text-p-sm text-ink-gray-5">
					{{ __('Loading...') }}
				</div>
				<template v-else-if="overview">
					<div v-if="activeTab === 'Overview'" data-testid="member-overview" class="space-y-6">
					<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<div
							v-for="stat in overviewStats"
							:key="stat.label"
							class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3"
						>
							<span :class="stat.icon" class="size-4 text-ink-gray-6" aria-hidden="true" />
							<div class="mt-2 text-xl-semibold text-ink-gray-9">{{ stat.value }}</div>
							<div class="text-p-sm text-ink-gray-6">{{ stat.label }}</div>
						</div>
					</div>

					<div class="grid grid-cols-2 gap-4 text-p-sm sm:grid-cols-3">
						<div>
							<div class="text-ink-gray-5">{{ __('Last login') }}</div>
							<div class="text-ink-gray-9">{{ formatDate(overview.last_login) }}</div>
						</div>
						<div>
							<div class="text-ink-gray-5">{{ __('Last active') }}</div>
							<div class="text-ink-gray-9">{{ formatDate(overview.last_active) }}</div>
						</div>
						<div>
							<div class="text-ink-gray-5">{{ __('Last IP') }}</div>
							<div class="text-ink-gray-9">{{ overview.last_ip || '—' }}</div>
						</div>
					</div>

					<MemberStudyTime :member="memberID" />

					<div>
						<div class="text-p-sm-medium text-ink-gray-7 mb-2">{{ __('Tags') }}</div>
						<div class="flex flex-wrap items-center gap-1.5">
							<Badge
								v-for="tag in overview.tags"
								:key="tag"
								theme="gray"
								variant="subtle"
								class="flex items-center gap-1"
							>
								{{ tag }}
								<button
									type="button"
									class="lucide-x size-3 text-ink-gray-5 hover:text-ink-gray-8"
									:aria-label="__('Remove tag {0}').format(tag)"
									@click="handleRemoveTag(tag)"
								/>
							</Badge>
							<FormControl
								v-model="newTag"
								type="text"
								:placeholder="__('Add a tag')"
								class="w-36"
								@keyup.enter="handleAddTag()"
							/>
							<Button
								variant="subtle"
								:label="__('Add')"
								data-testid="add-tag"
								@click="handleAddTag()"
							/>
						</div>
					</div>

					<div>
						<div class="text-p-sm-medium text-ink-gray-7 mb-2">{{ __('Notes') }}</div>
						<div v-if="overview.notes.length" class="mb-3 space-y-2">
							<div
								v-for="note in overview.notes"
								:key="note.name"
								class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3 text-p-sm"
							>
								<div class="flex items-start justify-between gap-2">
									<p class="whitespace-pre-wrap text-ink-gray-8">{{ note.content }}</p>
									<button
										type="button"
										class="lucide-trash-2 size-3.5 shrink-0 text-ink-gray-4 hover:text-ink-gray-7"
										:aria-label="__('Delete note')"
										@click="handleDeleteNote(note.name)"
									/>
								</div>
								<div class="mt-1.5 text-p-xs text-ink-gray-5">
									{{ note.comment_by }} · {{ formatDate(note.creation, true) }}
								</div>
							</div>
						</div>
						<div v-else class="mb-3 text-p-sm text-ink-gray-5">{{ __('No notes yet.') }}</div>
						<div class="flex items-start gap-2">
							<FormControl
								v-model="newNote"
								type="textarea"
								:placeholder="__('Add a note')"
								class="flex-1"
							/>
							<Button
								variant="solid"
								:label="__('Add')"
								:loading="addingNote"
								data-testid="add-note"
								@click="handleAddNote()"
							/>
						</div>
					</div>
				</div>

				<div v-else-if="activeTab === 'Courses'" data-testid="member-courses">
					<div v-if="!overview.enrollments.length" class="text-p-sm text-ink-gray-5">{{ __('No enrollments yet.') }}</div>
					<div v-else>
						<div
							v-for="row in overview.enrollments"
							:key="row.course"
							class="border-b border-outline-gray-1 text-p-sm last:border-0"
						>
							<div class="flex items-center gap-3 py-3">
								<button
									type="button"
									class="flex min-w-0 flex-1 items-center gap-2 text-left"
									:aria-expanded="Boolean(expandedCourses[row.course || ''])"
									@click="toggleCourse(row.course)"
								>
									<span
										class="lucide-chevron-right size-4 shrink-0 text-ink-gray-5 transition-transform"
										:class="{ 'rotate-90': expandedCourses[row.course || ''] }"
										aria-hidden="true"
									/>
									<span class="truncate text-ink-gray-8">{{ row.course_title }}</span>
								</button>
								<div class="w-32 shrink-0">
									<ProgressBar :progress="Math.round(row.progress ?? 0)" class="!mx-0" />
								</div>
								<span class="w-10 shrink-0 text-right text-ink-gray-6">{{ Math.round(row.progress ?? 0) }}%</span>
								<Dropdown :options="progressOptions(row.course, 'course', row.course, row.course_title)">
									<Button
										variant="ghost"
										:aria-label="__('Progress actions for {0}').format(row.course_title)"
									>
										<template #icon>
											<span class="lucide-more-horizontal size-4" aria-hidden="true" />
										</template>
									</Button>
								</Dropdown>
							</div>

							<div v-if="expandedCourses[row.course || '']" class="pb-4 pl-6">
								<div v-if="!courseOutlines[row.course || '']" class="text-p-sm text-ink-gray-5">
									{{ __('Loading...') }}
								</div>
								<div
									v-else-if="!courseOutlines[row.course || '']?.chapters.length"
									class="text-p-sm text-ink-gray-5"
								>
									{{ __('This course has no lessons yet.') }}
								</div>
								<div v-else class="space-y-3">
									<div
										v-for="chapter in courseOutlines[row.course || '']?.chapters"
										:key="chapter.name"
										class="rounded-lg border border-outline-gray-2"
									>
										<div class="flex items-center gap-2 border-b border-outline-gray-1 bg-surface-gray-1 px-3 py-1.5">
											<span class="min-w-0 flex-1 truncate text-p-sm-medium text-ink-gray-8">{{ chapter.title }}</span>
											<span class="shrink-0 text-p-xs text-ink-gray-5">
												{{ completedCount(chapter) }}/{{ chapter.lessons.length }}
											</span>
											<Dropdown :options="progressOptions(row.course, 'chapter', chapter.name, chapter.title)">
												<Button
													variant="ghost"
													:aria-label="__('Progress actions for {0}').format(chapter.title)"
												>
													<template #icon>
														<span class="lucide-more-horizontal size-4" aria-hidden="true" />
													</template>
												</Button>
											</Dropdown>
										</div>
										<div
											v-for="lesson in chapter.lessons"
											:key="lesson.name"
											class="flex items-start gap-2 border-b border-outline-gray-1 px-3 py-2 last:border-0"
										>
											<span
												:class="lessonIcon(lesson.status)"
												class="mt-0.5 size-4 shrink-0"
												role="img"
												:aria-label="lessonStatusLabel(lesson.status)"
												:title="lessonStatusLabel(lesson.status)"
											/>
											<div class="min-w-0 flex-1">
												<div class="truncate text-ink-gray-8">{{ lesson.title }}</div>
												<div
													v-if="lesson.quizzes.length || lesson.assignments.length"
													class="mt-1 flex flex-wrap gap-1.5"
												>
													<Badge
														v-for="quiz in lesson.quizzes"
														:key="'quiz-' + quiz.name"
														variant="subtle"
														:theme="quiz.percentage == null ? 'gray' : quiz.passed ? 'green' : 'red'"
													>
														{{ __('Quiz') }}: {{ quiz.title }} ·
														{{ quiz.percentage == null ? __('Not attempted') : Math.round(quiz.percentage) + '%' }}
													</Badge>
													<Badge
														v-for="assignment in lesson.assignments"
														:key="'assignment-' + assignment.name"
														variant="subtle"
														:theme="assignmentTheme(assignment.status)"
													>
														{{ __('Assignment') }}: {{ assignment.title }} ·
														{{ assignment.status ? __(assignment.status) : __('Not submitted') }}
													</Badge>
												</div>
											</div>
											<Dropdown :options="progressOptions(row.course, 'lesson', lesson.name, lesson.title)">
												<Button
													variant="ghost"
													:aria-label="__('Progress actions for {0}').format(lesson.title)"
												>
													<template #icon>
														<span class="lucide-more-horizontal size-4" aria-hidden="true" />
													</template>
												</Button>
											</Dropdown>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div v-else-if="activeTab === 'Quizzes'" data-testid="member-quizzes">
					<div v-if="!overview.quiz_submissions.length" class="text-p-sm text-ink-gray-5">{{ __('No quiz submissions yet.') }}</div>
					<div v-else>
						<div
							v-for="(row, idx) in overview.quiz_submissions"
							:key="idx"
							class="flex items-center justify-between border-b border-outline-gray-1 py-3 text-p-sm last:border-0"
						>
							<span class="text-ink-gray-8">{{ row.quiz }}</span>
							<span class="text-ink-gray-6">{{ Math.round(row.percentage ?? 0) }}%</span>
						</div>
					</div>
				</div>

				<div v-else-if="activeTab === 'Certificates'" data-testid="member-certificates">
					<div v-if="!overview.certificates.length" class="text-p-sm text-ink-gray-5">{{ __('No certificates yet.') }}</div>
					<div v-else>
						<div
							v-for="row in overview.certificates"
							:key="row.course"
							class="flex items-center justify-between border-b border-outline-gray-1 py-3 text-p-sm last:border-0"
						>
							<span class="text-ink-gray-8">{{ row.course_title }}</span>
							<span class="text-ink-gray-6">{{ formatDate(row.issue_date) }}</span>
						</div>
					</div>
				</div>

				<div v-else-if="activeTab === 'Programs'" data-testid="member-programs">
					<div v-if="!overview.programs.length" class="text-p-sm text-ink-gray-5">{{ __('Not enrolled in any program.') }}</div>
					<div v-else>
						<div
							v-for="row in overview.programs"
							:key="row.program"
							class="flex items-center gap-3 border-b border-outline-gray-1 py-3 text-p-sm last:border-0"
						>
							<span class="min-w-0 flex-1 truncate text-ink-gray-8">{{ row.program }}</span>
							<div class="w-32 shrink-0">
								<ProgressBar :progress="Math.round(row.progress ?? 0)" class="!mx-0" />
							</div>
							<span class="w-10 shrink-0 text-right text-ink-gray-6">{{ Math.round(row.progress ?? 0) }}%</span>
						</div>
					</div>
				</div>

				<div v-else-if="activeTab === 'Activity'" data-testid="member-activity">
					<div v-if="!overview.recent_logins.length" class="text-p-sm text-ink-gray-5">{{ __('No recent logins.') }}</div>
					<div v-else>
						<div
							v-for="(row, idx) in overview.recent_logins"
							:key="idx"
							class="flex items-center gap-3 border-b border-outline-gray-1 py-3 text-p-sm last:border-0"
						>
							<span class="lucide-log-in size-4 shrink-0 text-ink-gray-4" aria-hidden="true" />
							<span class="flex-1 text-ink-gray-8">{{ formatDate(row.creation, true) }}</span>
							<span class="text-ink-gray-5">{{ row.ip_address }}</span>
						</div>
					</div>
				</div>
			</template>
			</div>
		</div>
	</template>
</template>
<script setup lang="ts">
import { Avatar, Badge, Button, call, createResource, Dropdown, FormControl, TabButtons, toast } from 'frappe-ui'
import ProgressBar from '@/components/ProgressBar.vue'
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import MemberStudyTime from '@/components/MemberStudyTime.vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { notifyMembersChanged } from '@/stores/members'
import { cleanError } from '@/utils'
import { createDialog } from '@/utils/dialogs'
import type { Breadcrumb, Resource, SessionUser } from '@/types'

type MemberRow = {
	name: string
	full_name: string
	user_image?: string
	roles?: string[]
	enabled?: number
}

type MemberOverviewRow = {
	course?: string
	course_title?: string
	progress?: number
	quiz?: string
	percentage?: number
	issue_date?: string
	program?: string
	creation?: string
	ip_address?: string
}

type MemberNote = { name: string; content: string; comment_by: string; creation: string }

type ProgressScope = 'course' | 'chapter' | 'lesson'
type QuizResult = { name: string; title: string; percentage: number | null; passed: boolean }
type AssignmentResult = { name: string; title: string; status: string | null }
type OutlineLesson = {
	name: string
	title: string
	status: string | null
	quizzes: QuizResult[]
	assignments: AssignmentResult[]
}
type OutlineChapter = { name: string; title: string; lessons: OutlineLesson[] }
type CourseOutline = { progress: number; chapters: OutlineChapter[] }
type ProgressResult = { changed: number; progress: number; notes: MemberNote[] }

type MemberOverview = {
	last_login: string | null
	last_active: string | null
	last_ip: string | null
	tags: string[]
	notes: MemberNote[]
	enrollments: MemberOverviewRow[]
	quiz_submissions: MemberOverviewRow[]
	avg_quiz_score: number | null
	certificates: MemberOverviewRow[]
	programs: MemberOverviewRow[]
	recent_logins: MemberOverviewRow[]
}

type DetailTab =
	| 'Overview'
	| 'Courses'
	| 'Quizzes'
	| 'Certificates'
	| 'Programs'
	| 'Activity'
	| 'Roles'

const props = defineProps<{ memberID: string }>()

const user = inject<SessionUser>('$user')!
const route = useRoute()

// A page reached by a real URL — same gate as the rest of member management
// (MEMBER_ADMIN_ROLES on get_member/get_member_overview/save_role, lms/lms/api.py).
const refusal = computed(() => {
	if ((window as Window & { read_only_mode?: boolean }).read_only_mode)
		return __('This site is in read-only mode.')
	if (!user.data?.is_moderator && !user.data?.is_system_manager)
		return __('You are not permitted to manage members.')
	return ''
})

const tabOptions: { label: string; value: DetailTab }[] = [
	{ label: __('Overview'), value: 'Overview' },
	{ label: __('Courses'), value: 'Courses' },
	{ label: __('Quizzes'), value: 'Quizzes' },
	{ label: __('Certificates'), value: 'Certificates' },
	{ label: __('Programs'), value: 'Programs' },
	{ label: __('Activity'), value: 'Activity' },
	{ label: __('Roles'), value: 'Roles' },
]

// Members.vue's name link opens straight onto Overview; the "..." menu's Edit
// member opens onto Roles instead.
const activeTab = ref<DetailTab>(route.query.tab === 'Roles' ? 'Roles' : 'Overview')

const ROLE_MAP: Record<string, string> = {
	moderator: 'Moderator',
	course_creator: 'Course Creator',
	batch_evaluator: 'Batch Evaluator',
	lms_student: 'LMS Student',
}

const roles = reactive({
	moderator: false,
	course_creator: false,
	batch_evaluator: false,
	lms_student: false,
})
const initialRoles = reactive({ ...roles })
const submitting = ref(false)

const memberFetch = createResource({
	url: 'lms.lms.api.get_member',
	makeParams: () => ({ member: props.memberID }),
	auto: false,
}) as unknown as Resource<MemberRow | null>

onMounted(() => {
	if (!refusal.value) memberFetch.fetch()
})

const memberRow = computed<MemberRow | null>(() => memberFetch.data ?? null)

watch(
	memberRow,
	(found) => {
		const current = found?.roles ?? []
		for (const key of Object.keys(ROLE_MAP) as (keyof typeof roles)[]) {
			roles[key] = current.includes(ROLE_MAP[key])
			initialRoles[key] = roles[key]
		}
	},
	{ immediate: true }
)

const errorMessage = (err: { messages?: string[] }, fallback: string): string =>
	cleanError(err.messages?.[0]) || fallback

async function resendInvitation() {
	try {
		// Frappe's own public "forgot password" endpoint — deliberately
		// permission-check-free (silently no-ops for a disabled/nonexistent
		// user, same generic response either way) — doubles as a resend of the
		// original "set your password" invitation email.
		await call('frappe.core.doctype.user.user.reset_password', { user: props.memberID })
		toast.success(__('Invitation email sent'))
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to send the invitation')))
	}
}

async function handleSuspend() {
	try {
		await call('lms.lms.api.suspend_member', { member: props.memberID })
		if (memberFetch.data) memberFetch.data.enabled = 0
		toast.success(__('Member suspended'))
		notifyMembersChanged()
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to suspend this member')))
	}
}

async function handleUnsuspend() {
	try {
		await call('lms.lms.api.unsuspend_member', { member: props.memberID })
		if (memberFetch.data) memberFetch.data.enabled = 1
		toast.success(__('Member unsuspended'))
		notifyMembersChanged()
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to unsuspend this member')))
	}
}

const manageOptions = computed(() => [
	{
		label: __('Resend invitation'),
		icon: 'lucide-mail',
		onClick: resendInvitation,
	},
	memberRow.value?.enabled
		? { label: __('Suspend user'), icon: 'lucide-ban', theme: 'red', onClick: handleSuspend }
		: {
				label: __('Unsuspend user'),
				icon: 'lucide-check-circle',
				onClick: handleUnsuspend,
		  },
])

const overviewFetch = createResource({
	url: 'lms.lms.api.get_member_overview',
	makeParams: () => ({ member: props.memberID }),
	auto: false,
}) as unknown as Resource<MemberOverview | null>

const overview = computed<MemberOverview | null>(() => overviewFetch.data ?? null)

const overviewStats = computed(() => {
	const data = overview.value
	if (!data) return []
	return [
		{ icon: 'lucide-book-open', label: __('Courses'), value: data.enrollments.length },
		{ icon: 'lucide-award', label: __('Certificates'), value: data.certificates.length },
		{ icon: 'lucide-route', label: __('Programs'), value: data.programs.length },
		{
			icon: 'lucide-percent',
			label: __('Avg. quiz score'),
			value: data.avg_quiz_score != null ? Math.round(data.avg_quiz_score) + '%' : '—',
		},
	]
})

// Lazy + immediate: most visits land on Overview directly (the name link),
// but a visit that starts on Roles (the "..." menu) should still fetch it
// the moment someone switches to ANY of the other six tabs — they all read
// from this same `overview` object — not only on a later change.
watch(
	activeTab,
	(tab) => {
		if (tab !== 'Roles' && !overviewFetch.data && !overviewFetch.loading) {
			overviewFetch.fetch()
		}
	},
	{ immediate: true }
)

function formatDate(value: string | null | undefined, withTime = false): string {
	if (!value) return __('Never')
	const date = new Date(value.replace(' ', 'T'))
	if (Number.isNaN(date.getTime())) return value
	return withTime ? date.toLocaleString() : date.toLocaleDateString()
}

const newTag = ref('')

async function handleAddTag() {
	const tag = newTag.value.trim()
	if (!tag || !overviewFetch.data) return
	try {
		overviewFetch.data.tags = await call('lms.lms.api.add_member_tag', {
			member: props.memberID,
			tag,
		})
		newTag.value = ''
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to add tag')))
	}
}

async function handleRemoveTag(tag: string) {
	if (!overviewFetch.data) return
	try {
		overviewFetch.data.tags = await call('lms.lms.api.remove_member_tag', {
			member: props.memberID,
			tag,
		})
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to remove tag')))
	}
}

const newNote = ref('')
const addingNote = ref(false)

async function handleAddNote() {
	const content = newNote.value.trim()
	if (!content || !overviewFetch.data) return
	addingNote.value = true
	try {
		overviewFetch.data.notes = await call('lms.lms.api.add_member_note', {
			member: props.memberID,
			content,
		})
		newNote.value = ''
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to add note')))
	} finally {
		addingNote.value = false
	}
}

async function handleDeleteNote(name: string) {
	if (!overviewFetch.data) return
	try {
		overviewFetch.data.notes = await call('lms.lms.api.delete_member_note', { name })
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to delete note')))
	}
}

const expandedCourses = reactive<Record<string, boolean>>({})
const courseOutlines = reactive<Record<string, CourseOutline | null>>({})
const progressBusy = ref(false)

async function loadCourseOutline(course: string) {
	try {
		courseOutlines[course] = await call('lms.lms.api.get_member_course_progress', {
			member: props.memberID,
			course,
		})
	} catch (err: any) {
		expandedCourses[course] = false
		toast.error(errorMessage(err, __('Unable to load course progress')))
	}
}

function toggleCourse(course: string | undefined) {
	if (!course) return
	expandedCourses[course] = !expandedCourses[course]
	if (expandedCourses[course] && !courseOutlines[course]) loadCourseOutline(course)
}

const completedCount = (chapter: OutlineChapter) =>
	chapter.lessons.filter((lesson) => lesson.status === 'Complete').length

function lessonIcon(status: string | null) {
	if (status === 'Complete') return 'lucide-check-circle text-ink-green-3'
	if (status) return 'lucide-circle-dashed text-ink-amber-3'
	return 'lucide-circle text-ink-gray-4'
}

function lessonStatusLabel(status: string | null) {
	if (status === 'Complete') return __('Completed')
	if (status) return __('In progress')
	return __('Not started')
}

function assignmentTheme(status: string | null) {
	if (status === 'Pass') return 'green'
	if (status === 'Fail') return 'red'
	if (status) return 'orange'
	return 'gray'
}

async function runProgressAction(
	course: string | undefined,
	action: 'complete' | 'reset',
	scope: ProgressScope,
	target: string | undefined
) {
	if (!course || !target || progressBusy.value) return
	progressBusy.value = true
	try {
		const result: ProgressResult = await call('lms.lms.api.set_member_progress', {
			member: props.memberID,
			course,
			action,
			scope,
			target,
		})
		const enrollment = overviewFetch.data?.enrollments.find((row) => row.course === course)
		if (enrollment) enrollment.progress = result.progress
		if (overviewFetch.data) overviewFetch.data.notes = result.notes
		if (courseOutlines[course]) await loadCourseOutline(course)
		if (!result.changed) toast.success(__('Nothing to change'))
		else if (action === 'complete')
			toast.success(__('{0} lessons marked complete').format(result.changed))
		else toast.success(__('{0} lessons reset').format(result.changed))
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to update progress')))
	} finally {
		progressBusy.value = false
	}
}

function confirmReset(
	course: string | undefined,
	scope: ProgressScope,
	target: string | undefined,
	label: string | undefined
) {
	createDialog({
		title: __('Reset progress?'),
		message: __(
			'Progress for "{0}" will be cleared. Quiz and assignment submissions are kept, and this is recorded in the member notes.'
		).format(label || ''),
		actions: [
			{
				label: __('Reset'),
				theme: 'red',
				variant: 'solid',
				onClick(close: () => void) {
					close()
					runProgressAction(course, 'reset', scope, target)
				},
			},
		],
	})
}

function progressOptions(
	course: string | undefined,
	scope: ProgressScope,
	target: string | undefined,
	label: string | undefined
) {
	const markLabel = {
		course: __('Mark course complete'),
		chapter: __('Mark chapter complete'),
		lesson: __('Mark lesson complete'),
	}[scope]
	const resetLabel = {
		course: __('Reset course progress'),
		chapter: __('Reset chapter progress'),
		lesson: __('Reset lesson progress'),
	}[scope]
	return [
		{
			label: markLabel,
			icon: 'lucide-check-circle',
			onClick: () => runProgressAction(course, 'complete', scope, target),
		},
		{
			label: resetLabel,
			icon: 'lucide-rotate-ccw',
			theme: 'red',
			onClick: () => confirmReset(course, scope, target, label),
		},
	]
}

const saveRoles = async () => {
	if (refusal.value || submitting.value || !memberRow.value) return
	submitting.value = true
	try {
		for (const key of Object.keys(ROLE_MAP) as (keyof typeof roles)[]) {
			if (roles[key] !== initialRoles[key]) {
				await call('lms.lms.api.save_role', {
					user: props.memberID,
					role: ROLE_MAP[key],
					value: roles[key] ? 1 : 0,
				})
				// This page stays mounted after a save (it's a real page, not a
				// modal that closes) — without re-baselining here, an unchanged
				// second Save click would re-diff against the stale snapshot and
				// re-send every role this one just saved.
				initialRoles[key] = roles[key]
			}
		}
		toast.success(__('Member updated'))
		notifyMembersChanged()
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to update member')))
	} finally {
		submitting.value = false
	}
}

const breadcrumbs = computed<Breadcrumb[]>(() => [
	{ label: __('Users'), route: { name: 'Members' } },
	{ label: memberRow.value?.full_name || props.memberID },
])
</script>
