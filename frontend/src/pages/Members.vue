<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:title="__('Users')"
		layout="list"
		:columns="columns"
		:list-options="listOptions"
		:rows="memberList"
		:loading="Boolean(members.loading)"
		:has-next-page="hasNextPage"
		v-model:search="search"
		empty-name="Users"
		empty-icon="lucide-user"
		@load-more="fetchMembers()"
	>
		<template #actions>
			<Button
				v-if="user.data?.is_moderator"
				variant="solid"
				:label="__('New')"
				@click="openNewMember"
			>
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
			<Select
				v-model="currentTag"
				class="w-48"
				:aria-label="__('Filter by tag')"
				:options="tagFilterOptions"
			/>
		</template>

		<template #selection-actions="{ unselectAll, selections }">
			<Button
				variant="ghost"
				:label="__('Add tag')"
				data-testid="bulk-add-tag"
				@click="openBulkTag('add', selections, unselectAll)"
			>
				<template #prefix>
					<span class="lucide-tag size-4" aria-hidden="true" />
				</template>
			</Button>
			<Button
				variant="ghost"
				:label="__('Remove tag')"
				data-testid="bulk-remove-tag"
				@click="openBulkTag('remove', selections, unselectAll)"
			>
				<template #prefix>
					<span class="lucide-tag size-4" aria-hidden="true" />
				</template>
			</Button>
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
					<span class="flex items-center gap-1.5 truncate">
						{{ row.full_name }}
						<Badge v-if="!row.enabled" theme="red" variant="subtle">
							{{ __('Suspended') }}
						</Badge>
					</span>
					<span class="truncate text-p-xs text-ink-gray-5">{{ row.name }}</span>
				</div>
			</router-link>
			<div v-else-if="column.key === 'roles'" class="flex items-center gap-1">
				<Badge
					v-for="role in splitBadges(displayRoles(row)).shown"
					:key="role"
					theme="gray"
					variant="subtle"
				>
					{{ role }}
				</Badge>
				<Tooltip
					v-if="splitBadges(displayRoles(row)).hidden.length"
					:text="splitBadges(displayRoles(row)).hidden.join(', ')"
				>
					<Badge theme="gray" variant="subtle">
						+{{ splitBadges(displayRoles(row)).hidden.length }}
					</Badge>
				</Tooltip>
			</div>
			<div v-else-if="column.key === 'batches'" class="flex items-center gap-1">
				<Badge
					v-for="batch in splitBadges(row.batches || []).shown"
					:key="batch"
					theme="green"
					variant="subtle"
				>
					{{ batch }}
				</Badge>
				<Tooltip
					v-if="splitBadges(row.batches || []).hidden.length"
					:text="splitBadges(row.batches || []).hidden.join(', ')"
				>
					<Badge theme="green" variant="subtle">
						+{{ splitBadges(row.batches || []).hidden.length }}
					</Badge>
				</Tooltip>
			</div>
			<div v-else-if="column.key === 'tags'" class="flex items-center gap-1">
				<Badge
					v-for="tag in splitBadges(displayTags(row)).shown"
					:key="tag"
					theme="blue"
					variant="subtle"
				>
					{{ tag }}
				</Badge>
				<Tooltip
					v-if="splitBadges(displayTags(row)).hidden.length"
					:text="splitBadges(displayTags(row)).hidden.join(', ')"
				>
					<Badge theme="blue" variant="subtle">
						+{{ splitBadges(displayTags(row)).hidden.length }}
					</Badge>
				</Tooltip>
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

	<TagPickerDialog
		v-model="showTagPicker"
		:mode="tagPickerMode"
		:count="bulkSelection.length"
		:tags="tagRows"
		:loading="bulkSaving"
		@confirm="confirmBulkTag"
	/>

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
	Tooltip,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TagPickerDialog from '@/components/TagPickerDialog.vue'
import type { TagRow } from '@/components/TagPickerDialog.vue'
import type { Breadcrumb, ListColumn, ListViewOptions, SessionUser } from '@/types'
import { sessionStore } from '@/stores/session'
import { openFormRoute } from '@/composables/useFormRoute'
import { membersRevision } from '@/stores/members'
import { cleanError } from '@/utils'
import { resourceErrorMessage } from '@/utils/resource'

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
	enabled?: number
}

// Matches MEMBERS_PAGE_LENGTH in lms/lms/api.py, which pages `start` by this.
const MEMBERS_PAGE_LENGTH = 13

