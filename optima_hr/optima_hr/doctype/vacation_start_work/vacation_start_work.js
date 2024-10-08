
frappe.ui.form.on("Vacation Start Work", {

  employee(frm) {
    if (frm.doc.employee) {
      frappe.call({
        method: "get_last_doc_if_exists",
        doc : frm.doc,
        args: {
          employee: frm.doc.employee
        },
        callback(r) {
          if (r.message) {
            frm.set_value("vacation_start_date", r.message.leave_start_date);
            frm.set_value("vacation_end_date", r.message.leave_end_date);
            frm.set_value("applicable_leave_dues",r.message.name)
          }
        }
      });
    }
  },
  start_work_date(frm) {
    if (frm.doc.start_work_date < frm.doc.vacation_end_date) {
      frappe.throw(__("Start Work Date cannot be less than End Work Date"));
}}
})