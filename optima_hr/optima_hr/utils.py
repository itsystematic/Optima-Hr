
import frappe
from frappe import _
from frappe.utils import now
from datetime import datetime
from erpnext.accounts.party import get_party_account
from frappe.utils import getdate , date_diff , get_year_start, flt , get_first_day , get_last_day , get_datetime , formatdate
from dateutil.relativedelta import relativedelta
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
from hrms.hr.utils import calculate_pro_rated_leaves , create_additional_leave_ledger_entry , round_earned_leaves

def get_optima_hr_settings(company) :
    if settings:= frappe.db.exists("Optima HR Setting", {"company": company}) :
        return frappe.get_doc("Optima HR Setting", settings)
    return {}

def get_company_setting_with_employee(employee) :
    
    default_company = frappe.db.get_value("Employee" , employee , "company" , cache=True)
    optima_settings = get_optima_hr_settings(default_company)
    
    return optima_settings

@frappe.whitelist()
def get_fields_for_leave_dues(parent,parentfield) :

    label_fields = frappe.db.get_all("Salary Component Fields"  ,{"parent" : parent, "parentfield" : parentfield }, pluck="field_name")
    # fields = list(map(lambda x : x.get("fieldname") , filter(lambda x : x.get("label") in label_fields ,frappe.get_meta("Salary Structure Assignment").fields) ))

    return label_fields

@frappe.whitelist()
def get_total_amount_for_salary_structure_assignment(employee , include_fields) :

    if not include_fields : return 0.00

    last_doc = frappe.db.get_all("Salary Structure Assignment" , {
        "employee" : employee ,
        "docstatus" : 1,
    },include_fields , order_by="creation desc" , limit=1 , as_list=True)

    total = sum(map(lambda x : x , last_doc[0])) if last_doc else 0.00
    return total

@frappe.whitelist()
def get_last_work_days_salary(employee, company, end_work_date):
    payroll_date_beginning = get_optima_hr_payroll_date_beginning(company)
    
    end_work_date = getdate(end_work_date)
    payroll_start_date = get_payroll_start_date(payroll_date_beginning, end_work_date)
    days_to_pay = date_diff(end_work_date, payroll_start_date) + 1
    
    fields = get_fields_for_leave_dues(company, "component_to_calculate_cost_of_day")
    total = get_total_amount_for_salary_structure_assignment(employee, fields)
    salary_per_day = total / 30
    remaining_salary = salary_per_day * days_to_pay
    
    return {
        "remaining_salary" : remaining_salary,
        "days_to_pay": days_to_pay
    }

@frappe.whitelist()
def get_leave_balance_amount(company,employee,leave_date):

    to_date = getdate(leave_date)
    leave_type = get_optima_hr_leave_type(company)
    fields = get_fields_for_leave_dues(company, "component_to_calculate_cost_of_day_for_leaves")
    total_amounts = get_total_amount_for_salary_structure_assignment(employee , fields)
    starting_day_of_current_year = get_year_start(datetime.now())

    outstanding_leave_balance = get_leave_balance_on(
        employee=employee,
        leave_type=leave_type,
        date=starting_day_of_current_year,
        to_date=to_date,
        consider_all_leaves_in_the_allocation_period=1
    )
    
    salary_per_day = total_amounts / 30
    outstanding_leave_amount = outstanding_leave_balance * salary_per_day
    
    return {
        "outstanding_leave_amount" : outstanding_leave_amount,
        "outstanding_leave_balance":outstanding_leave_balance
    }

def get_optima_hr_payroll_date_beginning(company):
    payroll_date_beginning = frappe.db.get_value("Optima HR Setting", {"company": company}, "payroll_date_beginning")
    return getdate(payroll_date_beginning)

def get_optima_hr_leave_type(company):
    leave_type = frappe.db.get_value("Optima HR Setting", {"company": company}, "leave_type")
    return leave_type

def get_payroll_start_date(payroll_date_beginning, end_work_date):
    payroll_day = payroll_date_beginning.day
    
    if end_work_date.day >= payroll_day:
        return end_work_date.replace(day=payroll_day)
    else:
        previous_month = end_work_date - relativedelta(months=1)
        return previous_month.replace(day=payroll_day)

