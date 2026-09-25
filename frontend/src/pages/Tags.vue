<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:title="__('Tags')"
		layout="list"
		:columns="columns"
		:rows="filteredRows"
		:loading="Boolean(tagsResource.loading)"
		v-model:search="search"
		empty-name="Tags"
		empty-icon="lucide-tag"
	>
		<template #actions>
			<Button variant="solid" :label="__('New tag')" data-testid="new-tag" @click="openNew">
				<template #prefix>
					<span class="lucide-plus size-4" aria-hidden="true" />
				</template>
			</Button>
		</template>

		<template #cell="{ column, row }">
			<div v-if="column.key === 'tag'" class="flex min-w-0 items-center">
				<Badge theme="blue" variant="subtle" class="max-w-full truncate">
					{{ (row as TagListRow).tag }}
				</Badge>
			</div>
			<div v-else-if="column.key === 'count'" class="flex items-center gap-3">
				<span class="w-10 tabular-nums text-ink-gray-8">
					{{ (row as TagListRow).count }}
				</span>
				<router-link
					v-if="(row as TagListRow).count"
					:to="{ name: 'Members', query: { tag: (row as TagListRow).tag } }"
					class="text-p-sm text-ink-blue-3 hover:underline"
				>
					{{ __('View members') }}
				</router-link>
				<span v-else class="text-p-sm text-ink-gray-5">{{ __('Not used yet') }}</span>
			</div>
			<Dropdown v-else-if="column.key === 'actions'" :options="getActionOptions(row as TagListRow)">
				<Button
					variant="ghost"
					:aria-label="__('Actions for {0}').format((row as TagListRow).tag)"
				>
					<template #icon>
						<span class="lucide-more-horizontal size-4" aria-hidden="true" />
					</template>
				</Button>
			</Dropdown>
		</template>
	</ListPage>

	<Dialog v-model:open="showNameDialog" :title="nameDialogTitle" size="sm">
		<template #default>
			<div class="flex flex-col gap-2">
				<p v-if="renaming" class="text-p-sm text-ink-gray-6">
					{{
						__('Every member with "{0}" gets the new name. This can take a moment.').format(
							renaming.tag
						)
					}}
				</p>
				<FormControl
					v-model="nameInput"
					type="text"
					:label="__('Tag name')"
					data-testid="tag-name-input"
					@keydown.enter.prevent="saveName"
				/>
				<p v-if="nameHasComma" class="text-p-sm text-ink-red-4" role="alert">
					{{ __('A tag cannot contain a comma.') }}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2 pb-5">
				<Button variant="subtle" :label="__('Cancel')" @click="showNameDialog = false" />
				<Button
					variant="solid"
					:label="renaming ? __('Save') : __('Create tag')"
					:disabled="!nameInput.trim() || nameHasComma || saving"
					:loading="saving"
					data-testid="tag-name-save"
					@click="saveName"
				/>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model:open="showDeleteDialog"
		:title="deleteTitle"
		:message="deleteMessage"
		size="sm"
		:actions="[
			{
				label: __('Delete tag'),
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
import { Badge, Button, call, createResource, Dialog, Dropdown, FormControl, toast, usePageMeta } from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ListPage from '@/components/Layouts/ListPage.vue'
import { sessionStore } from '@/stores/session'
import { resourceErrorMessage } from '@/utils/resource'
import type { Breadcrumb, ListColumn, SessionUser } from '@/types'

type TagListRow = { name: string; tag: string; count: number }

const router = useRouter()
const user = inject('$user') as SessionUser
const { brand } = sessionStore()

const search = ref('')

const tagsResource = createResource({
	url: 'lms.lms.api.get_member_tags',
	auto: false,
})

const rows = computed<TagListRow[]>(() =>
	((tagsResource.data as { tag: string; count: number }[] | null) || []).map((row) => ({
		name: row.tag,
		tag: row.tag,
		count: row.count,
	}))
)

const filteredRows = computed(() => {
	const needle = search.value.trim().toLowerCase()
	return needle ? rows.value.filter((row) => row.tag.toLowerCase().includes(needle)) : rows.value
})

// Same gate as Members.vue and the server: a typed-in /tags link must not
// leave a non-admin on an empty page.
onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_system_manager) {
		router.push({ name: 'Home' })
		return
	}
	tagsResource.reload()
})

