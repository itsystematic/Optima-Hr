import frappe  , click
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():

    add_additional_fields()

    click.secho("Setup Optima HR Successfully" , fg="blue")


def add_additional_fields():
    
    custom_fields = {
        "Shift Type" : [
            {
                "fieldname" : "section_break_40" ,
                "insert_after" : "early_exit_grace_period" ,
                "fieldtype" : "Section Break" ,
                "label" : "Auto Attendance Settings",
            },
            {
                "fieldname":"early_checkout",
                "fieldtype":"Table",
                "label":"Early Checkout",
                "options" :"Auto Attendance Settings",
                "insert_after" :"section_break_40"
            },
            {
                "fieldname":"overtime",
                "fieldtype":"Table",
                "label":"Overtime",
                "options" :"Auto Attendance Settings",
                "insert_after" :"early_checkout"
            },
            {
                "fieldname" :"column_break_41" ,
                "insert_after" :"overtime",
                "fieldtype" :"Column Break"
            },
            {
                "fieldname":"late_checkin",
                "fieldtype":"Table",
                "label":"Late Checkin",
                "options" :"Auto Attendance Settings",
                "insert_after" :"column_break_41"
            },
            {
                "fieldname":"late_or_early_checkin",
                "fieldtype":"Table",
                "label":"Late or Early Checkin ",
                "options" :"Auto Attendance Settings",
                "insert_after" :"late_checkin"
            },
        ],

        "Employee": [
            {
                "fieldname": "is_vacationer",
                "fieldtype": "Check",
                "label": "Is vacationer",
                "insert_after": "date_of_joining",
            },
        ] ,
        "Attendance": [
            {
                "fieldname" : "is_vacation" ,
                "fieldtype" : "Check" ,
                "label" : "Is vacation" ,
                "insert_after" : "employee",
                "hidden" : 1 ,
            }
        ] ,
        "Salary Component" :[
            {
                "fieldname" : "salary_effect" ,
                "fieldtype" : "Check" ,
                "label"     : "Salary Effect" ,
                "insert_after" : "remove_if_zero_valued" ,
            } ,
            {
                "fieldname" : "absent" ,
                "fieldtype" : "Check" ,
                "label"     : "Absent" ,
                "insert_after" : "salary_effect" ,
                "depends_on" : "eval: doc.hours == 0 && doc.salary_effect == 1"
            } ,
            {
                "fieldname" : "hours" ,
                "fieldtype" : "Check" ,
                "label"     : "Hours" ,
                "insert_after" : "absent" ,
                "depends_on" : "eval: doc.absent == 0 && doc.salary_effect == 1"
            } ,
            {
                "fieldname" : "percent" ,
                "fieldtype" : "Float" ,
                "label"     : "Percent" ,
                "insert_after" : "hours" ,
                "depends_on" : "eval: doc.hours==1 || doc.absent==1 ;" ,
                "mandatory_depends_on" : "eval: doc.hours==1 || doc.absent==1 ;"
            } ,
            {
                "fieldname" : "is_account_total_in_salary_effect" ,
                "fieldtype" : "Check" ,
                "label"     : "Is Account Total In Salary Effect" ,
                "insert_after" : "percent" ,
            } ,
            {
                "fieldname" : "is_salary_structure_assignment_componant" ,
                "fieldtype" : "Check" ,
                "label"     : "Is Salary Structure Assignment Componant" ,
                "insert_after" : "is_account_total_in_salary_effect" ,
            } ,
            {
                "fieldname" : "ssa_name" ,
                "fieldtype" : "Data" ,
                "label"     : "SSA Name" ,
                "insert_after" : "is_salary_structure_assignment_componant" ,
                "depends_on" : "eval: doc.is_salary_structure_assignment_componant ==1 ;" ,
                "mandatory_depends_on" : "eval: doc.is_salary_structure_assignment_componant ==1 ;" ,
            } ,
        ]
    }

    create_custom_fields(custom_fields , update=True)