def get_optima_hr_employee_advance_account(company):
    employee_advance_account = frappe.db.get_value("Optima HR Setting", {"company": company}, "employee_advance_account")
    return employee_advance_account

@frappe.whitelist()
def get_closing_balances(company, to_date, party):
    employee_advance_account = get_optima_hr_employee_advance_account(company)
    
    if not employee_advance_account:
        frappe.throw(_("Employee Advance Account not set in Optima HR Setting for this company."))

    gle = frappe.db.sql(
        """
        SELECT 
            party,
            SUM(debit) as total_debit,
            SUM(credit) as total_credit
        FROM `tabGL Entry`
        WHERE company = %(company)s
            AND is_cancelled = 0
            AND party_type = 'Employee'
            AND party = %(party)s
            AND posting_date <= %(to_date)s
            AND account = %(account)s
        GROUP BY party
        """,
        {
            "company": company,
            "to_date": to_date,
            "party": party,
            "account": employee_advance_account
        },
        as_dict=True,
    )
    if gle:
        total_debit = flt(gle[0].total_debit)
        total_credit = flt(gle[0].total_credit)
        closing_balance = total_debit - total_credit
        
        return {
            "closing_debit": closing_balance if closing_balance > 0 else 0,
            "closing_credit": abs(closing_balance) if closing_balance < 0 else 0
        }
    else:
        return {
            "closing_debit": 0,
            "closing_credit": 0
        }
    
@frappe.whitelist()
def create_payment_entry(doc) :
    import json

    doc = json.loads(doc)
    
    party_account = get_party_account("Employee" , doc.get("employee") , doc.get("company"))
    grand_total = 0
    outstanding_amount = 0
    allocated_amount = 0
    
    if doc.get("doctype") == "Leave Dues" :
        grand_total = doc.get("total_dues_amount")
        outstanding_amount = doc.get("total_dues_amount") - doc.get("paid_amount")
        allocated_amount = doc.get("total_dues_amount") - doc.get("paid_amount")
        
    elif  doc.get("doctype") == "End of Service Benefits":
        grand_total = doc.get("final_result")
        outstanding_amount = doc.get("final_result") - doc.get("paid_amount")
        allocated_amount = doc.get("final_result") - doc.get("paid_amount")
        
    
    payment_entry = frappe.new_doc("Payment Entry")
    payment_entry.posting_date = getdate()
    payment_entry.company = doc.get("company")
    payment_entry.payment_type = "Pay"
    payment_entry.party_type = "Employee"
    payment_entry.party = doc.get("employee") 
    payment_entry.paid_to = party_account
    
    if doc.get("doctype") == "Leave Dues" :
        payment_entry.paid_amount = doc.get("total_dues_amount")
        payment_entry.received_amount = doc.get("total_dues_amount")
    elif  doc.get("doctype") == "End of Service Benefits":
        payment_entry.paid_amount = doc.get("final_result")
        payment_entry.received_amount = doc.get("final_result")
        
    # payment_entry.source_exchange_rate = 1
    # payment_entry.target_exchange_rate = 1

    payment_entry.append(
        "references",
        {
            "reference_doctype": doc.get("doctype"),
            "reference_name": doc.get("name"),
            "bill_no": doc.get("posting_date"),
            "due_date": doc.get("posting_date"),
            "total_amount": grand_total,
            "outstanding_amount":  outstanding_amount,
            "allocated_amount": allocated_amount,
        },
    )
    payment_entry.setup_party_account_field()
    payment_entry.set_missing_values()
    payment_entry.set_missing_ref_details()
    payment_entry.set_amounts()
    
    return payment_entry

def create_additional_salary(**kwargs):
    """
        Base Method To Create Additional Salary From Doctype ( Permissions  , Employee Advance , Attendance )
    """
    additional_salary = frappe.new_doc('Additional Salary')
    additional_salary.employee = kwargs.get("employee")
    additional_salary.payroll_date = kwargs.get("posting_date", now())
    additional_salary.amount = kwargs.get("amount", 0)
    additional_salary.salary_component = kwargs.get("salary_component")
    additional_salary.ref_doctype = kwargs.get("ref_doctype")
    additional_salary.ref_docname = kwargs.get("ref_docname")
    additional_salary.overwrite_salary_structure_amount = 0
    additional_salary.save(ignore_permissions=True)
    additional_salary.submit()
    
    return additional_salary

