function makeTranslationFunction() {
	let messages = {};
	return {
		translate,
		load: () => Promise.allSettled([
			setup(),
			// TODO: load dayjs locales
		]),
	}

	async function setup() {
		if (window.frappe?.boot?.__messages) {
			messages = window.frappe?.boot?.__messages;
			return;
		}

		// const url = new URL("/api/method/frappe.translate.get_all_translations", location.origin);
		// url.searchParams.append("hash", window.frappe?.boot?.translations_hash || window._version_number || Math.random()); // for cache busting
		// url.searchParams.append("app", "hrms");
		const url = '/api/method/optima_hr.api.get_translations';
		const formData = new FormData();
		formData.append('lang', window.frappe?.boot?.lang);
		const headers = new Headers();
		headers.append('X-Frappe-CSRF-Token', window.csrf_token);

		try {
			const response = await fetch(url, { method: 'POST', body: formData, headers });
			const jsonResponse = await response.json();
			messages = jsonResponse.message || {}
			window.frappe.boot.__messages = messages
		} catch (error) {
			console.error("Failed to fetch translations:", error)
		}
	}

	function translate(txt, replace, context = null) {
		if (!txt || typeof txt != "string") return txt;

		let translated_text = "";
		let key = txt;
		if (context) {
			translated_text = messages[`${key}:${context}`];
		}
		if (!translated_text) {
			translated_text = messages[key] || txt;
		}
		if (replace && typeof replace === "object") {
			translated_text = format(translated_text, replace);
		}

		return translated_text;
	}

	function format(str, args) {
		if (str == undefined) return str;

		let unkeyed_index = 0;
		return str.replace(
			/\{(\w*)\}/g,
			(match, key) => {
				if (key === "") {
					key = unkeyed_index;
					unkeyed_index++;
				}
				if (key == +key) {
					return args[key] !== undefined ? args[key] : match;
				}
			}
		);
	}
}

const { translate, load } = makeTranslationFunction();

export const translationsPlugin = {
	async isReady() {
		await load();
	},
	install(/** @type {import('vue').App} */ app) {
		const __ = translate;
		// app.mixin({ methods: { __ } })
		app.config.globalProperties.__ = __;
		app.provide("$translate", __);
	},
}