<template>
	<iframe
		v-if="frameSrc"
		:src="frameSrc"
		:title="__('SCORM content')"
		class="w-full h-[600px] mb-4 border rounded-md"
	/>
</template>
<script setup>
import { call } from 'frappe-ui'
import { computed, onBeforeMount, ref } from 'vue'
import { safeUrl } from '@/utils/safeUrl'

// Mirrors the SCORM API bridge in pages/SCORMChapter.vue, scoped to a single
// lesson-embedded package instead of a whole chapter. Kept as a separate
// component rather than reusing that page: this mounts standalone (EditorJS
// blocks live outside the app's Vue tree, like QuizBlock/AssessmentPlugin),
// has no outline/lock UI of its own (the lesson page around it already
// gated access before this block rendered), and the resource bytes are
// gated again server-side by LessonSCORMRenderer regardless.
const props = defineProps({
	course: {
		type: String,
		required: true,
	},
	lesson: {
		type: String,
		required: true,
	},
	launchFile: {
		type: String,
		required: true,
	},
	member: {
		type: String,
		default: null,
	},
})

const frameSrc = computed(() => safeUrl(props.launchFile))

const isSuccessfullyCompleted = ref(false)
const progressData = ref({ status: null, scorm_content: '' })

onBeforeMount(() => {
	setupSCORMAPI()
	loadProgress()
})

const loadProgress = () => {
	if (!props.member) return
	call('frappe.client.get_value', {
		doctype: 'LMS Course Progress',
		fieldname: ['status', 'scorm_content'],
		filters: {
			member: props.member,
			lesson: props.lesson,
			course: props.course,
		},
	})
		.then((data) => {
			if (data) progressData.value = data
		})
		.catch(() => {})
}

const getDataFromLMS = (key) => {
	if (key === 'cmi.core.lesson_status') {
		return progressData.value.status === 'Complete' ? 'passed' : 'incomplete'
	} else if (key === 'cmi.launch_data' || key === 'cmi.suspend_data') {
		return progressData.value.scorm_content || ''
	}
	return ''
}

let saveTimeout = null
const debouncedSaveProgress = (scormDetails) => {
	if (isSuccessfullyCompleted.value) return
	clearTimeout(saveTimeout)
	saveTimeout = setTimeout(() => {
		if (!isSuccessfullyCompleted.value) saveProgress(scormDetails)
	}, 300)
}

const saveDataToLMS = (key, value) => {
	const isLessonStatus = key === 'cmi.core.lesson_status' && value === 'passed'
	const isCompletionStatus =
		key === 'cmi.completion_status' && value === 'completed'

	if (isLessonStatus || isCompletionStatus) {
		if (isSuccessfullyCompleted.value) return
		isSuccessfullyCompleted.value = true
		saveProgress({ is_complete: true, scorm_content: '' })
		return
	}

	if (key === 'cmi.suspend_data' && !isSuccessfullyCompleted.value) {
		debouncedSaveProgress({ is_complete: false, scorm_content: value })
	}
}

const saveProgress = (scormDetails = null) => {
	call('lms.lms.doctype.course_lesson.course_lesson.save_progress', {
		lesson: props.lesson,
		course: props.course,
		scorm_details: scormDetails,
	}).catch(() => {})
}

const setupSCORMAPI = () => {
	window.API_1484_11 = {
		Initialize: () => 'true',
		Terminate: () => 'true',
		GetValue: (key) => getDataFromLMS(key),
		SetValue: (key, value) => {
			saveDataToLMS(key, value)
			return 'true'
		},
		Commit: () => 'true',
		GetLastError: () => '0',
		GetErrorString: () => '',
		GetDiagnostic: () => '',
	}
	window.API = {
		LMSInitialize: () => 'true',
		LMSFinish: () => 'true',
		LMSGetValue: (key) => getDataFromLMS(key),
		LMSSetValue: (key, value) => {
			saveDataToLMS(key, value)
			return 'true'
		},
		LMSCommit: () => 'true',
		LMSGetLastError: () => '0',
		LMSGetErrorString: () => '',
		LMSGetDiagnostic: () => '',
	}
}
</script>
