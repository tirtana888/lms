<template>
	<div class="flex h-full overflow-hidden">
		<TabsRoot
			v-model="activeTab"
			orientation="vertical"
			activation-mode="manual"
			class="flex h-full min-h-0 w-full flex-col overflow-hidden sm:flex-row"
		>
			<SettingsSidebar>
				<div class="flex h-7 items-center px-2 pb-2">
					<span class="text-base font-medium text-ink-gray-9">
						{{ __('Settings') }}
					</span>
				</div>
				<SettingsNavGroup
					v-for="group in tabs"
					:key="group.label"
					:label="group.hideLabel ? undefined : __(group.label)"
				>
					<template #label>
						<span class="text-p-xs-medium text-ink-gray-5">
							{{ __(group.label) }}
						</span>
					</template>
					<SettingsNavItem
						v-for="item in group.items"
						:key="item.label"
						:value="item.label"
					>
						<template #prefix>
							<span :class="[item.icon, 'size-4 shrink-0 text-ink-gray-7']" />
						</template>
						<span class="text-p-sm text-ink-gray-7">{{ __(item.label) }}</span>
					</SettingsNavItem>
				</SettingsNavGroup>
			</SettingsSidebar>
			<SettingsContent v-if="data.doc" class="overflow-y-auto">
				<SettingsPanel
					v-for="item in items"
					:key="item.label"
					:value="item.label"
				>
					<component
						v-if="item.template"
						:is="item.template"
						v-bind="panelProps(item)"
					/>
					<SettingDetails
						v-else
						:sections="item.sections"
						:label="item.label"
						:description="item.description"
						:data="data"
					/>
				</SettingsPanel>
			</SettingsContent>
		</TabsRoot>
	</div>
</template>
<script setup>
import {
	SettingsContent,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
	createDocumentResource,
	usePageMeta,
} from 'frappe-ui'
import { TabsRoot } from 'reka-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SettingDetails from '@/components/Settings/SettingDetails.vue'
import { settingsStructure } from '@/components/Settings/settingsStructure.js'

const route = useRoute()
const router = useRouter()
const doctype = ref('LMS Settings')
const activeTab = ref('')

usePageMeta(() => ({ title: __('Settings') }))

const data = createDocumentResource({
	doctype: doctype.value,
	name: doctype.value,
	fields: ['*'],
	cache: doctype.value,
	auto: true,
})

const tabs = computed(() => {
	return settingsStructure.map((tab) => {
		return {
			...tab,
			items: tab.items.filter((item) => {
				return !item.condition || item.condition()
			}),
		}
	})
})

const items = computed(() => tabs.value.flatMap((group) => group.items))

function resolveTab(label) {
	const stored = items.value.find((item) => item.label === label)
	return (stored || items.value[0])?.label
}

// The URL is the source of truth for which tab is open, so a direct link (or
// AppSidebar's onboarding shortcut, via a router.push with a `tab` param)
// lands on the right panel and the back/forward buttons work. Only reacts
// when the resolved tab actually changes, so switching tabs the other way
// (see below) doesn't bounce back into this and fight the route push.
watch(
	() => route.params.tab,
	(tab) => {
		const resolved = resolveTab(tab)
		if (resolved && resolved !== activeTab.value) activeTab.value = resolved
	},
	{ immediate: true }
)

// Reka-ui drives `activeTab` directly when a nav item is clicked; push that
// back into the URL (replace, not push, so tabbing through Settings doesn't
// pile up history entries) rather than routing the click itself.
watch(activeTab, (tab) => {
	if (tab && tab !== route.params.tab) {
		router.replace({ name: 'Settings', params: { tab } })
	}
})

// Members and Transactions own dialogs of their own; nothing needs to close
// them anymore now that Settings is a real page instead of an overlay.
const panelProps = (item) => ({
	label: item.label,
	description: item.description,
})
</script>
