<template>
	<div
		v-if="enabled"
		class="fixed bottom-20 start-4 z-40 flex flex-col items-start gap-3 sm:bottom-5"
		:class="sidebar.isSidebarCollapsed ? 'sm:start-[4.5rem]' : 'sm:start-[15rem]'"
	>
		<Transition name="gl-pop">
			<section
				v-if="open"
				role="dialog"
				aria-label="AI Study Coach"
				class="flex h-[34rem] max-h-[78vh] w-[24rem] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-outline-gray-2 bg-surface-base shadow-2xl"
			>
				<!-- Header -->
				<header class="flex items-center gap-3 border-b border-outline-gray-2 px-4 py-3">
					<div
						class="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#00A0E0]/15 text-[#00A0E0]"
					>
						<span class="lucide-sparkles size-4" />
					</div>
					<div class="min-w-0 flex-1">
						<div class="truncate text-p-base font-semibold text-ink-gray-9">
							AI Study Coach
						</div>
						<div class="truncate text-p-xs text-ink-gray-5">
							{{ currentLessonTitle ? `Lesson: ${currentLessonTitle}` : 'Teman belajarmu' }}
						</div>
					</div>
					<button
						class="rounded-lg p-2 text-ink-gray-5 transition hover:bg-surface-gray-2 hover:text-ink-gray-8 disabled:opacity-40"
						title="Mulai percakapan baru"
						aria-label="Mulai percakapan baru"
						:disabled="loading || starting"
						@click="newConversation"
					>
						<span class="lucide-square-pen size-4" />
					</button>
					<button
						class="rounded-lg p-2 text-ink-gray-5 transition hover:bg-surface-gray-2 hover:text-ink-gray-8"
						title="Tutup"
						aria-label="Tutup"
						@click="open = false"
					>
						<span class="lucide-x size-4" />
					</button>
				</header>

				<!-- Conversation -->
				<div
					ref="scroller"
					role="log"
					aria-live="polite"
					class="flex-1 space-y-3 overflow-y-auto px-4 py-4"
				>
					<div v-if="starting && !messages.length" class="space-y-3" aria-hidden="true">
						<div class="h-10 w-3/4 animate-pulse rounded-2xl bg-surface-gray-2" />
						<div class="ms-auto h-8 w-1/2 animate-pulse rounded-2xl bg-surface-gray-2" />
						<div class="h-14 w-4/5 animate-pulse rounded-2xl bg-surface-gray-2" />
					</div>

					<template v-for="item in items" :key="item.key">
						<div
							v-if="item.kind === 'divider'"
							class="flex items-center gap-2 py-1 text-p-xs text-ink-gray-5"
						>
							<span class="h-px flex-1 bg-outline-gray-2" />
							<span class="max-w-[85%] truncate">Lesson: {{ item.text }}</span>
							<span class="h-px flex-1 bg-outline-gray-2" />
						</div>

						<div
							v-else
							class="flex gl-fade"
							:class="item.role === 'user' ? 'justify-end' : 'justify-start'"
						>
							<div
								class="max-w-[88%] px-3.5 py-2.5 text-p-sm leading-relaxed"
								:class="
									item.role === 'user'
										? 'rounded-2xl rounded-br-md bg-[#3050A0] text-white'
										: item.error
											? 'rounded-2xl rounded-bl-md bg-surface-amber-1 text-ink-amber-6'
											: 'rounded-2xl rounded-bl-md bg-surface-gray-2 text-ink-gray-9'
								"
							>
								<div
									v-if="item.role === 'assistant' && !item.error"
									class="gl-prose"
									v-html="render(item.text)"
								/>
								<div v-else class="whitespace-pre-wrap break-words">{{ item.text }}</div>

								<button
									v-if="item.error && (item.retryText || item.retryLoad)"
									class="mt-2 text-p-xs font-medium underline underline-offset-2"
									@click="retry(item)"
								>
									Coba lagi
								</button>

								<div v-if="item.sources?.length" class="mt-2.5 flex flex-wrap gap-1.5">
									<span
										v-for="s in item.sources"
										:key="s.id"
										class="inline-flex max-w-full items-center gap-1 rounded-full bg-surface-gray-3 px-2 py-0.5 text-p-xs text-ink-gray-6"
										:title="s.title"
									>
										<span class="lucide-book-open size-3 shrink-0" />
										<span class="truncate">{{ s.title }}</span>
									</span>
								</div>
							</div>
						</div>
					</template>

					<!-- Typing indicator -->
					<div v-if="loading" class="flex justify-start" aria-label="Coach sedang mengetik">
						<div class="flex items-center gap-1 rounded-2xl rounded-bl-md bg-surface-gray-2 px-4 py-3">
							<span class="gl-dot" />
							<span class="gl-dot" style="animation-delay: 0.15s" />
							<span class="gl-dot" style="animation-delay: 0.3s" />
						</div>
					</div>

					<!-- Quick questions, only before the first question -->
					<div v-if="showSuggestions" class="flex flex-wrap gap-2 pt-1">
						<button
							v-for="q in suggestions"
							:key="q"
							class="rounded-full border border-[#3050A0]/30 bg-[#3050A0]/5 px-3 py-1.5 text-p-xs text-ink-gray-8 transition hover:border-[#00A0E0]/60 hover:bg-[#00A0E0]/10"
							@click="ask(q)"
						>
							{{ q }}
						</button>
					</div>
				</div>

				<!-- Composer -->
				<form class="border-t border-outline-gray-2 p-3" @submit.prevent="send">
					<div class="flex items-end gap-2">
						<textarea
							id="getlearn-chat-input"
							ref="input"
							v-model="draft"
							rows="1"
							maxlength="1000"
							class="max-h-28 min-h-10 flex-1 resize-none rounded-xl border border-outline-gray-2 bg-surface-gray-1 px-3 py-2.5 text-p-sm text-ink-gray-9 outline-none transition placeholder:text-ink-gray-4 focus:border-[#00A0E0] focus:ring-2 focus:ring-[#00A0E0]/25 disabled:opacity-60"
							placeholder="Tanya soal materi, tugas, atau nilaimu..."
							aria-label="Pertanyaan untuk AI Study Coach"
							:disabled="loading || !sessionId"
							@input="autosize"
							@keydown.enter.exact="onEnter"
						/>
						<button
							type="submit"
							class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#3050A0] text-white transition hover:bg-[#274285] disabled:cursor-not-allowed disabled:opacity-40"
							title="Kirim"
							aria-label="Kirim"
							:disabled="loading || !sessionId || !draft.trim()"
						>
							<span class="lucide-arrow-up size-4" />
						</button>
					</div>
					<div class="mt-1.5 flex items-center justify-between px-1 text-p-xs text-ink-gray-4">
						<span>Enter untuk kirim, Shift+Enter baris baru</span>
						<span v-if="draft.length > 800" :class="draft.length >= 1000 ? 'text-ink-red-4' : ''">
							{{ draft.length }}/1000
						</span>
					</div>
				</form>
			</section>
		</Transition>

		<button
			class="flex h-12 items-center gap-2 rounded-full bg-[#3050A0] px-4 text-p-sm font-medium text-white shadow-lg transition hover:bg-[#274285]"
			:aria-expanded="open"
			aria-label="Buka AI Study Coach"
			@click="toggle"
		>
			<span class="relative flex">
				<span class="lucide-message-circle size-5" />
				<span
					class="absolute -end-0.5 -top-0.5 size-2 rounded-full bg-[#00A0E0] ring-2 ring-[#3050A0]"
				/>
			</span>
			<span class="hidden sm:inline">AI Study Coach</span>
		</button>
	</div>
