<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:title="__('Users')"
		layout="list"
		:columns="columns"
		:rows="memberList"
		:loading="Boolean(members.loading)"
		:has-next-page="hasNextPage"
		v-model:search="search"
		empty-name="Users"
		empty-icon="lucide-user"
		@load-more="fetchMembers()"
	>
		<template #actions>
			<Button variant="solid" :label="__('New')" @click="openNewMember">
				<template #prefix>
					<span class="lucide-plus size-4" aria-hidden="true" />
				</template>
			</Button>
		</template>

		<template #filters>
			<Select
				v-model="currentRole"
				class="w-40"
				:aria-label="__('Filter by role')"
				:options="roleOptions"
			/>
		</template>

		<template #cell="{ column, row, value }">
			<router-link
				v-if="column.key === 'full_name'"
				:to="{
					name: 'MemberForm',
					params: { memberID: row.name },
					query: { tab: 'Overview' },
				}"
				class="flex items-center gap-x-3 hover:underline"
			>
				<Avatar size="sm" :image="row.user_image" :label="row.full_name" />
				<div class="flex min-w-0 flex-col">
					<span class="truncate">{{ row.full_name }}</span>
					<span class="truncate text-p-xs text-ink-gray-5">{{ row.name }}</span>
				</div>
			</router-link>
			<div v-else-if="column.key === 'roles'" class="flex flex-wrap gap-1">
				<Badge
					v-for="role in displayRoles(row)"
					:key="role"
					theme="gray"
					variant="subtle"
				>
					{{ role }}
				</Badge>
			</div>
			<div v-else-if="column.key === 'batches'" class="flex flex-wrap gap-1">
				<Badge
					v-for="batch in row.batches || []"
					:key="batch"
					theme="green"
					variant="subtle"
				>
					{{ batch }}
				</Badge>
			</div>
			<div v-else-if="column.key === 'tags'" class="flex flex-wrap gap-1">
				<Badge
					v-for="tag in displayTags(row)"
					:key="tag"
					theme="blue"
					variant="subtle"
				>
					{{ tag }}
				</Badge>
			</div>
			<div
				v-else-if="column.key === 'last_active' || column.key === 'creation'"
				class="text-p-sm text-ink-gray-6"
			>
				{{ formatDate(value) }}
			</div>
			<Dropdown
				v-else-if="column.key === 'actions'"
				:options="getActionOptions(row)"
			>
				<Button variant="ghost" :aria-label="__('Actions for {0}').format(row.full_name)">
					<template #icon>
						<span class="lucide-more-horizontal size-4" aria-hidden="true" />
					</template>
				</Button>
			</Dropdown>
			<div v-else>{{ value }}</div>
		</template>
	</ListPage>

	<router-view />

	<Dialog
		v-model:open="showDeleteDialog"
		:title="
			memberToDelete ? __('Delete {0}?').format(memberToDelete.full_name) : ''
		"
		:message="
			__('This permanently deletes the user account and cannot be undone.')
		"
		size="sm"
		:actions="[
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick: confirmDelete,
			},
			{
				label: __('Cancel'),
				onClick: () => {
					showDeleteDialog = false
				},
			},
		]"
	/>
