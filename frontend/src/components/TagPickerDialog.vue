<template>
	<Dialog v-model:open="open" :title="title" size="sm">
		<template #default>
			<div class="flex flex-col gap-3">
				<FormControl
					v-model="query"
					type="text"
					:label="__('Tag')"
					:placeholder="
						mode === 'add' ? __('Search or create a tag') : __('Search tags')
					"
					data-testid="tag-picker-input"
					@keydown.enter.prevent="submit"
				/>
				<p v-if="hasComma" class="text-p-sm text-ink-red-4" role="alert">
					{{ __('A tag cannot contain a comma.') }}
				</p>
				<div
					v-if="matches.length || canCreate"
					class="max-h-52 overflow-y-auto rounded-md border p-1"
				>
					<button
						v-for="row in matches"
						:key="row.tag"
						type="button"
						class="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-p-sm text-ink-gray-8 hover:bg-surface-gray-2"
						:class="{ 'bg-surface-gray-2': sameTag(row.tag, trimmed) }"
						@click="query = row.tag"
					>
						<span class="flex min-w-0 items-center gap-2">
							<span
								class="lucide-tag size-3.5 shrink-0 text-ink-gray-5"
								aria-hidden="true"
							/>
							<span class="truncate">{{ row.tag }}</span>
						</span>
						<span class="tabular-nums text-ink-gray-5">{{ row.count }}</span>
					</button>
					<button
						v-if="canCreate"
						type="button"
						class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-p-sm-medium text-ink-blue-3 hover:bg-surface-gray-2"
						@click="submit"
					>
						<span class="lucide-plus size-3.5 shrink-0" aria-hidden="true" />
						<span class="truncate">{{ __('Create tag "{0}"').format(trimmed) }}</span>
					</button>
				</div>
				<p
					v-else-if="mode === 'remove' && !tags.length"
					class="text-p-sm text-ink-gray-5"
				>
					{{ __('There are no tags yet.') }}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2 pb-5">
				<Button variant="subtle" :label="__('Cancel')" @click="open = false" />
				<Button
					variant="solid"
					:label="confirmLabel"
					:disabled="!canSubmit || loading"
					:loading="loading"
					data-testid="tag-picker-confirm"
					@click="submit"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog, FormControl } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

export type TagRow = { tag: string; count: number }

const props = defineProps<{
	mode: 'add' | 'remove'
	/** How many members the change applies to, for the title and the button. */
	count: number
	tags: TagRow[]
	loading?: boolean
}>()

const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ confirm: [tag: string] }>()

const query = ref('')

// A fresh dialog every time it opens; a leftover query would pre-fill the
// next bulk change with the last one's tag.
watch(open, (isOpen) => {
	if (isOpen) query.value = ''
})

const sameTag = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase()

const trimmed = computed(() => query.value.replace(/\s+/g, ' ').trim())
const hasComma = computed(() => trimmed.value.includes(','))

const matches = computed(() => {
	const needle = trimmed.value.toLowerCase()
	return props.tags.filter((row) => !needle || row.tag.toLowerCase().includes(needle))
})

const exists = computed(() => props.tags.some((row) => sameTag(row.tag, trimmed.value)))

const canCreate = computed(
	() => props.mode === 'add' && Boolean(trimmed.value) && !hasComma.value && !exists.value
)

// Removing only makes sense for a tag that exists; adding accepts a new one.
const canSubmit = computed(() => {
	if (!trimmed.value || hasComma.value) return false
	return props.mode === 'add' || exists.value
})

const title = computed(() =>
	props.mode === 'add'
		? __('Add a tag to {0} members').format(props.count)
		: __('Remove a tag from {0} members').format(props.count)
)

const confirmLabel = computed(() => (props.mode === 'add' ? __('Add tag') : __('Remove tag')))

function submit() {
	if (!canSubmit.value || props.loading) return
	// Reuse the existing spelling so "beasiswa" does not become a second tag.
	const existing = props.tags.find((row) => sameTag(row.tag, trimmed.value))
	emit('confirm', existing ? existing.tag : trimmed.value)
}
</script>
