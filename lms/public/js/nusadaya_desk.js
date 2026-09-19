/*
 * Nusadaya Desk branding.
 *
 * 1. Every outbound Frappe / ERPNext link becomes a dead link (help results,
 *    dialogs, any other anchor). Standard navbar items cannot be deleted in
 *    Frappe, so entries that carry the Frappe name are hidden by CSS instead.
 * 2. Visible strings that name Frappe are renamed through the `__()`
 *    translation function (see RENAMES).
 *
 * Loaded via `app_include_js` in hooks.py; delete that line to revert.
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

	// exact source strings -> replacement shown to users
	var RENAMES = {
		"Frappe Light": "Light", // theme switcher
		"Frappe Framework": "Nusadaya Academy",
		"Frappe Support": "Support",
	};

	var nativeTranslate = window.__;
	if (typeof nativeTranslate === "function") {
		window.__ = function (text) {
			if (typeof text === "string" && Object.prototype.hasOwnProperty.call(RENAMES, text)) {
				arguments[0] = RENAMES[text];
			}
			return nativeTranslate.apply(this, arguments);
		};
		for (var key in nativeTranslate) {
			if (Object.prototype.hasOwnProperty.call(nativeTranslate, key)) window.__[key] = nativeTranslate[key];
		}
	}

	window.nusadayaIsFrappeUrl = isFrappeUrl;
})();
