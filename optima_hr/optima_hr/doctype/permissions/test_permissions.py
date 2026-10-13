# Copyright (c) 2024, IT Systematic Company and Contributors
# See license.txt

"""In-memory tests for the From Time / To Time rules on Permissions.

Documents are built with ``frappe.get_doc`` and never inserted, so there is no
DB write and no teardown. A stored Time field reaches the browser without a
leading zero ("9:00:00") while the time picker sends one ("09:00:00"), and a
document loaded on the server holds ``timedelta`` values, so every case mixes
these representations.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.tests.utils import FrappeTestCase


def _permission(from_time, to_time):
	return frappe.get_doc({"doctype": "Permissions", "from_time": from_time, "to_time": to_time})


class TestValidateDifferenceTimeCalculation(FrappeTestCase):
	def test_to_time_after_from_time_passes(self):
		cases = [
			("09:00:00", "10:00:00"),
			# A plain string compare rejected this: "9:00:00" > "10:00:00".
			("9:00:00", "10:00:00"),
			(timedelta(hours=4), "10:00:00"),
			(timedelta(hours=9), timedelta(hours=10)),
		]
		for from_time, to_time in cases:
			with self.subTest(from_time=from_time, to_time=to_time):
				_permission(from_time, to_time).validate_difference_time_calculation()

	def test_to_time_not_after_from_time_throws(self):
		cases = [
			("09:00:00", "09:00:00"),
			("9:00:00", "09:00:00"),
			(timedelta(hours=9), "09:00:00"),
			("14:30:00", "09:15:00"),
			# A plain string compare accepted this: "10:00:00" > "9:00:00" is False.
			("10:00:00", "9:00:00"),
		]
		for from_time, to_time in cases:
			with self.subTest(from_time=from_time, to_time=to_time):
				doc = _permission(from_time, to_time)
				with self.assertRaises(frappe.ValidationError) as ctx:
					doc.validate_difference_time_calculation()
				self.assertEqual(str(ctx.exception), _("To Time Must be Greater Than From Time"))


class TestSetTimeDifference(FrappeTestCase):
	def test_computed_on_construction(self):
		cases = [
			("09:00:00", "10:00:00", timedelta(hours=1)),
			("9:00:00", "10:00:00", timedelta(hours=1)),
			("16:30:00", "17:31:00", timedelta(hours=1, minutes=1)),
			(timedelta(hours=4), "10:00:00", timedelta(hours=6)),
		]
		for from_time, to_time, expected in cases:
			with self.subTest(from_time=from_time, to_time=to_time):
				self.assertEqual(_permission(from_time, to_time).time_difference, expected)

	def test_recomputed_after_server_side_edit(self):
		doc = _permission(timedelta(hours=4), timedelta(hours=5, minutes=30))
		doc.to_time = "10:00:00"
		doc.set_time_difference()
		self.assertEqual(doc.time_difference, timedelta(hours=6))

	def test_left_unset_when_a_time_is_missing(self):
		for from_time, to_time in (("09:00:00", None), (None, "10:00:00")):
			with self.subTest(from_time=from_time, to_time=to_time):
				self.assertIsNone(_permission(from_time, to_time).time_difference)
