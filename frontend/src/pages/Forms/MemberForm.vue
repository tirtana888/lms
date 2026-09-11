<template>
	<FormShell
		:title="isEdit ? __('Edit Member') : __('Add New Member')"
		size="lg"
		@close="close"
	>
		<template #default>
			<div v-if="refusal" class="p-4 text-base text-ink-gray-6">
				{{ refusal }}
			</div>
			<template v-else>
				<TabButtons
					v-if="isEdit"
					class="mb-4 inline-block"
					:options="[
						{ label: __('Roles'), value: 'Roles' },
						{ label: __('Overview'), value: 'Overview' },
					]"
					v-model="activeTab"
				/>
				<div
					v-if="activeTab === 'Overview' && isEdit"
					data-testid="member-overview"
					class="space-y-5"
				>
					<div v-if="overviewFetch.loading" class="text-p-sm text-ink-gray-5">
						{{ __('Loading...') }}
					</div>
					<template v-else-if="overview">
						<div class="grid grid-cols-2 gap-4 text-p-sm">
							<div>
								<div class="text-ink-gray-5">{{ __('Last login') }}</div>
								<div class="text-ink-gray-9">
									{{ formatDate(overview.last_login) }}
								</div>
							</div>
							<div>
								<div class="text-ink-gray-5">{{ __('Last active') }}</div>
								<div class="text-ink-gray-9">
									{{ formatDate(overview.last_active) }}
								</div>
							</div>
							<div>
								<div class="text-ink-gray-5">{{ __('Last IP') }}</div>
								<div class="text-ink-gray-9">{{ overview.last_ip || '—' }}</div>
							</div>
							<div>
								<div class="text-ink-gray-5">{{ __('Avg. quiz score') }}</div>
								<div class="text-ink-gray-9">
									{{
										overview.avg_quiz_score != null
											? overview.avg_quiz_score + '%'
											: '—'
									}}
								</div>
							</div>
						</div>

						<div v-if="overview.tags.length" class="flex flex-wrap gap-1.5">
							<span
								v-for="tag in overview.tags"
								:key="tag"
								class="rounded bg-surface-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-7"
							>
								{{ tag }}
							</span>
						</div>

						<div>
							<div class="text-p-sm-medium text-ink-gray-7 mb-2">
								{{ __('Courses') }} ({{ overview.enrollments.length }})
							</div>
							<div
								v-if="!overview.enrollments.length"
								class="text-p-sm text-ink-gray-5"
							>
								{{ __('No enrollments yet.') }}
							</div>
							<div v-else class="space-y-1.5">
								<div
									v-for="row in overview.enrollments"
									:key="row.course"
									class="flex items-center justify-between text-p-sm"
								>
									<span class="text-ink-gray-8">{{ row.course_title }}</span>
									<span class="text-ink-gray-5">{{ row.progress }}%</span>
								</div>
							</div>
						</div>

						<div>
							<div class="text-p-sm-medium text-ink-gray-7 mb-2">
								{{ __('Quiz submissions') }} ({{ overview.quiz_submissions.length }})
							</div>
							<div
								v-if="!overview.quiz_submissions.length"
								class="text-p-sm text-ink-gray-5"
							>
								{{ __('No quiz submissions yet.') }}
							</div>
							<div v-else class="space-y-1.5">
								<div
									v-for="(row, idx) in overview.quiz_submissions"
									:key="idx"
									class="flex items-center justify-between text-p-sm"
								>
									<span class="text-ink-gray-8">{{ row.quiz }}</span>
									<span class="text-ink-gray-5">{{ row.percentage }}%</span>
								</div>
							</div>
						</div>

						<div>
							<div class="text-p-sm-medium text-ink-gray-7 mb-2">
								{{ __('Certificates') }} ({{ overview.certificates.length }})
							</div>
							<div
								v-if="!overview.certificates.length"
								class="text-p-sm text-ink-gray-5"
							>
								{{ __('No certificates yet.') }}
							</div>
							<div v-else class="space-y-1.5">
								<div
									v-for="row in overview.certificates"
									:key="row.course"
									class="flex items-center justify-between text-p-sm"
								>
									<span class="text-ink-gray-8">{{ row.course_title }}</span>
									<span class="text-ink-gray-5">{{
										formatDate(row.issue_date)
									}}</span>
								</div>
							</div>
						</div>

						<div v-if="overview.programs.length">
							<div class="text-p-sm-medium text-ink-gray-7 mb-2">
								{{ __('Programs') }}
							</div>
							<div class="space-y-1.5">
								<div
									v-for="row in overview.programs"
									:key="row.program"
									class="flex items-center justify-between text-p-sm"
								>
									<span class="text-ink-gray-8">{{ row.program }}</span>
									<span class="text-ink-gray-5">{{ row.progress }}%</span>
								</div>
							</div>
						</div>

						<div v-if="overview.recent_logins.length">
							<div class="text-p-sm-medium text-ink-gray-7 mb-2">
								{{ __('Recent logins') }}
							</div>
							<div class="space-y-1.5">
								<div
									v-for="(row, idx) in overview.recent_logins"
									:key="idx"
									class="flex items-center justify-between text-p-sm"
								>
									<span class="text-ink-gray-8">{{
										formatDate(row.creation, true)
									}}</span>
									<span class="text-ink-gray-5">{{ row.ip_address }}</span>
								</div>
							</div>
						</div>
					</template>
				</div>
				<div v-else data-testid="member-fields" class="space-y-4">
				<FormControl
					v-model="member.email"
					:label="__('Email')"
					placeholder="jane@doe.com"
					type="email"
					:required="!isEdit"
					:disabled="isEdit"
					@keyup.enter="submit()"
				/>
				<div v-if="!isEdit" class="flex items-center gap-3">
					<FormControl
						v-model="member.first_name"
						:label="__('First Name')"
						placeholder="Jane"
						type="text"
						class="w-full"
					/>
					<FormControl
						v-model="member.last_name"
						:label="__('Last Name')"
						placeholder="Doe"
						type="text"
						class="w-full"
					/>
				</div>
				<div class="flex flex-col gap-2">
					<div class="text-p-sm-medium text-ink-gray-7">
						{{ __('Roles') }}
					</div>
					<div class="grid md:grid-cols-2 gap-x-6 gap-y-3">
						<BooleanSwitch
							size="sm"
							:label="__('Student')"
							v-model="roles.lms_student"
						/>
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
						<BooleanSwitch
							size="sm"
							:label="__('Moderator')"
							v-model="roles.moderator"
						/>
					</div>
				</div>
			</div>
			</template>
		</template>
		<template #actions>
			<div
				v-if="!refusal && activeTab !== 'Overview'"
				class="flex items-center justify-end"
			>
				<HeaderButton
					data-testid="member-save"
					:label="__('Save')"
					variant="solid"
					:loading="submitting"
					:disabled="isEdit && !memberRow"
					@click="submit()"
				/>
			</div>
		</template>
	</FormShell>
