<template>
	<SettingsLayout
		:title="__('Notifications')"
		:description="
			__(
				'Turn individual emails on or off, and point any of them at your own Email Template instead of the built-in wording.'
			)
		"
	>
		<div v-if="notifications.loading" class="text-p-sm text-ink-gray-5">
			{{ __('Loading...') }}
		</div>
		<div v-else class="flex flex-col gap-6">
			<div v-for="group in groups" :key="group.category">
				<div class="mb-2 text-p-sm-medium text-ink-gray-6">
					{{ __(group.category) }}
				</div>
				<div class="flex flex-col gap-2">
					<div
						v-for="row in group.rows"
						:key="row.event_key"
						class="flex items-start justify-between gap-4 rounded-lg border border-outline-gray-2 p-3"
					>
						<div class="min-w-0 flex-1">
							<div class="text-p-base-medium text-ink-gray-9">
								{{ __(row.label) }}
							</div>
							<div class="mt-0.5 text-p-sm text-ink-gray-5">
								{{ __(row.description) }}
							</div>
							<div class="mt-2 flex items-center gap-2">
								<span class="text-p-xs text-ink-gray-5 shrink-0">
									{{ __('Custom Template') }}
								</span>
								<Link
									:model-value="row.custom_template"
									doctype="Email Template"
									class="w-56"
									:aria-label="__('Custom Template for {0}').format(row.label)"
									@update:model-value="
										(value) => handleTemplateChange(row, value)
									"
								/>
							</div>
						</div>
						<Switch
							size="sm"
							:model-value="Boolean(row.enabled)"
							:aria-label="__('Send {0}').format(row.label)"
							@update:model-value="(value) => handleEnabledChange(row, value)"
						/>
					</div>
				</div>
			</div>
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import { Switch, call, createResource, toast } from 'frappe-ui'
import { computed } from 'vue'
import SettingsLayout from '@/components/Layouts/SettingsLayout.vue'
import Link from '@/components/Controls/Link.vue'
import { cleanError } from '@/utils'

type EmailNotificationRow = {
	event_key: string
	label: string
	category: string
	description: string
	enabled: number
	custom_template: string | null
	default_template: string
}

const notifications = createResource({
	url: 'lms.lms.email_notifications.get_email_notifications',
	auto: true,
}) as unknown as { loading: boolean; data: EmailNotificationRow[] | null; reload: () => void }

// Server already orders by category then label; group() here only splits the
// flat list into sections, it does not decide the order.
const groups = computed(() => {
	const rows = notifications.data ?? []
	const byCategory = new Map<string, EmailNotificationRow[]>()
	for (const row of rows) {
		if (!byCategory.has(row.category)) byCategory.set(row.category, [])
		byCategory.get(row.category)!.push(row)
	}
	return Array.from(byCategory, ([category, groupRows]) => ({ category, rows: groupRows }))
})

async function handleEnabledChange(row: EmailNotificationRow, value: boolean) {
	const previous = row.enabled
	row.enabled = value ? 1 : 0
	try {
		await call('lms.lms.email_notifications.update_email_notification', {
			event_key: row.event_key,
			enabled: value ? 1 : 0,
		})
	} catch (err: any) {
		row.enabled = previous
		toast.error(cleanError(err?.messages?.[0]) || __('Unable to update this notification'))
	}
}

async function handleTemplateChange(row: EmailNotificationRow, value: string | null) {
	const previous = row.custom_template
	row.custom_template = value
	try {
		await call('lms.lms.email_notifications.update_email_notification', {
			event_key: row.event_key,
			custom_template: value ?? '',
		})
	} catch (err: any) {
		row.custom_template = previous
		toast.error(cleanError(err?.messages?.[0]) || __('Unable to update this notification'))
	}
}
</script>
