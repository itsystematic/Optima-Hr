import frappe  , click
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate():

    add_additional_fields()

    click.secho("Setup Optima HR Successfully" , fg="blue")


def add_additional_fields():
    
    create_custom_fields(get_custom_fields() , update=True)



def get_custom_fields():
    custom_fields = {

        "Employee": [
            {
                "fieldname": "is_vacationer",
                "fieldtype": "Check",
                "label": "Is vacationer",
                "insert_after": "date_of_joining",
            },
            {
                "fieldname": "identification_",
                "fieldtype": "Tab Break",
                "label": "Identification",
                # "insert_after": "basic_details_tab",
            },
            {
                "fieldname": "nationality",
                "fieldtype": "Link",
                "label": "Nationality",
                "options": "Nationality",
                "insert_after": "identification_",
                
            },
            {
                "fieldname": "identification_document_type",
                "label": "Identification Document Type",
                "fieldtype": "Link",
                "options": "Identification Document Type",
                "insert_after": "nationality",
            },
            {
                "fieldname": "identification_document_number",
                "label": "Identification Document Number",
                "fieldtype": "Data",
                "insert_after": "identification_document_type",
                "depends_on": "eval:doc.identification_document_type",
                "mandatory_depends_on": "eval:doc.identification_document_type"
            },
            {
                "fieldname": "column_break_8t4r6",
                "fieldtype": "Column Break",
                "insert_after": "identification_document_number",
            },
            {
                "fieldname": "issue_date",
                "label": "Issue Date",
                "fieldtype": "Date",
                "insert_after": "column_break_8t4r6",
                "depends_on": "eval:doc.identification_document_type",
            },
            {
                "fieldname": "expire_date",
                "label": "Expire Date",
                "fieldtype": "Date",
                "insert_after": "issue_date",
                "depends_on": "eval:doc.identification_document_type",
                "mandatory_depends_on": "eval:doc.identification_document_type"
            },
            {
                "fieldname": "identification_place_of_issue",
                "label": "Identification Place Of Issue",
                "fieldtype": "Data",
                "insert_after": "expire_date",
                "depends_on": "eval:doc.identification_document_type",
                "translatable": 1,
            },
            {
                "fieldname": "is_saudi_arabia",
                "fieldtype": "Check",
                "label": "Is Saudi Arabia",
                "insert_after": "identification_place_of_issue",
                "hidden": 1,
                "fetch_from": "nationality.is_saudi_arabia",
            },
            {
                "fieldname":"guarantor_data",
                "fieldtype": "Section Break",
                "label": "Guarantor Data",
                "insert_after": "is_saudi_arabia",
                "depends_on": "eval: doc.is_saudi_arabia == 0",
            },
            {
                "fieldname": "guarantor_name",
                "label": "Guarantor Name",
                "fieldtype": "Data",
                "insert_after": "guarantor_data",
                "translatable": 1,
            },
            {
                "fieldname":"guarantor_number",
                "fieldtype": "Data",
                "label": "Guarantor Number",
                "insert_after": "guarantor_name",
                "translatable": 1,
            },
            {
                "fieldname": "guarantor_email",
                "label": "Guarantor Email",
                "fieldtype": "Data",
                "insert_after": "guarantor_number",
                "translatable": 1,
                
            },
            {
                "fieldname": "column_break_t0t1j",
                "fieldtype": "Column Break",
                "insert_after": "guarantor_email",
            },
            {
                "fieldname": "guarantor_phone",
                "label": "Guarantor Phone",
                "fieldtype": "Data",
                "insert_after": "column_break_t0t1j",
                "translatable": 1,
                "options": "Phone",
            },
            {
                "fieldname": "guarantor_address",
                "label": "Guarantor Address",
                "fieldtype": "Data",
                "insert_after": "guarantor_phone",
                "translatable": 1,
            }
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
    return custom_fields