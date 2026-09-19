<template>
	<div v-if="enabled" class="fixed bottom-20 end-4 z-40 sm:bottom-5 sm:end-5 flex flex-col items-end gap-3">
		<div
			v-if="open"
			class="flex h-[32rem] max-h-[80vh] w-[22rem] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-xl border bg-surface-base shadow-2xl"
		>
			<div class="flex items-center justify-between border-b px-4 py-3">
				<div class="flex items-center gap-2">
					<span class="lucide-sparkles size-4 text-ink-gray-7" />
					<div class="text-p-base font-semibold text-ink-gray-9">
						{{ __('AI Study Coach') }}
					</div>
				</div>
				<button
					class="rounded p-1 text-ink-gray-5 hover:bg-surface-gray-2"
					:aria-label="__('Close')"
					@click="open = false"
				>
					<span class="lucide-x size-4" />
				</button>
			</div>

			<div ref="scroller" class="flex-1 space-y-3 overflow-y-auto px-4 py-3">
				<div
					v-for="(m, idx) in messages"
					:key="idx"
					class="flex"
					:class="m.role === 'user' ? 'justify-end' : 'justify-start'"
				>
					<div
						class="max-w-[85%] rounded-lg px-3 py-2 text-p-sm"
						:class="
							m.role === 'user'
								? 'bg-surface-gray-7 text-ink-white'
								: m.error
									? 'bg-surface-red-2 text-ink-red-4'
									: 'bg-surface-gray-2 text-ink-gray-9'
						"
					>
						<div
							v-if="m.role === 'assistant' && !m.error"
							class="coach-prose"
							v-html="render(m.text)"
						/>
						<div v-else class="whitespace-pre-wrap break-words">{{ m.text }}</div>
						<div v-if="m.sources?.length" class="mt-2 border-t pt-2 text-p-xs text-ink-gray-6">
							<div class="mb-1 font-medium">{{ __('Sources') }}</div>
							<ul class="list-disc ps-4">
								<li v-for="s in m.sources" :key="s.id">{{ s.title }}</li>
							</ul>
						</div>
					</div>
				</div>
				<div v-if="loading" class="flex justify-start">
					<div class="rounded-lg bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
						{{ __('Thinking...') }}
					</div>
				</div>
			</div>

			<form class="flex items-end gap-2 border-t p-3" @submit.prevent="send">
				<textarea
					id="getlearn-chat-input"
					v-model="draft"
					rows="1"
					maxlength="1000"
					class="max-h-28 min-h-9 flex-1 resize-none rounded-md border bg-surface-gray-1 px-3 py-2 text-p-sm text-ink-gray-9 outline-none focus:border-outline-gray-4"
					:placeholder="__('Ask about this lesson...')"
					:disabled="loading || !sessionId"
					@keydown.enter.exact.prevent="send"
				/>
				<Button
					variant="solid"
					type="submit"
					:disabled="loading || !sessionId || !draft.trim()"
				>
					{{ __('Send') }}
				</Button>
			</form>
		</div>

		<button
			class="flex h-12 items-center gap-2 rounded-full bg-surface-gray-7 px-4 text-p-sm font-medium text-ink-white shadow-lg hover:bg-surface-gray-6"
			:aria-expanded="open"
			@click="toggle"
		>
			<span class="lucide-message-circle size-5" />
			<span class="hidden sm:inline">{{ __('AI Study Coach') }}</span>
		</button>
	</div>
</template>

<script setup>
import { Button, call } from 'frappe-ui'
import { nextTick, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const props = defineProps({
	lesson: { type: String, default: null },
})

// html:false stops raw HTML in the model's answer from being parsed at all; DOMPurify is the
// second line of defence for whatever markdown-it does emit.
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
const render = (text) =>
	DOMPurify.sanitize(md.render(text || ''), { USE_PROFILES: { html: true } })

const enabled = ref(false)
const open = ref(false)
const loading = ref(false)
const sessionId = ref(null)
const draft = ref('')
const messages = ref([])
const scroller = ref(null)

const errorText = (err) => {
	// Frappe puts the readable reason (our frappe.throw messages) in _server_messages.
	try {
		const raw = JSON.parse(err?.messages?.[0] || err?._server_messages || '[]')
		const first = typeof raw[0] === 'string' ? JSON.parse(raw[0]) : raw[0]
		if (first?.message) return first.message.replace(/<[^>]+>/g, '')
	} catch (e) {
		// fall through to the generic message
	}
	return err?.messages?.[0] || __('The AI Study Coach could not answer right now.')
}

const scrollDown = async () => {
	await nextTick()
	if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

const startSession = async () => {
	sessionId.value = null
	messages.value = []
	try {
		const data = await call('lms.lms.getlearn_chat.start_session', {
			lesson: props.lesson,
		})
		sessionId.value = data.session_id
		messages.value.push({ role: 'assistant', text: data.opening_message })
	} catch (err) {
		messages.value.push({ role: 'assistant', text: errorText(err), error: true })
	}
	scrollDown()
}

const toggle = async () => {
	open.value = !open.value
	if (open.value && !sessionId.value && !messages.value.length) await startSession()
}

const send = async () => {
	const text = draft.value.trim()
	if (!text || loading.value || !sessionId.value) return
	draft.value = ''
	messages.value.push({ role: 'user', text })
	loading.value = true
	scrollDown()
	try {
		const data = await call('lms.lms.getlearn_chat.send_message', {
			session_id: sessionId.value,
			message: text,
		})
		messages.value.push({
			role: 'assistant',
			text: data.message,
			sources: data.sources,
		})
	} catch (err) {
		messages.value.push({ role: 'assistant', text: errorText(err), error: true })
	} finally {
		loading.value = false
		scrollDown()
	}
}

// Moving to another lesson starts a fresh conversation scoped to that lesson.
watch(
	() => props.lesson,
	() => {
		sessionId.value = null
		messages.value = []
		if (open.value) startSession()
	},
)

onMounted(async () => {
	try {
		const cfg = await call('lms.lms.getlearn_chat.get_chat_config')
		enabled.value = !!cfg?.enabled
	} catch (e) {
		enabled.value = false
	}
})
</script>

<style scoped>
.coach-prose :deep(p) {
	margin: 0 0 0.5rem;
}
.coach-prose :deep(p:last-child) {
	margin-bottom: 0;
}
.coach-prose :deep(ul),
.coach-prose :deep(ol) {
	margin: 0 0 0.5rem;
	padding-inline-start: 1.25rem;
}
.coach-prose :deep(ul) {
	list-style: disc;
}
.coach-prose :deep(ol) {
	list-style: decimal;
}
.coach-prose :deep(code) {
	font-size: 0.85em;
}
</style>
