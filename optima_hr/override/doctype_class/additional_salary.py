from hrms.payroll.doctype.additional_salary.additional_salary import AdditionalSalary


class CustomAdditionalSalary(AdditionalSalary):
    def validate_recurring_additional_salary_overlap(self):
        pass

    def update_return_amount_in_employee_advance(self) :
        """ Disable Update  TO make sure return amount get from gl """
        pass