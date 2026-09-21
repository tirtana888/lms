import { call } from 'frappe-ui'
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { sessionStore } from '@/stores/session'

// The server keeps a user "present" for 90 seconds after a ping, so this must stay
// comfortably under a third of that to survive a missed request.
export const PING_INTERVAL_MS = 30000
// Two pings closer than this are one ping (a burst of route changes, tab switching).
const MIN_GAP_MS = 2000

/**
 * Tells the server this tab is open and visible, so the admin dashboard can show who
 * is using the LMS right now. Pings stop while the tab is hidden and resume when it
 * is shown again. Failures are ignored: presence must never disturb the page.
 */
export function usePresence() {
	const route = useRoute()
	const session = sessionStore()

	let timer = null
	let lastPingAt = 0

	const isVisible = () => document.visibilityState === 'visible'

	async function ping() {
		if (!session.isLoggedIn || !isVisible()) return
		const now = Date.now()
		if (now - lastPingAt < MIN_GAP_MS) return
		lastPingAt = now
		try {
			await call('lms.lms.presence.ping', {
				page: route.name ? String(route.name) : null,
				course: route.params?.courseName ? String(route.params.courseName) : null,
			})
		} catch (e) {
			// Offline, logged out elsewhere, or a deploy in progress: try again next tick.
		}
	}

	function stop() {
		if (timer !== null) clearInterval(timer)
		timer = null
	}

	function start() {
		stop()
		ping()
		timer = setInterval(ping, PING_INTERVAL_MS)
	}

	function onVisibilityChange() {
		if (isVisible()) start()
		else stop()
	}

	onMounted(() => {
		document.addEventListener('visibilitychange', onVisibilityChange)
		if (isVisible()) start()
	})

	onBeforeUnmount(() => {
		document.removeEventListener('visibilitychange', onVisibilityChange)
		stop()
	})

	// Report a new location straight away instead of waiting for the next tick.
	watch(
		() => [route.name, route.params?.courseName],
		() => ping()
	)
	// Signing in without a page reload starts the heartbeat; signing out ends it.
	watch(
		() => session.isLoggedIn,
		(loggedIn) => (loggedIn ? start() : stop())
	)
}

/**
 * "<1 min", "25 min", "1 h 5 min", "2 h": how long someone has been online, from seconds.
 * Language-neutral abbreviations, so it needs no translation.
 */
export function formatOnlineFor(seconds) {
	const minutes = Math.floor(Math.max(0, Number(seconds) || 0) / 60)
	if (minutes < 1) return '<1 min'
	if (minutes < 60) return `${minutes} min`
	const hours = Math.floor(minutes / 60)
	const rest = minutes % 60
	return rest ? `${hours} h ${rest} min` : `${hours} h`
}