def get_employee_salary(employee , child_table) :
    """ 
        Base Method To Get Employee Salary
    """
    employee_salary = get_company_setting_with_employee(employee).get("employee_salary" ,[])

    if not  employee_salary : return 0

    base_salary_fields = list(map(lambda x : x.get("field_name") , employee_salary ))

    last_salary = frappe.db.get_all("Salary Structure Assignment" , {"docstatus":1 , "employee" : employee} ,
                                    base_salary_fields  ,  order_by="creation desc" , limit=1 )

    if not last_salary : return 0

    return sum(last_salary[0].values())

def allow_edit_salary_slip(func):
    def wrapper(self, *args, **kwargs):
        # Get the company from the salary slip document itself
        company = self.company
        
        setting = frappe.get_value("Optima HR Setting", 
                                 {"company": company},
                                 "allow_to_edit_salary_slip_component")
        
        if not setting:
            # If setting is disabled, use parent class method
            parent_method = getattr(super(self.__class__, self), func.__name__)
            return parent_method(*args, **kwargs)
        
        # If setting is enabled, use the custom method
        return func(self, *args, **kwargs)
    return wrapper

# This method is used in Scheduled Job
def custom_get_earned_leaves():
    return frappe.get_all(
        "Leave Type",
        fields=[
            "name",
            "max_leaves_allowed",
            "earned_leave_frequency",
            "rounding",
            "allocate_on_day",
        ],
        filters={"is_earned_leave": 1 , "earned_leave_frequency" : "Daily"},
    )


def custom_check_effective_date(from_date, today, frequency, allocate_on_day):

    from_date = get_datetime(from_date)
    today = frappe.flags.current_date or get_datetime(today)
    expected_date = {
        "First Day": get_first_day(today),
        "Last Day": get_last_day(today),
        "Date of Joining": from_date,
    }[allocate_on_day]

    return True if expected_date.day == today.day and frequency == "Daily"  else False


def custom_update_previous_leave_allocation(allocation, annual_allocation, e_leave_type, date_of_joining):
    allocation = frappe.get_doc("Leave Allocation", allocation.name)
    annual_allocation = flt(annual_allocation, allocation.precision("total_leaves_allocated"))

    earned_leaves = custom_get_monthly_earned_leave(
        date_of_joining,
        annual_allocation,
        e_leave_type.earned_leave_frequency,
        e_leave_type.rounding,
    )

    new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)
    new_allocation_without_cf = flt(
        flt(allocation.get_existing_leave_count()) + flt(earned_leaves),
        allocation.precision("total_leaves_allocated"),
    )

    if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
        new_allocation = e_leave_type.max_leaves_allowed

    if (
        new_allocation != allocation.total_leaves_allocated
        # annual allocation as per policy should not be exceeded
        and new_allocation_without_cf <= annual_allocation
    ):
        today_date = frappe.flags.current_date or getdate()

        allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
        create_additional_leave_ledger_entry(allocation, earned_leaves, today_date)

        if e_leave_type.allocate_on_day:
            text = _(
                "Allocated {0} leave(s) via scheduler on {1} based on the 'Allocate on Day' option set to {2}"
            ).format(
                frappe.bold(earned_leaves), frappe.bold(formatdate(today_date)), e_leave_type.allocate_on_day
            )

        allocation.add_comment(comment_type="Info", text=text)

def custom_get_monthly_earned_leave(
    date_of_joining,
    annual_leaves,
    frequency,
    rounding,
    period_start_date=None,
    period_end_date=None,
    pro_rated=True,
):
    earned_leaves = 0.0
    divide_by_frequency = {"Yearly": 1, "Half-Yearly": 2, "Quarterly": 4, "Monthly": 12 , "Daily": 365}
    if annual_leaves:
        earned_leaves = flt(annual_leaves) / divide_by_frequency[frequency]

        if pro_rated:
            if not (period_start_date or period_end_date):
                today_date = frappe.flags.current_date or getdate()
                period_end_date = get_last_day(today_date)
                period_start_date = get_first_day(today_date)

            earned_leaves = calculate_pro_rated_leaves(
                earned_leaves, date_of_joining, period_start_date, period_end_date, is_earned_leave=True
            )

        earned_leaves = round_earned_leaves(earned_leaves, rounding)

    return earned_leaves