</template>
<script setup lang="ts">
import { call, createResource, FormControl, TabButtons, toast } from 'frappe-ui'
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { useOnboarding, useTelemetry } from 'frappe-ui/frappe'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import FormShell from '@/components/FormShell.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import { useFormRoute } from '@/composables/useFormRoute'
import { notifyMembersChanged } from '@/stores/members'
import { cleanError } from '@/utils'
import type { Resource, SessionUser } from '@/types'

type MemberRow = { name: string; roles?: string[] }

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

type MemberOverview = {
	last_login: string | null
	last_active: string | null
	last_ip: string | null
	tags: string[]
	enrollments: MemberOverviewRow[]
	quiz_submissions: MemberOverviewRow[]
	avg_quiz_score: number | null
	certificates: MemberOverviewRow[]
	programs: MemberOverviewRow[]
	recent_logins: MemberOverviewRow[]
}

const props = defineProps<{ memberID: string }>()

const user = inject<SessionUser>('$user')!
const { capture } = useTelemetry()
const { updateOnboardingStep } = useOnboarding('learning')

// House style for a route that serves both create and edit
// (`/job-opening/:jobName/edit`, JobForm.vue:147-149).
const isEdit = computed(() => props.memberID !== 'new')

// Only reached on a deep link or a reload — opened from Members.vue this pops
// back to whatever page it was opened from (useFormRoute.ts). Members is now a
// real top-level page (this route's own parent), so it is the natural fallback
// rather than a phone-only surface with no real connection to user management.
const { close } = useFormRoute({ name: 'Members' })

// Members.vue's Add button carried no gate of its own — the gate was on the
// settings surface around it (UserDropdown.vue:59-62 for the desktop dialog),
// and a URL goes through neither. `is_moderator` alone, deliberately: this is
// the narrowest gate in settings and get_members/save_role both
// `frappe.only_for("Moderator")`.
//
// UX gate, not an authorization boundary — those two only_for calls are
// (lms/lms/api.py:977 and :1851).
const refusal = computed(() => {
	if ((window as Window & { read_only_mode?: boolean }).read_only_mode)
		return __('This site is in read-only mode.')
	if (!user.data?.is_moderator)
		return __('You are not permitted to manage members.')
	return ''
})

