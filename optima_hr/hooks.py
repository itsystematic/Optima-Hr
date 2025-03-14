app_name = "optima_hr"
app_title = "Optima Hr KSA"
app_publisher = "IT Systematic Company"
app_description = "App For Customization of Hr KSA's projects"
app_email = "sales@itsystematic.com"
required_apps = ["frappe", "erpnext", "hrms"]
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "optima_hr",
# 		"logo": "/assets/optima_hr/logo.png",
# 		"title": "Optima Hr",
# 		"route": "/optima_hr",
# 		"has_permission": "optima_hr.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/optima_hr/css/css-rtl/almarai.css"
# app_include_js = "/assets/optima_hr/js/optima_hr.js"

# include js, css files in header of web template
# web_include_css = "/assets/optima_hr/css/optima_hr.css"
# web_include_js = "/assets/optima_hr/js/optima_hr.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "optima_hr/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Leave Application" : "public/js/leave_application.js" ,
    "Employee Advance" : "public/js/employee_advance.js" ,
    "Bank": "public/js/bank.js"
}
doctype_list_js = {
    "Attendance" : "public/js/list/attendance_list.js" ,
    "Employee" : "public/js/list/employee_list.js" ,
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "optima_hr/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "optima_hr.utils.jinja_methods",
# 	"filters": "optima_hr.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "optima_hr.install.before_install"
# after_install = "optima_hr.after_install.delete_genders"

# Uninstallation
# ------------

# before_uninstall = "optima_hr.uninstall.before_uninstall"
# after_uninstall = "optima_hr.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "optima_hr.utils.before_app_install"
after_app_install = "optima_hr.install.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "optima_hr.utils.before_app_uninstall"
# after_app_uninstall = "optima_hr.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "optima_hr.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways  

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Leave Allocation": "optima_hr.override.doctype_class.leave_allocation.OptimaLeaveAllocation",
    "Additional Salary": "optima_hr.override.doctype_class.additional_salary.CustomAdditionalSalary",
    "Payment Entry": "optima_hr.override.doctype_class.payment_entry.OptimaPaymentEntry",
    "Salary Slip": "optima_hr.override.doctype_class.salary_slip.CustomSalarySlip",
    "Employee Checkin": "optima_hr.override.doctype_class.employee_checkin.CustomEmployeeCheckin", 
    "Shift Type": "optima_hr.override.doctype_class.shift_type.OptimaShiftType",
    "Payroll Entry": "optima_hr.override.doctype_class.payroll_entry.OptimaPayrollEntry",
    "Leave Policy Assignment": "optima_hr.override.doctype_class.leave_policy_assignment.OptimaHRLeavePolicyAssignment",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Attendance": {
		"on_submit": "optima_hr.doc_events.attendance.attendance_on_submit",
	},
    "Shift Assignment": {
        "on_submit": "optima_hr.doc_events.shift-assignment.default_shift_assignment",
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    # "Cron": {
        # "0 0 1 * *": "optima_hr.tasks.cron.make_attendance_absent_for_unmarked_employee",
    # },
# 	"all": [
# 		"optima_hr.tasks.all"
# 	],
# 	"daily": [
# 		"optima_hr.tasks.daily"
# 	],
# 	"hourly": [
# 		"optima_hr.tasks.hourly"
# 	],
# 	"weekly": [
# 		"optima_hr.tasks.weekly"
# 	],
# 	"monthly": [
# 		"optima_hr.tasks.monthly"
# 	],
    "cron" : {
        "1 0 * * *": [
            "optima_hr.tasks.daily.daily_allocate_earned_leaves",
        ]
    }
}

# Testing
# -------

# before_tests = "optima_hr.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "optima_hr.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "optima_hr.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["optima_hr.utils.before_request"]
# after_request = ["optima_hr.utils.after_request"]

# Job Events
# ----------
# before_job = ["optima_hr.utils.before_job"]
# after_job = ["optima_hr.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"optima_hr.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


#fixtures=[
#    {
#        "dt": "Workspace",
#        "filters": {
#            "name": ["in", ["HR","Salary Payout" , "Employee Lifecycle" , "Shift & Attendance" , "Leaves"]]
#        }
#    }
#]

after_migrate = "optima_hr.migrate.after_migrate"
advance_payment_doctypes = ["Leave Dues", "End of Service Benefits" , "Employee Advance"]
website_route_rules = [{'from_route': '/attendance_log/<path:app_path>', 'to_route': 'attendance_log'}, {'from_route': '/attendance_log/<path:app_path>', 'to_route': 'attendance_log'},]