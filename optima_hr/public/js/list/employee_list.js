


frappe.listview_settings["Employee"].add_fields.unshift("is_vacationer")
frappe.listview_settings["Employee"].get_indicator = function (doc) {

    if (doc.status == "Inactive" && doc.is_vacationer == 1) {
        return [__("Vacationer"), "blue", "status,=," + "Vacationer"];
    }
}