</template>

<script setup>
import { call } from 'frappe-ui'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { useSidebar } from '@/stores/sidebar'

const props = defineProps({
	lesson: { type: String, default: null },
	lessonTitle: { type: String, default: null },
})

// html:false stops raw HTML in the model's answer from being parsed at all; DOMPurify is the
// second line of defence for whatever markdown-it does emit.
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
const render = (text) =>
	DOMPurify.sanitize(md.render(text || ''), { USE_PROFILES: { html: true } })

// Bottom-left, clear of the lesson outline on the right and (on desktop) of the app sidebar.
const sidebar = useSidebar()

const enabled = ref(false)
const open = ref(false)
const starting = ref(false)
const loading = ref(false)
const sessionId = ref(null)
const draft = ref('')
const messages = ref([])
const scroller = ref(null)
const input = ref(null)

// One conversation follows the student from lesson to lesson: it is kept by getlearn.ai and
// reloaded from there, so switching lessons, reloading or using another device never loses it.
const currentLessonTitle = computed(
	() => props.lessonTitle || (props.lesson ? props.lesson.replace(/^\d+\s+/, '') : ''),
)

// Consecutive messages sent from a different lesson get a small divider, live and in history.
const items = computed(() => {
	const out = []
	let previous = null
	messages.value.forEach((m, i) => {
		if (m.lesson && m.lesson !== previous) {
			out.push({ kind: 'divider', key: `d${i}`, text: m.lessonTitle || m.lesson })
			previous = m.lesson
		}
		out.push({ kind: 'message', key: m.id || `m${i}`, ref: m, ...m })
	})
	return out
})

