# Copyright (c) 2024, IT Systematic Company and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns , data

def get_data(filters :dict ) -> list[dict] :
    
    conditions = ""
    
    
    if filters.get("from_date") and filters.get("to_date") :
        conditions += f" AND ss.start_date >= '{filters.get('from_date')}' AND ss.end_date <= '{filters.get('to_date')}' "
        
    if filters.get("company") :
        conditions += f" AND ss.company = '{filters.get('company')}' "
        
    if filters.get("docstatus") :
        conditions += f" AND ss.status = '{filters.get('docstatus')}' "
        
    if filters.get("employee") :
        conditions += f" AND ss.employee = '{filters.get('employee')}' "
        
    if filters.get("currency"):
        conditions += f" AND ss.currency = '{filters.get('currency')}' "
        
    # if filters.get("project"):
    #     conditions += f"AND e.custom_project = '{filters.get('project')}' "

    
    salary_slip_data = frappe.db.sql("""
    SELECT 
        ss.name AS salary_slip_id, 
        ss.employee, 
        ss.start_date, 
        ss.end_date, 
        ss.net_pay, 
        ss.total_deduction, 
        e.name AS employee_id_name, 
        e.passport_number, 
        e.bank_ac_no, 
        e.iban, 
        e.employee_name,
        t1.amount AS base_salary,  
        t2.amount AS house_allowance,
        CONCAT("Salary ", DATE_FORMAT(ss.start_date, %(format)s)) AS beneficiary_narration,
        (ss.gross_pay - (t2.amount + t1.amount)) AS other_earnings
    FROM 
        `tabSalary Slip` ss
    INNER JOIN 
        `tabEmployee` e ON ss.employee = e.name
    LEFT JOIN 
        `tabSalary Detail` t1 ON t1.parent = ss.name AND t1.parentfield = 'earnings' AND t1.salary_component = 'Basic'
    LEFT JOIN 
        `tabSalary Detail` t2 ON t2.parent = ss.name AND t2.parentfield = 'earnings' AND t2.salary_component = 'Housing Allowance'
    WHERE 
        e.salary_mode = "Bank"
        {conditions}
""".format(conditions=conditions), {
    "format": "%b %Y"
}, as_dict=True)
    
    return salary_slip_data
    #ss.mode_of_payment ="Bank"
    
def get_columns(filters: dict) -> list[dict] :

    if filters.get("bank_syle"):
        columns_to_field_map = get_field_mapping(filters)
        print(columns_to_field_map)

        sorted_items = sort_items_by_key(columns_to_field_map)
        print(type(sorted_items))
        columns = [
            {
                "label": " ".join(word.capitalize() for word in value.replace("_", " ").split()), # spit the column name by underscore and capitalize each word
                "fieldname": value,
                "fieldtype": "Data",
                "width": 150,
            }
            for _, value in sorted_items
        ]


        return columns
    # get salary component included in salary structure, to show in report as columns
    salary_struture_assignment_component =  frappe.get_all('Salary Component' , {'is_salary_structure_assignment_componant' : 1} , pluck='name')
    columns = [
        {
            "label": _("Salary Slip ID"),
            "fieldname": "salary_slip_id",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 200,
        },
        {
            "label": _("Employee ID"),
            "fieldname": "employee_id_name",
            "fieldtype": "Link",
			"options": "Employee",
            "width": 70,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 255,
        },
        # {
        #     "label": _("Employee Resident ID"),
        #     "fieldname": "identification_document_number",
        #     "fieldtype": "Data",
        #     "width": 120,
        # },
        {
            "label": _("Employee Bank ID"),
            "fieldname": "bank_ac_no",
            "fieldtype": "Data",
            "width": 255,
        },
        {
            "label": _("Employee Passport ID"),
            "fieldname": "passport_number",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Employee Account number"),
            "fieldname": "iban",
            "fieldtype": "Data",
            "width": 60,
        },
        {
            "label": ("Payment Amount"),
            "fieldname": "net_pay",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": ("Employee Basic Salary"),
            "fieldname": "base_salary",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        }
    ]
    # append salary component 
    if len(salary_struture_assignment_component) > 1:
        for component in salary_struture_assignment_component[:]:
            if component == "Basic": # Basic is already added
                continue
            columns.append({
                "label": _(component),
                "fieldname": component.lower().replace(" ", "_"),
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150,
            })
        # {
        #     "label": ("Housing Allowance"),
        #     "fieldname": "house_allowance",
        #     "fieldtype": "Currency",
        #     "options": "currency",
        #     "width":150,
        # },
        # {
        #     "label": ("Other Earnings"),
        #     "fieldname": "other_earnings",
        #     "fieldtype": "Currency",
        #     "options": "currency",
        #     "width":150,
        # },
    columns.extend(
        [
            {
                "label": ("Deductions"),
                "fieldname": "total_deduction",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 120,
            },
            {
                "label": ("Beneficiary Narration"),
                "fieldname": "beneficiary_narration",
                "fieldtype": "Data",
                "width":140,
            },
        ]
    )   
    
    return columns

def get_field_mapping(filters):
    column_to_field_map = {}
    bank = frappe.get_doc("Bank", filters.get("bank_syle"))
    for i in bank.bank_salary_slip_mapping:
        column_to_field_map[i.column_in_bank_file] = i.field_in_salary_slip

    return column_to_field_map

def sort_items_by_key(mapping):
    return sorted(mapping.items(), key=lambda x: x[0])