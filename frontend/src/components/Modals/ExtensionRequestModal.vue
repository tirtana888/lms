<template>
	<Dialog v-model:open="show" :title="dialogTitle" size="lg" :actions="dialogActions">
		<template #default>
			<div v-if="picker.loading" class="py-6 text-center text-ink-gray-5">
				{{ __('Loading...') }}
			</div>

			<div v-else-if="!selectedItem" class="flex flex-col gap-4">
				<div
					v-if="picker.data?.chapters_pending"
					class="bg-surface-amber-1 rounded-lg px-4 py-3 text-sm text-ink-amber-6"
				>
					{{
						__(
							'You can request an extension once every chapter in this course has opened for you.'
						)
					}}
				</div>
				<div
					v-else-if="!picker.data?.items?.length"
					class="bg-surface-gray-1 rounded-lg px-4 py-3 text-sm text-ink-gray-6"
				>
					{{ __('Nothing in this course is currently blocked.') }}
				</div>
				<template v-else>
					<div class="text-p-sm text-ink-gray-5">
						{{
							__('{0} of {1} extension requests used for this course.').format(
								picker.data.requests_used,
								picker.data.requests_limit
							)
						}}
					</div>
					<div
						v-if="atLimit"
						class="bg-surface-amber-1 rounded-lg px-4 py-3 text-sm text-ink-amber-6"
					>
						{{ __('You have reached the maximum number of extension requests for this course.') }}
					</div>
					<div
						v-for="item in picker.data.items"
						:key="item.reference_name"
						class="flex items-center justify-between gap-3 rounded-lg border p-3"
					>
						<div class="min-w-0">
							<div class="truncate text-p-base-medium text-ink-gray-9">
								{{ item.title }}
							</div>
							<div class="text-p-xs text-ink-gray-5">
								{{ item.reference_type === 'LMS Quiz' ? __('Quiz') : __('Assignment') }}
								<span v-if="item.has_pending_request">
									· {{ __('Request pending review') }}
								</span>
							</div>
						</div>
						<Button
							variant="outline"
							size="sm"
							:disabled="atLimit || item.has_pending_request"
							@click="selectedItem = item"
						>
							{{ __('Request') }}
						</Button>
					</div>
				</template>
			</div>

			<div v-else class="flex flex-col gap-4">
				<div class="text-p-base-medium text-ink-gray-9">
					{{ selectedItem.title }}
				</div>
				<FormControl
					type="select"
					:label="__('Reason')"
					v-model="reasonCategory"
					variant="outline"
					:options="[
						{ label: __('Select a reason'), value: '' },
						{ label: __('Illness'), value: 'Sakit' },
						{ label: __('Technical Issue'), value: 'Kendala Teknis' },
						{
							label: __('Family or Personal Emergency'),
							value: 'Keperluan Keluarga atau Darurat',
						},
						{ label: __('Other'), value: 'Lainnya' },
					]"
				/>
				<FormControl
					type="textarea"
					:label="__('Explanation')"
					v-model="explanation"
					variant="outline"
					:required="true"
				/>
				<div>
					<span class="mb-1.5 block text-p-sm text-ink-gray-5">
						{{ __('Evidence (optional)') }}
					</span>
					<div v-if="!evidence">
						<FileUploader :uploadArgs="{ private: 1 }" @success="(file) => (evidence = file)">
							<template v-slot="{ uploading, progress, openFileSelector }">
								<Button :loading="uploading" @click="openFileSelector">
									<template #prefix>
										<span class="lucide-upload size-4" />
									</template>
									{{ uploading ? __('Uploading {0}%').format(progress) : __('Upload a file') }}
								</Button>
							</template>
						</FileUploader>
					</div>
					<div v-else class="flex items-center gap-2">
						<span class="lucide-file-text size-4 text-ink-gray-6" />
						<span class="truncate text-p-sm text-ink-gray-7">{{ evidence.file_name }}</span>
						<Button variant="ghost" size="sm" @click="evidence = null">
							<template #icon>
								<span class="lucide-x size-4" />
							</template>
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Button, Dialog, FileUploader, FormControl, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { resourceErrorMessage, submitResource } from '@/utils/resource'

const props = defineProps({
	course: {
		type: String,
		required: true,
	},
})

const emit = defineEmits(['submitted'])

const show = defineModel()
const selectedItem = ref(null)
const reasonCategory = ref('')
const explanation = ref('')
const evidence = ref(null)

const dialogTitle = computed(() =>
	selectedItem.value ? __('Request Extension') : __('Select an item to extend')
)

const picker = createResource({
	url: 'lms.lms.api.get_extendable_items',
	makeParams: () => ({ course: props.course }),
})

const atLimit = computed(
	() => (picker.data?.requests_used ?? 0) >= (picker.data?.requests_limit ?? 0)
)

watch(show, (open) => {
	if (open) {
		selectedItem.value = null
		reasonCategory.value = ''
		explanation.value = ''
		evidence.value = null
		picker.reload()
	}
})

const request = createResource({
	url: 'frappe.client.insert',
	makeParams: () => ({
		doc: {
			doctype: 'LMS Extension Request',
			course: props.course,
			reference_type: selectedItem.value?.reference_type,
			reference_name: selectedItem.value?.reference_name,
			reason_category: reasonCategory.value,
			explanation: explanation.value,
			evidence: evidence.value?.file_url,
		},
	}),
})

const submit = () =>
	submitResource(
		request,
		{},
		{
			validate() {
				if (!reasonCategory.value) return __('Please select a reason.')
				if (!explanation.value) return __('Please explain your request.')
			},
			onSuccess() {
				toast.success(__('Your extension request has been submitted.'))
				emit('submitted')
				show.value = false
			},
			onError(err) {
				toast.error(resourceErrorMessage(err))
			},
		}
	)

const dialogActions = computed(() => {
	if (!selectedItem.value) return []
	return [
		{
			label: __('Back'),
			variant: 'subtle',
			onClick: () => {
				selectedItem.value = null
			},
		},
		{
			label: __('Submit Request'),
			variant: 'solid',
			loading: request.loading,
			onClick: submit,
		},
	]
})
</script>
