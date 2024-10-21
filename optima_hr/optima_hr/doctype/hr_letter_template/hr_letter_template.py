# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class HRLetterTemplate(Document):
	pass


@frappe.whitelist()
def get_template(temp, doc):
	if isinstance(doc, str):
		doc = json.loads(doc)

	hr_l_temp = frappe.get_doc("HR Letter Template", temp)
	terms = None

	if hr_l_temp.terms :
		terms = frappe.render_template(hr_l_temp.terms, doc)

	return {"template": hr_l_temp, "terms": terms}