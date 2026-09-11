<template>
	<div v-if="!course || !lesson" class="mb-4 text-sm text-ink-gray-5">
		{{ __('Save the lesson before adding a SCORM package.') }}
	</div>
	<FileUploader
		v-else
		:fileTypes="['.zip']"
		:uploadArgs="{ private: true }"
		:validateFile="validateFile"
		@success="onFileUploaded"
	>
		<template v-slot="{ progress, uploading, openFileSelector }">
			<div class="mb-4">
				<Button @click="openFileSelector" :loading="uploading || extracting">
					{{ uploadLabel(uploading, progress) }}
				</Button>
			</div>
		</template>
	</FileUploader>
</template>
<script setup>
import { Button, FileUploader, call, toast } from 'frappe-ui'
import { ref } from 'vue'

const props = defineProps({
	course: {
		type: String,
		default: null,
	},
	lesson: {
		type: String,
		default: null,
	},
	onUploaded: {
		type: Function,
		required: true,
	},
})

const extracting = ref(false)

const validateFile = (file) => {
	if (!file.name.toLowerCase().endsWith('.zip')) {
		return __('Only ZIP files are allowed.')
	}
}

const uploadLabel = (uploading, progress) => {
	if (uploading) return `${__('Uploading')} ${progress}%`
	if (extracting.value) return __('Processing SCORM package...')
	return __('Upload SCORM Package')
}

const onFileUploaded = async (file) => {
	extracting.value = true
	try {
		const data = await call('lms.lms.api.upload_lesson_scorm', {
			course: props.course,
			lesson: props.lesson,
			scorm_package: file,
		})
		props.onUploaded(data)
	} catch (err) {
		toast.error(err.messages?.[0] || __('Failed to process SCORM package.'))
	} finally {
		extracting.value = false
	}
}
</script>
