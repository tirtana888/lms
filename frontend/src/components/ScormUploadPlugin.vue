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
		:uploadArgs="{
			private: true,
			upload_endpoint: '/api/method/lms.lms.api.upload_scorm_package',
			docname: course,
		}"
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

// `getContext` is a closure over LessonForm.vue's uploadContext (see
// utils/scorm.js's renderUploader) rather than that object passed directly:
// EditorJS snapshots a tool's `config` once, when the editor is constructed,
// so a plain object reference stops seeing later updates (docname is only
// known once the lesson - a placeholder at editor-construction time for a
// brand-new lesson - is first saved). Calling the closure re-reads the live
// object every time instead of whatever it looked like at construction.
const props = defineProps({
	getContext: {
		type: Function,
		default: () => ({}),
	},
	onUploaded: {
		type: Function,
		required: true,
	},
})

const course = computed(() => props.getContext?.()?.course)
const lesson = computed(() => props.getContext?.()?.docname)

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
		// Fold course/lesson into the saved block data: renderScorm() (the
		// student-facing playback) reads them from there instead of `config`,
		// since Lesson.vue constructs that student-view editor with an empty
		// uploadContext ({}) — none of the other blocks need one for read-only
		// rendering.
		props.onUploaded({ ...data, course: course.value, lesson: lesson.value })
	} catch (err) {
		toast.error(err.messages?.[0] || __('Failed to process SCORM package.'))
	} finally {
		extracting.value = false
	}
}
</script>