// --- create + rename share one dialog ---------------------------------------
const showNameDialog = ref(false)
const nameInput = ref('')
const renaming = ref<TagListRow | null>(null)
const saving = ref(false)

const nameHasComma = computed(() => nameInput.value.includes(','))
const nameDialogTitle = computed(() => (renaming.value ? __('Rename tag') : __('New tag')))

const openNew = () => {
	renaming.value = null
	nameInput.value = ''
	showNameDialog.value = true
}

const openRename = (row: TagListRow) => {
	renaming.value = row
	nameInput.value = row.tag
	showNameDialog.value = true
}

async function saveName() {
	const value = nameInput.value.replace(/\s+/g, ' ').trim()
	if (!value || nameHasComma.value || saving.value) return
	saving.value = true
	try {
		if (renaming.value) {
			const result = await call('lms.lms.api.rename_member_tag', {
				tag: renaming.value.tag,
				new_tag: value,
			})
			toast.success(__('Tag renamed on {0} members').format(result.updated))
		} else {
			await call('lms.lms.api.create_member_tag', { tag: value })
			toast.success(__('Tag created'))
		}
		showNameDialog.value = false
		await tagsResource.reload()
	} catch (err) {
		toast.error(resourceErrorMessage(err, __('Unable to save the tag')))
	} finally {
		saving.value = false
	}
}

// --- delete -----------------------------------------------------------------
const showDeleteDialog = ref(false)
const tagToDelete = ref<TagListRow | null>(null)

const deleteTitle = computed(() =>
	tagToDelete.value ? __('Delete tag "{0}"?').format(tagToDelete.value.tag) : ''
)

const deleteMessage = computed(() => {
	if (!tagToDelete.value) return ''
	return tagToDelete.value.count
		? __(
				'This removes the tag from {0} members. Their accounts and learning data are not changed. This cannot be undone.'
		  ).format(tagToDelete.value.count)
		: __('No member uses this tag. It will be removed from the list.')
})

const openDelete = (row: TagListRow) => {
	tagToDelete.value = row
	showDeleteDialog.value = true
}

async function confirmDelete(close?: () => void) {
	if (!tagToDelete.value) return
	try {
		const result = await call('lms.lms.api.delete_member_tag', { tag: tagToDelete.value.tag })
		toast.success(__('Tag removed from {0} members').format(result.removed))
		showDeleteDialog.value = false
		tagToDelete.value = null
		await tagsResource.reload()
	} catch (err) {
		toast.error(resourceErrorMessage(err, __('Unable to delete the tag')))
	}
	close?.()
}

const getActionOptions = (row: TagListRow) => [
	{
		label: __('View members'),
		icon: 'lucide-users',
		onClick: () => router.push({ name: 'Members', query: { tag: row.tag } }),
	},
	{ label: __('Rename tag'), icon: 'lucide-pencil', onClick: () => openRename(row) },
	{
		label: __('Delete tag'),
		icon: 'lucide-trash-2',
		theme: 'red',
		onClick: () => openDelete(row),
	},
]

const columns: ListColumn[] = [
	{ label: __('Tag'), key: 'tag', width: 2.4, icon: 'lucide-tag' },
	{ label: __('Members'), key: 'count', width: 2, icon: 'lucide-users' },
	{ label: '', key: 'actions', width: 0.4, kind: 'actions' },
]

const breadcrumbs: Breadcrumb[] = [
	{ label: __('Users'), route: { name: 'Members' } },
	{ label: __('Tags'), route: { name: 'Tags' } },
]

usePageMeta(() => ({
	title: __('Tags'),
	icon: brand.favicon,
}))
</script>