const router = useRouter()
const route = useRoute()
const user = inject('$user') as SessionUser
const { brand } = sessionStore()
const search = ref('')
const currentRole = ref('All')
// 'All' mirrors the role filter; a real tag arrives from ?tag= (the Tags page links here).
const currentTag = ref(typeof route.query.tag === 'string' && route.query.tag ? route.query.tag : 'All')
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

// frappe-ui's ListView rows appear to be fixed-height, so wrapping badges
// (2+ roles/batches/tags) overflow into the row above/below instead of
// growing the row - capping what's shown avoids ever needing a second line.
const BADGE_DISPLAY_LIMIT = 2
const splitBadges = (items: string[]): { shown: string[]; hidden: string[] } => ({
	shown: items.slice(0, BADGE_DISPLAY_LIMIT),
	hidden: items.slice(BADGE_DISPLAY_LIMIT),
})

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
		tag: currentTag.value === 'All' ? undefined : currentTag.value,
	}),
	auto: false,
})

// --- tags: filter options + bulk change --------------------------------------
// Fetched with call() rather than a resource: the member list's paging tokens
// (and its tests) count createResource reloads, and this is not one of them.
const tagRows = ref<TagRow[]>([])

async function loadTags() {
	try {
		tagRows.value = ((await call('lms.lms.api.get_member_tags')) as TagRow[] | undefined) || []
	} catch {
		// The filter just stays at "All tags"; the list itself is unaffected.
		tagRows.value = []
	}
}

// A tag from the URL that is not in the fetched list (e.g. removed meanwhile)
// still gets an option, so the Select never shows a blank for an active filter.
const tagFilterOptions = computed(() => {
	const options = [
		{ label: __('All tags'), value: 'All' },
		...tagRows.value.map((row) => ({ label: `${row.tag} (${row.count})`, value: row.tag })),
	]
	const active = currentTag.value
	if (active !== 'All' && !options.some((option) => option.value === active)) {
		options.push({ label: active, value: active })
	}
	return options
})

const listOptions: ListViewOptions = { selectable: true, showTooltip: false }

const showTagPicker = ref(false)
const tagPickerMode = ref<'add' | 'remove'>('add')
const bulkSelection = ref<string[]>([])
const bulkSaving = ref(false)
let clearSelection: (() => void) | null = null

const openBulkTag = (mode: 'add' | 'remove', selections: Set<string>, unselectAll: () => void) => {
	tagPickerMode.value = mode
	// Only rows still on screen: a filter change replaces the rows but the list
	// can keep the old ticks, and a bulk change must never reach a member the
	// admin can no longer see.
	const visible = new Set(memberList.value.map((member) => member.name))
	bulkSelection.value = Array.from(selections).filter((name) => visible.has(name))
	clearSelection = unselectAll
	showTagPicker.value = true
}

async function confirmBulkTag(tag: string) {
	bulkSaving.value = true
	try {
		const result = await call(
			tagPickerMode.value === 'add'
				? 'lms.lms.api.bulk_add_member_tag'
				: 'lms.lms.api.bulk_remove_member_tag',
			{ members: bulkSelection.value, tag }
		)
		toast.success(
			tagPickerMode.value === 'add'
				? __('Tag "{0}" added to {1} members').format(result.tag, result.updated)
				: __('Tag "{0}" removed from {1} members').format(result.tag, result.updated)
		)
		showTagPicker.value = false
		clearSelection?.()
		await Promise.all([refreshMembers(), loadTags()])
	} catch (err) {
		toast.error(resourceErrorMessage(err, __('Unable to change tags')))
	} finally {
		bulkSaving.value = false
	}
}

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

watch([search, currentRole, currentTag], () => {
	refreshMembers()
})

// Followed from the address too, not only read once: a link to /users while
// this page is already open on ?tag=X reuses the component.
watch(
	() => route.query.tag,
	(tag) => {
		const fromUrl = typeof tag === 'string' && tag ? tag : 'All'
		if (fromUrl !== currentTag.value) currentTag.value = fromUrl
	}
)

// Keep the address shareable: the tag filter is what the Tags page links to.
watch(currentTag, (tag) => {
	const query = { ...route.query }
	if (tag === 'All') delete query.tag
	else query.tag = tag
	router.replace({ query })
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
	if (!user.data?.is_moderator && !user.data?.is_system_manager) {
		router.push({ name: 'Home' })
		return
	}
	loadTags()
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
	// delete_member stays Moderator-only; a System Manager manages but can't delete here.
	...(user.data?.is_moderator
		? [
				{
					label: __('Delete user'),
					icon: 'lucide-trash-2',
					theme: 'red',
					onClick: () => openDeleteDialog(row),
				},
		  ]
		: []),
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
