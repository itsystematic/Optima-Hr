from hrms.payroll.doctype.additional_salary.additional_salary import AdditionalSalary


class CustomAdditionalSalary(AdditionalSalary):
    def validate_recurring_additional_salary_overlap(self):
        pass