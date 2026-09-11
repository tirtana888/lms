<template>
	<div v-if="!course || !lesson" class="mb-4 text-sm text-ink-gray-5">
		{{
			__(
				'Press Ctrl+S (Cmd+S on Mac) to save this lesson, then come back to add the SCORM package.'
			)
		}}
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
import { computed, ref } from 'vue'

// `config` is the same reactive uploadContext object LessonForm.vue passes
// into every editor tool (see utils/upload.js's identical `this.config`
// pattern) - read through computed()s rather than destructured once, so
// this block picks up `docname` the moment the lesson is first saved,
// instead of staying stuck on whatever it saw when the block was created
// (before the lesson - and its name - existed).
const props = defineProps({
	config: {
		type: Object,
		default: () => ({}),
	},
	onUploaded: {
		type: Function,
		required: true,
	},
})

const course = computed(() => props.config?.course)
const lesson = computed(() => props.config?.docname)

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
			course: course.value,
			lesson: lesson.value,
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
