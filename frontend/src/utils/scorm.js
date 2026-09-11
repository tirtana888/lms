import { registerDirectives } from '@/directives'
import { createApp, h } from 'vue'
import { Package } from 'lucide-vue-next'
import { usersStore } from '../stores/user'
import translationPlugin from '../translation'
import { blockNotice } from '@/utils/blockDom'
import ScormUploadPlugin from '@/components/ScormUploadPlugin.vue'
import ScormBlock from '@/components/ScormBlock.vue'

// Lesson-scoped counterpart to the whole-chapter SCORM package (BooleanSwitch
// in ChapterForm.vue + SCORMChapter.vue). This lets a package sit inline among
// a lesson's other blocks instead of taking over the entire chapter. Backed by
// lms.lms.api.upload_lesson_scorm (extracts under
// private/scorm-lesson/<course>/<lesson>) and served by
// lms.page_renderers.LessonSCORMRenderer — both additive, the existing
// chapter-level SCORM code path is untouched.
export class Scorm {
	constructor({ data, api, config, readOnly }) {
		this.data = data || {}
		this.readOnly = readOnly
		this.config = config || {}
	}

	static get toolbox() {
		const app = createApp({
			render: () => h(Package, { size: 18, strokeWidth: 1.5 }),
		})
		registerDirectives(app)

		const div = document.createElement('div')
		app.mount(div)

		return {
			title: __('SCORM Package'),
			icon: div.innerHTML,
		}
	}

	static get isReadOnlySupported() {
		return true
	}

	render() {
		this.wrapper = document.createElement('div')
		if (this.data?.launch_file) {
			this.readOnly ? this.renderScorm() : this.renderSummary()
		} else {
			this.renderUploader()
		}
		return this.wrapper
	}

	renderUploader() {
		const app = createApp(ScormUploadPlugin, {
			course: this.config.course,
			lesson: this.config.docname,
			onUploaded: (data) => {
				this.data = data
				this.wrapper.replaceChildren()
				this.renderSummary()
			},
		})
		registerDirectives(app)
		app.use(translationPlugin)
		app.mount(this.wrapper)
	}

	// Editing mode, package already uploaded: show a static summary rather than
	// an interactive player, matching how the Quiz block avoids running a live
	// quiz while an instructor edits (renderQuizModal never re-mounts once
	// data.quiz is set; here the SCORM iframe/API bridge only mounts readOnly).
	renderSummary() {
		this.wrapper.replaceChildren(
			blockNotice(`${__('SCORM Package')}: ${this.data.scorm_package}`)
		)
	}

	renderScorm() {
		const { userResource } = usersStore()
		this.app = createApp(ScormBlock, {
			course: this.config.course,
			lesson: this.config.docname,
			launchFile: this.data.launch_file,
			member: userResource.data?.name,
		})
		registerDirectives(this.app)
		this.app.use(translationPlugin)
		// Contain SCORM iframe/runtime errors to this mount, same as the inline
		// quiz app — an uncaught error here must not blank the whole lesson.
		this.app.config.errorHandler = (err) => {
			console.error('[lms] in-lesson SCORM block failed to render', err)
		}
		this.app.mount(this.wrapper)
	}

	// EditorJS calls destroy() when a block is removed or the editor is torn
	// down. Unmount whichever app render() mounted so it doesn't leak.
	destroy() {
		this.app?.unmount()
	}

	save() {
		if (!this.data?.launch_file) return {}
		return { ...this.data }
	}
}