const suggestions = computed(() => [
	'Jelaskan inti lesson ini',
	'Kasih contoh dong',
	'Bagaimana progres belajarku?',
	'Tugas apa yang belum kukumpulkan?',
	'Berapa nilai quiz-ku?',
])
const showSuggestions = computed(
	() =>
		!!sessionId.value &&
		!loading.value &&
		!messages.value.some((m) => m.role === 'user'),
)

const errorText = (err) => {
	// Frappe puts the readable reason (our frappe.throw messages) in _server_messages.
	try {
		const raw = JSON.parse(err?.messages?.[0] || err?._server_messages || '[]')
		const first = typeof raw[0] === 'string' ? JSON.parse(raw[0]) : raw[0]
		if (first?.message) return first.message.replace(/<[^>]+>/g, '')
	} catch (e) {
		// fall through to the generic message
	}
	return err?.messages?.[0] || 'AI Study Coach belum bisa menjawab sekarang. Coba lagi sebentar.'
}

const scrollDown = async () => {
	await nextTick()
	if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

const autosize = () => {
	const el = input.value
	if (!el) return
	el.style.height = 'auto'
	el.style.height = `${Math.min(el.scrollHeight, 112)}px`
}

const fromHistory = (m) => ({
	id: m.id,
	role: m.role,
	text: m.text,
	sources: m.sources || [],
	lesson: m.lesson || null,
	lessonTitle: m.lesson_title || null,
})

const startSession = async (fresh = false) => {
	starting.value = true
	try {
		const data = await call('lms.lms.getlearn_chat.resume_session', { fresh: fresh ? 1 : 0 })
		sessionId.value = data.session_id
		messages.value = (data.messages || []).map(fromHistory)
	} catch (err) {
		sessionId.value = null
		messages.value = [{ role: 'assistant', text: errorText(err), error: true, retryLoad: true }]
	} finally {
		starting.value = false
		scrollDown()
	}
}

const toggle = async () => {
	open.value = !open.value
	if (open.value) {
		if (!sessionId.value) await startSession()
		else scrollDown()
		nextTick(() => input.value?.focus())
	}
}

const newConversation = async () => {
	if (loading.value || starting.value) return
	await startSession(true)
	nextTick(() => input.value?.focus())
}

const ask = async (text, { echo = true } = {}) => {
	const question = (text || '').trim()
	if (!question || loading.value || !sessionId.value) return
	if (echo) {
		messages.value.push({
			role: 'user',
			text: question,
			lesson: props.lesson,
			lessonTitle: currentLessonTitle.value,
		})
	}
	loading.value = true
	scrollDown()
	try {
		const data = await call('lms.lms.getlearn_chat.send_message', {
			session_id: sessionId.value,
			message: question,
			lesson: props.lesson,
		})
		messages.value.push({
			id: data.id || undefined,
			role: 'assistant',
			text: data.message,
			sources: data.sources,
			lesson: props.lesson,
			lessonTitle: currentLessonTitle.value,
		})
	} catch (err) {
		messages.value.push({
			role: 'assistant',
			text: errorText(err),
			error: true,
			retryText: question,
		})
	} finally {
		loading.value = false
		scrollDown()
	}
}

const send = async () => {
	const text = draft.value
	if (!text.trim()) return
	draft.value = ''
	nextTick(autosize)
	await ask(text)
	nextTick(() => input.value?.focus())
}

const onEnter = (e) => {
	// Do not send while an input method (e.g. IME) is still composing text.
	if (e.isComposing) return
	e.preventDefault()
	send()
}

const retry = async (item) => {
	if (item.retryLoad) {
		messages.value = []
		return startSession()
	}
	messages.value = messages.value.filter((m) => m !== item.ref)
	await ask(item.retryText, { echo: false })
}

watch(open, (isOpen) => {
	if (isOpen) scrollDown()
})

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
.gl-prose :deep(p) {
	margin: 0 0 0.5rem;
}
.gl-prose :deep(p:last-child) {
	margin-bottom: 0;
}
.gl-prose :deep(ul),
.gl-prose :deep(ol) {
	margin: 0 0 0.5rem;
	padding-inline-start: 1.25rem;
}
.gl-prose :deep(ul) {
	list-style: disc;
}
.gl-prose :deep(ol) {
	list-style: decimal;
}
.gl-prose :deep(li) {
	margin-bottom: 0.15rem;
}
.gl-prose :deep(strong) {
	font-weight: 600;
}
.gl-prose :deep(a) {
	color: #00a0e0;
	text-decoration: underline;
	text-underline-offset: 2px;
}
.gl-prose :deep(code) {
	font-size: 0.85em;
	padding: 0.1rem 0.3rem;
	border-radius: 0.3rem;
	background: rgba(127, 127, 127, 0.18);
}
.gl-prose :deep(blockquote) {
	margin: 0 0 0.5rem;
	padding-inline-start: 0.75rem;
	border-inline-start: 3px solid rgba(0, 160, 224, 0.6);
	opacity: 0.9;
}

/* typing dots */
.gl-dot {
	width: 6px;
	height: 6px;
	border-radius: 9999px;
	background: #00a0e0;
	opacity: 0.4;
	animation: gl-bounce 1s infinite ease-in-out;
}
@keyframes gl-bounce {
	0%,
	60%,
	100% {
		transform: translateY(0);
		opacity: 0.4;
	}
	30% {
		transform: translateY(-4px);
		opacity: 1;
	}
}

/* new messages ease in; the panel opens from its launcher */
.gl-fade {
	animation: gl-fade-in 0.22s ease-out;
}
@keyframes gl-fade-in {
	from {
		opacity: 0;
		transform: translateY(4px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}
.gl-pop-enter-active,
.gl-pop-leave-active {
	transition:
		opacity 0.18s ease,
		transform 0.18s ease;
	transform-origin: bottom left;
}
.gl-pop-enter-from,
.gl-pop-leave-to {
	opacity: 0;
	transform: translateY(8px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
	.gl-dot,
	.gl-fade {
		animation: none;
	}
	.gl-pop-enter-active,
	.gl-pop-leave-active {
		transition: none;
	}
}
</style>
