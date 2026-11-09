"""Optional HR features, switched on from the "Feed HR Features" tab of Optima HR Setting.

Everything here is OFF by default, so sites that do not use these features see optima_hr exactly as
before. The fixtures ship hidden / inactive / disabled and `apply()` turns on what the settings ask
for. It runs after every migrate, because a fixture sync restores the shipped state, and whenever a
settings record changes.
"""

import json

import frappe

SETTINGS = "Optima HR Setting"
CACHE_KEY = "optima_hr:features"
WORKSPACE = "HR"
WORKSPACE_CARD = "KSA HR Services"
WORKSPACE_CARD_ID = "optimaHrKsaCard"

FEATURES = {
	"enable_iqama_renewal": {
		"doctypes": ["Iqama Renewal"],
		"workflows": ["Iqama Renewal Approval"],
		"notifications": ["Iqama Expiry - 30 Days"],
		"links": [("Iqama Renewals", "Iqama Renewal")],
	},
	"enable_overtime_request": {
		"doctypes": ["Overtime Request"],
		"workflows": ["Overtime Request Approval"],
		"links": [("Overtime Requests", "Overtime Request")],
	},
	"enable_staff_housing": {
		"doctypes": ["Housing Unit"],
		"links": [("Staff Housing", "Housing Unit")],
	},
	"enable_employee_ksa_fields": {"sections": {"Employee": ["opf_ksa_sb", "opf_contract_sb"]}},
	"enable_feed_penalty_fields": {
		"fields": {
			"Employee Penalty": [
				"feed_deduction_section", "deduction_percent", "deduction_amount",
				"feed_deduction_cb", "additional_salary",
			],
		},
	},
	"enable_feed_letter_fields": {
		"fields": {
			"HR Letter": [
				"feed_letter_section", "directed_to", "gross_salary",
				"feed_letter_cb", "posting_date", "chamber_attestation",
			],
		},
	},
	"enable_feed_eos_fields": {
		"fields": {
			"End of Service Benefits": [
				"feed_request_section", "request_type", "feed_request_cb", "gratuity",
				"feed_reason_section", "reason",
			],
		},
	},
	"enable_permission_workflow": {"workflows": ["Permissions Approval"]},
	"enable_eos_workflow": {"workflows": ["End of Service Benefits Approval"]},
}

DOCTYPE_FEATURE = {dt: key for key, spec in FEATURES.items() for dt in spec.get("doctypes", [])}


# ------------------------------------------------------------------ state


def enabled_map() -> dict:
	"""{feature_key: bool}. The settings are per company; a feature is on if any company enables it."""

	def load():
		present = [key for key in FEATURES if frappe.db.has_column(SETTINGS, key)]
		rows = frappe.get_all(SETTINGS, fields=present) if present else []
		return {key: any(row.get(key) for row in rows) for key in FEATURES}

	return frappe.cache.get_value(CACHE_KEY, generator=load)


def is_enabled(key: str) -> bool:
	return enabled_map().get(key, False)


def clear_cache():
	frappe.cache.delete_value(CACHE_KEY)


# ------------------------------------------------------------------ permission hooks


def has_permission(doc, ptype=None, user=None, debug=False):
	key = DOCTYPE_FEATURE.get(doc.doctype)
	return True if not key else is_enabled(key)


def query_conditions(user=None, doctype=None):
	key = DOCTYPE_FEATURE.get(doctype)
	return "1=0" if key and not is_enabled(key) else ""


# ------------------------------------------------------------------ apply


def _section_fields(doctype, section):
	"""The section break itself plus every opf_ field up to the next section or tab."""
	out, inside = [], False
	for field in frappe.get_meta(doctype).fields:
		if field.fieldname == section:
			inside = True
		elif inside and field.fieldtype in ("Section Break", "Tab Break"):
			break
		if inside and field.fieldname.startswith("opf_"):
			out.append(field.fieldname)
	return out


def apply(*args, **kwargs):
	"""Make the site match the settings. Safe to run any number of times."""
	if not frappe.db.table_exists(SETTINGS):
		return
	clear_cache()
	on = enabled_map()
	touched = set()

	for key, spec in FEATURES.items():
		enabled = on[key]
		fields = dict(spec.get("fields", {}))
		for doctype, sections in spec.get("sections", {}).items():
			fields[doctype] = [name for section in sections for name in _section_fields(doctype, section)]
		for doctype, fieldnames in fields.items():
			for fieldname in fieldnames:
				name = f"{doctype}-{fieldname}"
				if frappe.db.get_value("Custom Field", name, "hidden") not in (None, 0 if enabled else 1):
					frappe.db.set_value("Custom Field", name, "hidden", 0 if enabled else 1, update_modified=False)
					touched.add(doctype)
		for name in spec.get("workflows", []):
			_set("Workflow", name, "is_active", int(enabled))
		for name in spec.get("notifications", []):
			_set("Notification", name, "enabled", int(enabled))

	for doctype in touched:
		frappe.clear_cache(doctype=doctype)
	_apply_workspace(on)


def _set(doctype, name, field, want):
	if not frappe.db.exists(doctype, name):
		return
	doc = frappe.get_doc(doctype, name)
	if int(doc.get(field) or 0) == want:
		return
	doc.set(field, want)
	doc.flags.ignore_permissions = True
	modified = doc.modified
	doc.save()
	# A feature switch is site state, not an edit to the shipped configuration.
	frappe.db.set_value(doctype, name, "modified", modified, update_modified=False)


def _apply_workspace(on):
	"""Add the card of the enabled features to the HR workspace, or remove it.

	Written directly to the tables: HR is a standard workspace, and a normal save would export it
	into the hrms app in developer mode or refuse the edit outside it.
	"""
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	wanted = [link for key, spec in FEATURES.items() if on[key] for link in spec.get("links", [])]
	owned = [doctype for spec in FEATURES.values() for _label, doctype in spec.get("links", [])]

	workspace = frappe.get_doc("Workspace", WORKSPACE)
	current = [row.link_to for row in workspace.links if row.type == "Link" and row.link_to in owned]
	blocks = json.loads(workspace.content or "[]")
	has_block = any(block.get("id") == WORKSPACE_CARD_ID for block in blocks)
	if current == [doctype for _label, doctype in wanted] and has_block == bool(wanted):
		return

	frappe.db.delete("Workspace Link", {"parent": WORKSPACE, "type": "Link", "link_to": ("in", owned)})
	frappe.db.delete("Workspace Link", {"parent": WORKSPACE, "type": "Card Break", "label": WORKSPACE_CARD})
	blocks = [block for block in blocks if block.get("id") != WORKSPACE_CARD_ID]

	if wanted:
		idx = max([row.idx for row in workspace.links] or [0])
		rows = [{"type": "Card Break", "label": WORKSPACE_CARD, "link_count": len(wanted)}]
		rows += [{"type": "Link", "label": label, "link_type": "DocType", "link_to": doctype} for label, doctype in wanted]
		for offset, row in enumerate(rows, start=1):
			frappe.get_doc(
				dict(row, doctype="Workspace Link", parent=WORKSPACE, parenttype="Workspace", parentfield="links", idx=idx + offset)
			).db_insert()
		blocks.append({"id": WORKSPACE_CARD_ID, "type": "card", "data": {"card_name": WORKSPACE_CARD, "col": 4}})

	frappe.db.set_value("Workspace", WORKSPACE, "content", json.dumps(blocks, ensure_ascii=False), update_modified=False)
	frappe.clear_cache()