</template>
<script setup lang="ts">
import {
	Avatar,
	Badge,
	Button,
	call,
	createResource,
	Dialog,
	Dropdown,
	Select,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { inject, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Breadcrumb, ListColumn, SessionUser } from '@/types'
import { sessionStore } from '@/stores/session'
import { openFormRoute } from '@/composables/useFormRoute'
import { membersRevision } from '@/stores/members'
import { cleanError } from '@/utils'

type Member = {
	username: string
	full_name: string
	name: string
	roles?: string[]
	user_image?: string
	last_active?: string
	creation?: string
	_user_tags?: string
	batches?: string[]
}

// Matches MEMBERS_PAGE_LENGTH in lms/lms/api.py, which pages `start` by this.
const MEMBERS_PAGE_LENGTH = 13

const router = useRouter()
const user = inject('$user') as SessionUser
const { brand } = sessionStore()
const search = ref('')
const currentRole = ref('All')
const start = ref(0)

const roleOptions = [
	{ label: __('All'), value: 'All' },
	{ label: __('Student'), value: 'LMS Student' },
	{ label: __('Instructor'), value: 'Course Creator' },
	{ label: __('Moderator'), value: 'Moderator' },
	{ label: __('Evaluator'), value: 'Batch Evaluator' },
]

const roleLabels: Record<string, string> = {
	'LMS Student': __('Student'),
	'Course Creator': __('Instructor'),
	Moderator: __('Moderator'),
	'Batch Evaluator': __('Evaluator'),
}

const displayRoles = (row: Member): string[] =>
	(row.roles || []).filter((role) => roleLabels[role]).map((role) => roleLabels[role])

// Frappe stores tags as a bare comma-separated string on every doc
// (`_user_tags`), not a child table — same parsing as get_member_overview.
const displayTags = (row: Member): string[] =>
	(row._user_tags || '').split(',').filter((tag) => tag)

const dayjs = inject('$dayjs') as (date: string) => { format: (fmt: string) => string }

const formatDate = (value: unknown): string =>
	typeof value === 'string' && value ? dayjs(value).format('DD MMM YYYY') : ''

const memberList = ref<Member[]>([])
const hasNextPage = ref(false)

const showDeleteDialog = ref(false)
const memberToDelete = ref<Member | null>(null)

// No frappe-ui `cache` key on purpose: makeParams closes over this component's
// refs, and createResource hands back the FIRST instance for a key without
// rebinding those closures — see the analogous note this replaced in
// components/Settings/Members.vue.
const members = createResource({
	url: 'lms.lms.api.get_members',
	makeParams: () => ({
		search: search.value,
		start: start.value,
		role: currentRole.value,
	}),
	auto: false,
})

// createResource carries no request sequence and aborts nothing, so two calls
// in flight both resolve and both append: a role change mid-request would show
// one filter's page under another's, and over-advance `start` past rows nobody
// ever saw. Each call takes a token and a superseded response is dropped.
let requestToken = 0

const fetchMembers = async () => {
	const token = ++requestToken
	const data = (await members.reload()) as Member[] | null
	if (token !== requestToken || !data) return
	memberList.value = memberList.value.concat(data)
	// Paged by what the server actually returned, not by the constant. An
	// exact-equality check hides Load More outright the moment the two
	// disagree, and stepping `start` by the constant would then skip rows.
	start.value = start.value + data.length
	hasNextPage.value = data.length >= MEMBERS_PAGE_LENGTH
}

// The search goes to the server with start reset, so a match past the first
// page is reachable without pressing Load More first.
const refreshMembers = () => {
	memberList.value = []
	start.value = 0
	return fetchMembers()
}

watch([search, currentRole], () => {
	refreshMembers()
})

// A member form saved while this page is still mounted behind it (desktop:
// the form renders as a dialog stacked on top of this route) has no other way
// to reach the list.
watch(membersRevision, () => {
	refreshMembers()
})

// The sidebar item is already hidden from a non-moderator, but the route
// itself has a real address now (unlike the old settings-dialog panel, which
// no URL could reach on its own) — so a typed-in link needs the same refusal
// MemberDetail.vue's own deep link already handles, not a get_members call a
// non-moderator was never going to see the results of. Mirrors QuizSubmissions.vue's
// admin gate.
onMounted(() => {
	if (!user.data?.is_moderator) {
		router.push({ name: 'Home' })
		return
	}
	refreshMembers()
})

// A real page now (MemberDetail.vue), not a modal stacked on this list — plain
// navigation, not openFormRoute's back-tracking. Lands on Roles, matching
// this menu item's name; the row's own name link opens the same page onto
// Overview instead (query.tab), further down in the template.
const openEditMember = (member: Member) => {
	router.push({
		name: 'MemberForm',
		params: { memberID: member.name },
		query: { tab: 'Roles' },
	})
}

const openNewMember = () => {
	openFormRoute(router, { name: 'NewMemberForm' })
}

const openDeleteDialog = (member: Member) => {
	memberToDelete.value = member
	showDeleteDialog.value = true
}

const getActionOptions = (row: Member) => [
	{
		label: __('Edit member'),
		icon: 'lucide-pencil',
		onClick: () => openEditMember(row),
	},
	{
		label: __('Delete user'),
		icon: 'lucide-trash-2',
		theme: 'red',
		onClick: () => openDeleteDialog(row),
	},
]

const confirmDelete = async (close: () => void) => {
	if (!memberToDelete.value) return
	try {
		await call('lms.lms.api.delete_member', { user: memberToDelete.value.name })
		showDeleteDialog.value = false
		memberToDelete.value = null
		refreshMembers()
		toast.success(__('User deleted'))
	} catch (err: any) {
		toast.error(cleanError(err.messages?.[0]) || err)
	}
	close?.()
}

const columns: ListColumn[] = [
	{ label: __('User'), key: 'full_name', width: 2.2, icon: 'lucide-user' },
	{ label: __('Roles'), key: 'roles', width: 1.3 },
	{
		label: __('Batch'),
		key: 'batches',
		width: 1.5,
		icon: 'lucide-users',
		hideOnMobile: true,
	},
	{ label: __('Tags'), key: 'tags', width: 1.2, hideOnMobile: true },
	{
		label: __('Last Activity'),
		key: 'last_active',
		width: 1.1,
		icon: 'lucide-clock',
	},
	{
		label: __('Registered'),
		key: 'creation',
		width: 1.1,
		icon: 'lucide-calendar',
		hideOnMobile: true,
	},
	{ label: '', key: 'actions', width: 0.4, kind: 'actions' },
]

const breadcrumbs: Breadcrumb[] = [{ label: __('Users'), route: { name: 'Members' } }]

usePageMeta(() => ({
	title: __('Users'),
	icon: brand.favicon,
}))
</script>
