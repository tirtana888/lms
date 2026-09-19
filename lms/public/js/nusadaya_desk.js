/*
 * Nusadaya Desk: turn every outbound Frappe / ERPNext link into a dead link.
 *
 * Covers the Help menu ("Frappe Support"), the About dialog (website, GitHub,
 * forum, social), help search results and any other anchor in Desk. Items stay
 * in place (Frappe refuses to delete standard navbar items); they just lead
 * nowhere. Loaded via `app_include_js` in hooks.py; delete that line to revert.
 */
(function () {
	"use strict";

	var FRAPPE_HOSTS = /(^|\.)(frappe\.io|frappe\.school|frappe\.cloud|frappe\.dev|frappecloud\.com|erpnext\.com)$/i;
	var FRAPPE_PATHS = /(^|\/)(github\.com\/frappe(\/|$)|[^/]*frappe-?tech)/i;

	function isFrappeUrl(href) {
		if (!href) return false;
		var url;
		try {
			url = new URL(href, window.location.href);
		} catch (e) {
			return false;
		}
		if (url.protocol !== "http:" && url.protocol !== "https:") return false;
		if (url.host === window.location.host) return false;
		return FRAPPE_HOSTS.test(url.hostname) || FRAPPE_PATHS.test(url.hostname + url.pathname);
	}

	function block(event) {
		var node = event.target;
		var anchor = node && node.closest ? node.closest("a[href]") : null;
		if (anchor && isFrappeUrl(anchor.getAttribute("href"))) {
			event.preventDefault();
			event.stopImmediatePropagation();
		}
	}

	// capture phase so we run before Frappe's own delegated handlers
	document.addEventListener("click", block, true);
	document.addEventListener("auxclick", block, true);

	var nativeOpen = window.open;
	window.open = function (url) {
		if (isFrappeUrl(String(url || ""))) return null;
		return nativeOpen.apply(window, arguments);
	};

	window.nusadayaIsFrappeUrl = isFrappeUrl;
})();
