import frappe  , click
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():

    add_additional_fields()

    click.secho("Setup Optima HR Successfully" , fg="blue")


def add_additional_fields():
    
    custom_fields = {

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

    }

    create_custom_fields(custom_fields , update=True)

