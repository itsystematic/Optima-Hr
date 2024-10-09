

frappe.listview_settings["Attendance"].add_fields =  ["status", "attendance_date" , "custom_is_vacation"] ;

frappe.listview_settings["Attendance"].get_indicator = function (doc) {
	if (["Present", "Work From Home"].includes(doc.status)) {
		return [__(doc.status), "green", "status,=," + doc.status];
	} else if (doc.status == "Absent" && doc.custom_is_vacation == 1) {
		return [__("Vacation"), "blue", "status,=," + "Vacation"];
	} else if (["Absent", "On Leave"].includes(doc.status)) {
		return [__(doc.status), "red", "status,=," + doc.status];
	} else if (doc.status == "Half Day") {
		return [__(doc.status), "orange", "status,=," + doc.status];
	}
}
