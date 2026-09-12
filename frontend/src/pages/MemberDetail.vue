<template>
	<div v-if="refusal" class="p-4 text-base text-ink-gray-6">
		{{ refusal }}
	</div>
	<template v-else>
		<PageHeader :breadcrumbs="breadcrumbs">
			<template #actions>
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

			<div class="mb-6 mt-8">
				<TabButtons
					:options="[
						{ label: __('Overview'), value: 'Overview' },
						{ label: __('Roles'), value: 'Roles' },
					]"
					v-model="activeTab"
				/>
			</div>

			<div v-if="activeTab === 'Overview'" data-testid="member-overview" class="space-y-5">
				<div v-if="overviewFetch.loading" class="text-p-sm text-ink-gray-5">
					{{ __('Loading...') }}
				</div>
				<template v-else-if="overview">
					<div class="grid grid-cols-2 gap-4 text-p-sm sm:grid-cols-4">
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
						<Badge v-for="tag in overview.tags" :key="tag" theme="gray" variant="subtle">
							{{ tag }}
						</Badge>
					</div>

					<div>
						<div class="text-p-sm-medium text-ink-gray-7 mb-2">
							{{ __('Courses') }} ({{ overview.enrollments.length }})
						</div>
						<div v-if="!overview.enrollments.length" class="text-p-sm text-ink-gray-5">
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
						<div v-if="!overview.quiz_submissions.length" class="text-p-sm text-ink-gray-5">
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
						<div v-if="!overview.certificates.length" class="text-p-sm text-ink-gray-5">
							{{ __('No certificates yet.') }}
						</div>
						<div v-else class="space-y-1.5">
							<div
								v-for="row in overview.certificates"
								:key="row.course"
								class="flex items-center justify-between text-p-sm"
							>
								<span class="text-ink-gray-8">{{ row.course_title }}</span>
								<span class="text-ink-gray-5">{{ formatDate(row.issue_date) }}</span>
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
								<span class="text-ink-gray-8">{{ formatDate(row.creation, true) }}</span>
								<span class="text-ink-gray-5">{{ row.ip_address }}</span>
							</div>
						</div>
					</div>
				</template>
			</div>

			<div v-else data-testid="member-roles" class="flex flex-col gap-2">
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
		</div>
	</template>
</template>
<script setup lang="ts">
import { Avatar, Badge, call, createResource, TabButtons, toast } from 'frappe-ui'
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { notifyMembersChanged } from '@/stores/members'
import { cleanError } from '@/utils'
import type { Breadcrumb, Resource, SessionUser } from '@/types'

type MemberRow = { name: string; full_name: string; user_image?: string; roles?: string[] }

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
const route = useRoute()

// A moderator-only page reached by a real URL — same gate as the rest of
// member management (`frappe.only_for("Moderator")` on
// get_member/get_member_overview/save_role, lms/lms/api.py).
const refusal = computed(() => {
	if ((window as Window & { read_only_mode?: boolean }).read_only_mode)
		return __('This site is in read-only mode.')
	if (!user.data?.is_moderator)
		return __('You are not permitted to manage members.')
	return ''
})

// Members.vue's name link opens straight onto Overview; the "..." menu's Edit
// member opens onto Roles instead.
const activeTab = ref<'Roles' | 'Overview'>(
	route.query.tab === 'Roles' ? 'Roles' : 'Overview'
)

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

const overviewFetch = createResource({
	url: 'lms.lms.api.get_member_overview',
	makeParams: () => ({ member: props.memberID }),
	auto: false,
}) as unknown as Resource<MemberOverview | null>

const overview = computed<MemberOverview | null>(() => overviewFetch.data ?? null)

// Lazy + immediate: most visits land on Overview directly (the name link), but
// a visit that starts on Roles (the "..." menu) should still fetch it the
// moment someone switches tabs, not only on a later change.
watch(
	activeTab,
	(tab) => {
		if (tab === 'Overview' && !overviewFetch.data && !overviewFetch.loading) {
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

const errorMessage = (err: { messages?: string[] }, fallback: string): string =>
	cleanError(err.messages?.[0]) || fallback

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