const ROLE_MAP: Record<string, string> = {
	moderator: 'Moderator',
	course_creator: 'Course Creator',
	batch_evaluator: 'Batch Evaluator',
	lms_student: 'LMS Student',
}

const member = reactive({
	email: isEdit.value ? props.memberID : '',
	first_name: '',
	last_name: '',
})

const roles = reactive({
	moderator: false,
	course_creator: false,
	batch_evaluator: false,
	lms_student: false,
})

const initialRoles = reactive({ ...roles })
const submitting = ref(false)

const activeTab = ref<'Roles' | 'Overview'>('Roles')

const overviewFetch = createResource({
	url: 'lms.lms.api.get_member_overview',
	makeParams() {
		return { member: props.memberID }
	},
	auto: false,
}) as unknown as Resource<MemberOverview | null>

const overview = computed<MemberOverview | null>(() => overviewFetch.data ?? null)

// Lazy: most edits here only touch Roles, so this only runs once someone
// actually opens the Overview tab, not on every dialog open.
watch(activeTab, (tab) => {
	if (tab === 'Overview' && isEdit.value && !overviewFetch.data && !overviewFetch.loading) {
		overviewFetch.fetch()
	}
})

function formatDate(value: string | null | undefined, withTime = false): string {
	if (!value) return __('Never')
	const date = new Date(value.replace(' ', 'T'))
	if (Number.isNaN(date.getTime())) return value
	return withTime ? date.toLocaleString() : date.toLocaleDateString()
}

// C4 — edit mode used to be seeded from the row Members.vue already held in
// memory, which on a cold deep link does not exist.
//
// get_member, not the get_members list endpoint: that one hard-filters
// `enabled = 1` and pages at MEMBERS_PAGE_LENGTH, so a disabled member, or one
// whose address is a substring of more than a page of other members', never
// came back — and the form sat with Save permanently disabled and nothing on
// screen saying why.
const memberFetch = createResource({
	url: 'lms.lms.api.get_member',
	makeParams() {
		return { member: props.memberID }
	},
	auto: false,
}) as unknown as Resource<MemberRow | null>

onMounted(() => {
	if (isEdit.value && !refusal.value) memberFetch.fetch()
})

const memberRow = computed<MemberRow | null>(() =>
	isEdit.value ? memberFetch.data ?? null : null
)

// `immediate` matters: the modal's watcher only ran when the dialog opened, and
// a route component is already open by the time it mounts.
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

// Stands in for the modal's `created`/`updated` emits: a route component has no
// parent listening. A signal rather than the parent's resource, because that
// resource cannot be cached — see the note in @/stores/members. Nobody is
// listening on a phone deep link, which is correct: Members.vue fetches on
// mount.
const reloadMembers = () => {
	notifyMembersChanged()
}

const errorMessage = (err: { messages?: string[] }, fallback: string): string =>
	cleanError(err.messages?.[0]) || fallback

const assignRoles = async (userEmail: string) => {
	for (const [key, checked] of Object.entries(roles)) {
		if (checked)
			await call('lms.lms.api.save_role', {
				user: userEmail,
				role: ROLE_MAP[key],
				value: 1,
			})
	}
}

const addMember = async () => {
	if (!member.email?.trim()) {
		toast.error(__('Email is required'))
		return
	}

	submitting.value = true
	try {
		const created = await call('frappe.client.insert', {
			doc: {
				doctype: 'User',
				email: member.email.trim(),
				first_name: member.first_name.trim() || undefined,
				last_name: member.last_name.trim() || undefined,
			},
		})

		await assignRoles(created.name)

		if (user.data?.is_system_manager) updateOnboardingStep('invite_students')
		capture('user_added')
		toast.success(__('Member added successfully'))
		reloadMembers()
		close()
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to add member')))
	} finally {
		submitting.value = false
	}
}

const saveRoles = async () => {
	submitting.value = true
	try {
		for (const key of Object.keys(ROLE_MAP) as (keyof typeof roles)[]) {
			if (roles[key] !== initialRoles[key]) {
				await call('lms.lms.api.save_role', {
					user: props.memberID,
					role: ROLE_MAP[key],
					value: roles[key] ? 1 : 0,
				})
			}
		}

		toast.success(__('Member updated'))
		reloadMembers()
		close()
	} catch (err: any) {
		toast.error(errorMessage(err, __('Unable to update member')))
	} finally {
		submitting.value = false
	}
}

const submit = () => {
	if (refusal.value || submitting.value) return
	// Edit mode before the row lands would post a role diff against an all-off
	// snapshot and strip every role the member has; the button is disabled for
	// the same reason.
	if (isEdit.value && !memberRow.value) return
	return isEdit.value ? saveRoles() : addMember()
}
</script>
