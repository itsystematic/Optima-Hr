# Copyright (c) 2026, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProjectMonthlyEffects(Document):
	def on_submit(self):
		"""
		Create Additional Salary records for overtime and deductions when submitted
		"""
		try:
			self.create_additional_salary()
			self.update_percentages_for_salary_structure_assignment()
		except Exception as e:
			frappe.log_error(f"Error in on_submit: {str(e)}", "Project Monthly Effects on_submit")
			frappe.throw(f"Error creating Additional Salary: {str(e)}")
	
	def on_cancel(self):
		"""
		Cancel Additional Salary records when Project Monthly Effects is cancelled
		"""
		try:
			self.cancel_additional_salary()
			self.remove_percentages_for_salary_structure_assignment()

		except Exception as e:
			frappe.log_error(f"Error in on_cancel: {str(e)}", "Project Monthly Effects on_cancel")
			frappe.throw(f"Error cancelling Additional Salary: {str(e)}")
	
	def create_additional_salary(self):
		"""
		Create Additional Salary records for each employee's overtime and deduction
		Optimized with batch processing for better performance
		"""
		try:
			if not self.table_iogy:
				return
			
			# Get all unique employees
			employees = [row.employee for row in self.table_iogy if row.employee]
			if not employees:
				return
			
			# Batch operations for performance
			hourly_rates_cache = self._batch_calculate_hourly_rates(employees)
			existing_records = self._batch_check_existing_records(employees)
			
			# Prepare records to create
			records_to_create = []
			
			for row in self.table_iogy:
				if not row.employee or row.employee not in hourly_rates_cache:
					continue
				
				hourly_rate = hourly_rates_cache[row.employee]
				if hourly_rate <= 0:
					continue
				
				# Prepare overtime record if exists
				if row.total_overtime and row.total_overtime > 0:
					overtime_key = f"{row.employee}-Overtime"
					if overtime_key not in existing_records:
						overtime_amount = self._calculate_amount(hourly_rate, row.total_overtime, 1.0)
						if overtime_amount > 0:
							records_to_create.append({
								"employee": row.employee,
								"salary_component": "Overtime",
								"amount": overtime_amount ,
								"overwrite_salary_structure_amount": 0

							})
				
				# Prepare deduction record if exists
				if row.total_deduction and row.total_deduction > 0:
					deduction_key = f"{row.employee}-Deduction"
					if deduction_key not in existing_records:
						deduction_amount = self._calculate_amount(hourly_rate, row.total_deduction, 1.0)
						if deduction_amount > 0:
							records_to_create.append({
								"employee": row.employee,
								"salary_component": "Deduction",
								"amount": deduction_amount,
								"overwrite_salary_structure_amount": 0

							})
			
			# Batch create all records
			created_count = self._batch_create_additional_salary_records(records_to_create)
			
			if created_count > 0:
				frappe.msgprint(f"Additional Salary records created: {created_count}")
			
		except Exception as e:
			frappe.log_error(f"Error in create_additional_salary: {str(e)}", "Project Monthly Effects")
			raise e
	
	def cancel_additional_salary(self):
		"""
		Cancel Additional Salary records that were created from this Project Monthly Effects document
		"""
		try:
			# Get all Additional Salary records linked to this document
			additional_salary_records = self._get_linked_additional_salary_records()
			
			if not additional_salary_records:
				frappe.msgprint("No Additional Salary records found to cancel")
				return
			
			# Cancel all linked Additional Salary records
			cancelled_count = self._cancel_additional_salary_records(additional_salary_records)
			
			if cancelled_count > 0:
				frappe.msgprint(f"Additional Salary records cancelled: {cancelled_count}")
			
		except Exception as e:
			frappe.log_error(f"Error in cancel_additional_salary: {str(e)}", "Project Monthly Effects")
			raise e
	
	def _get_linked_additional_salary_records(self):
		"""
		Get all submitted Additional Salary records that reference this Project Monthly Effects document
		"""
		try:
			additional_salary_records = frappe.get_all(
				"Additional Salary",
				filters={
					"ref_doctype": "Project Monthly Effects",
					"ref_docname": self.name,
					"docstatus": 1  # Only submitted records
				},
				fields=["name", "employee", "salary_component"],
				limit_page_length=0
			)
			return additional_salary_records
		except Exception as e:
			frappe.log_error(f"Error getting linked Additional Salary records: {str(e)}", "Project Monthly Effects")
			return []
	
	def _cancel_additional_salary_records(self, records):
		"""
		Cancel multiple Additional Salary records
		"""
		if not records:
			return 0
		
		cancelled_count = 0
		batch_size = 50  # Process in batches
		
		try:
			for i in range(0, len(records), batch_size):
				batch = records[i:i + batch_size]
				
				for record in batch:
					try:
						additional_salary_doc = frappe.get_doc("Additional Salary", record.name)
						additional_salary_doc.cancel()
						cancelled_count += 1
					except Exception as e:
						frappe.log_error(
							f"Error cancelling Additional Salary {record.name} for employee {record.employee}: {str(e)}", 
							"Project Monthly Effects Cancel"
						)
						continue
				
				# Commit batch to database
				frappe.db.commit()
			
			return cancelled_count
			
		except Exception as e:
			frappe.log_error(f"Error in _cancel_additional_salary_records: {str(e)}", "Project Monthly Effects")
			return cancelled_count
	
	def _batch_calculate_hourly_rates(self, employees):
		"""
		Batch calculate hourly rates for multiple employees for better performance
		"""
		try:
			# Batch query all salary structure assignments
			salary_assignments = frappe.get_all(
				"Salary Structure Assignment",
				filters={
					"employee": ["in", employees],
					"docstatus": 1
				},
				fields=["employee", "base", "custom_allowance", "from_date"],
				order_by="from_date desc",
				limit_page_length=0
			)
			
			# Create hourly rates cache
			hourly_rates = {}
			processed_employees = set()
			
			# Get the latest salary assignment for each employee
			for assignment in salary_assignments:
				employee = assignment.employee
				if employee not in processed_employees:
					# Calculate hourly rate (assuming 30 days * 8 hours)
					monthly_salary = assignment.base + (assignment.custom_allowance or 0)
					hourly_rate = monthly_salary / (30 * 8)
					hourly_rates[employee] = round(hourly_rate, 2)
					processed_employees.add(employee)
			
			# Add 0 for employees without salary assignments
			for employee in employees:
				if employee not in hourly_rates:
					hourly_rates[employee] = 0
					frappe.log_error(f"No salary structure found for employee {employee}", "Project Monthly Effects")
			
			return hourly_rates
			
		except Exception as e:
			frappe.log_error(f"Error batch calculating hourly rates: {str(e)}", "Project Monthly Effects")
			return {}
	
	def _batch_check_existing_records(self, employees):
		"""
		Batch check for existing Additional Salary records to avoid duplicates
		"""
		try:
			existing_records = frappe.get_all(
				"Additional Salary",
				filters={
					"employee": ["in", employees],
					"payroll_date": self.end_date,
					"docstatus": ["!=", 2]  # Not cancelled
				},
				fields=["employee", "salary_component"],
				limit_page_length=0
			)
			
			# Create lookup set for O(1) checking
			existing_lookup = set()
			for record in existing_records:
				key = f"{record.employee}-{record.salary_component}"
				existing_lookup.add(key)
			
			return existing_lookup
			
		except Exception as e:
			frappe.log_error(f"Error batch checking existing records: {str(e)}", "Project Monthly Effects")
			return set()
	
	def _batch_create_additional_salary_records(self, records_data):
		"""
		Batch create Additional Salary records with transaction optimization
		"""
		if not records_data:
			return 0
		
		created_count = 0
		batch_size = 20  # Smaller batches for better transaction management
		
		try:
			for i in range(0, len(records_data), batch_size):
				batch = records_data[i:i + batch_size]
				
				for record_data in batch:
					try:
						additional_salary = frappe.get_doc({
							"doctype": "Additional Salary",
							"employee": record_data["employee"],
							"salary_component": record_data["salary_component"],
							"amount": record_data["amount"],
							"payroll_date": self.end_date,
							"is_recurring": 0,
							"ref_doctype": "Project Monthly Effects",
							"ref_docname": self.name,
							"overwrite_salary_structure_amount": record_data.get("overwrite_salary_structure_amount", 0)
						})
						
						additional_salary.insert()
						additional_salary.submit()
						created_count += 1
						
					except Exception as e:
						frappe.log_error(
							f"Error creating Additional Salary for {record_data['employee']}: {str(e)}",
							"Project Monthly Effects Batch Create"
						)
						continue
				
				# Commit each batch
				frappe.db.commit()
			
			return created_count
			
		except Exception as e:
			frappe.log_error(f"Error in batch creating Additional Salary records: {str(e)}", "Project Monthly Effects")
			return created_count
	
	def _calculate_hourly_rate(self, employee):
		"""
		Calculate hourly rate for an employee based on their salary structure
		(Kept for backward compatibility - use _batch_calculate_hourly_rates for better performance)
		"""
		try:
			# Get employee's salary structure assignment
			salary_assignment = frappe.get_list(
				"Salary Structure Assignment",
				filters={
					"employee": employee,
					"docstatus": 1
				},
				fields=["base", "custom_allowance"],
				order_by="from_date desc",
				limit=1
			)
			
			if not salary_assignment:
				frappe.log_error(f"No salary structure found for employee {employee}", "Project Monthly Effects")
				return 0
			
			# Calculate hourly rate (assuming 30 days * 8 hours)
			monthly_salary = salary_assignment[0].base + (salary_assignment[0].custom_allowance or 0)
			hourly_rate = monthly_salary / (30 * 8)
			
			return round(hourly_rate, 2)
			
		except Exception as e:
			frappe.log_error(f"Error calculating hourly rate for employee {employee}: {str(e)}", "Project Monthly Effects")
			return 0
	
	def _calculate_amount(self, hourly_rate, hours, rate_multiplier):
		"""
		Calculate amount based on hourly rate, hours, and rate multiplier
		"""
		try:
			amount = hourly_rate * hours * rate_multiplier
			return round(amount, 2)
		except Exception as e:
			frappe.log_error(f"Error calculating amount: {str(e)}", "Project Monthly Effects")
			return 0
	
 
	def update_percentages_for_salary_structure_assignment(self):
		"""
		Update payroll cost center percentages in salary structure assignment
		based on employee attendance distribution across projects/cost centers
		"""
		try:
			# Get employees from child table
			employees = self._get_employees_from_child_table()
			if not employees:
				frappe.msgprint("No employees found in child table")
				return
			
			# Batch get attendance records for all employees
			attendance_records = self._batch_get_attendance_records(employees)
			if not attendance_records:
				frappe.msgprint("No attendance records found for the period")
				return
			
			# Calculate cost center percentages for each employee
			employee_percentages = self._calculate_cost_center_percentages(attendance_records)
			if not employee_percentages:
				frappe.msgprint("No cost center percentages calculated")
				return
			
			# Batch update salary structure assignments
			updated_count = self._batch_update_salary_structure_assignments(employee_percentages)
			
			if updated_count > 0:
				frappe.msgprint(f"Salary Structure Assignment cost centers updated for {updated_count} employees")
			
		except Exception as e:
			frappe.log_error(f"Error in update_percentages_for_salary_structure_assignment: {str(e)}", "Project Monthly Effects")
			raise e
	
	def remove_percentages_for_salary_structure_assignment(self):
		"""
		Remove/reset payroll cost center percentages when document is cancelled
		"""
		try:
			# Get employees from child table
			employees = self._get_employees_from_child_table()
			if not employees:
				return
			
			# Reset cost center percentages for all employees
			reset_count = self._batch_reset_salary_structure_assignments(employees)
			
			if reset_count > 0:
				frappe.msgprint(f"Salary Structure Assignment cost centers reset for {reset_count} employees")
			
		except Exception as e:
			frappe.log_error(f"Error in remove_percentages_for_salary_structure_assignment: {str(e)}", "Project Monthly Effects")
			raise e
	
	def _get_employees_from_child_table(self):
		"""
		Get unique employees from table_iogy child table
		"""
		try:
			if not self.table_iogy:
				return []
			
			# Get unique employees from child table
			employees = list(set([row.employee for row in self.table_iogy if row.employee]))
			return employees
			
		except Exception as e:
			frappe.log_error(f"Error getting employees from child table: {str(e)}", "Project Monthly Effects")
			return []
	
	def _batch_get_attendance_records(self, employees):
		"""
		Batch get attendance records for employees within date range
		"""
		try:
			if not employees:
				return []
			
			# Batch query attendance records for all employees within date range
			attendance_records = frappe.get_all(
				"Attendance",
				filters={
					"employee": ["in", employees],
					"attendance_date": ["between", [self.start_date, self.end_date]],
					"docstatus": 1,  # Only submitted attendance
					"status": ["=", "Present"]  # just present records
				},
				fields=["employee", "attendance_date", "custom_employee_project"],
				order_by="employee, attendance_date",
				limit_page_length=0
			)
			
			return attendance_records
			
		except Exception as e:
			frappe.log_error(f"Error batch getting attendance records: {str(e)}", "Project Monthly Effects")
			return []
	
	def _calculate_cost_center_percentages(self, attendance_records):
		"""
		Calculate cost center percentages for each employee based on attendance
		"""
		try:
			if not attendance_records:
				
				return {}
			
			# Get unique employee projects to fetch cost centers
			employee_projects = list(set([
				record.custom_employee_project 
				for record in attendance_records 
				if record.custom_employee_project
			]))
			
			# Batch get cost centers for employee projects
			project_cost_centers = self._batch_get_project_cost_centers(employee_projects)
			
			# Calculate employee attendance distribution
			employee_data = {}
			
			for record in attendance_records:
				employee = record.employee
				project = record.custom_employee_project
				
				if not project or project not in project_cost_centers:
					continue
				
				cost_center = project_cost_centers[project]
				if not cost_center:
					continue
				
				# Initialize employee data
				if employee not in employee_data:
					employee_data[employee] = {
						"total_days": 0,
						"cost_centers": {}
					}
				
				# Count attendance per cost center
				if cost_center not in employee_data[employee]["cost_centers"]:
					employee_data[employee]["cost_centers"][cost_center] = 0
				
				employee_data[employee]["cost_centers"][cost_center] += 1
				employee_data[employee]["total_days"] += 1
			
			# Calculate percentages
			employee_percentages = {}
			
			for employee, data in employee_data.items():
				if data["total_days"] == 0:
					continue
				
				percentages = {}
				for cost_center, days in data["cost_centers"].items():
					percentage = round((days / data["total_days"]) * 100, 2)
					if percentage > 0:
						percentages[cost_center] = percentage
				
				if percentages:
					employee_percentages[employee] = percentages
			
			return employee_percentages
			
		except Exception as e:
			frappe.log_error(f"Error calculating cost center percentages: {str(e)}", "Project Monthly Effects")
			return {}
	
	def _batch_get_project_cost_centers(self, employee_projects):
		"""
		Batch get cost centers for employee projects
		"""
		try:
			if not employee_projects:
				return {}
			
			# Batch query employee projects to get cost centers
			project_records = frappe.get_all(
				"Employee Project",
				filters={
					"name": ["in", employee_projects]
				},
				fields=["name", "cost_center"],
				limit_page_length=0
			)
			
			# Create lookup dictionary
			project_cost_centers = {}
			for record in project_records:
				project_cost_centers[record.name] = record.cost_center
			
			return project_cost_centers
			
		except Exception as e:
			frappe.log_error(f"Error batch getting project cost centers: {str(e)}", "Project Monthly Effects")
			return {}
	
	def _batch_update_salary_structure_assignments(self, employee_percentages):
		"""
		Batch update payroll cost center percentages in salary structure assignments
		"""
		if not employee_percentages:
			return 0
		
		updated_count = 0
		employees = list(employee_percentages.keys())
		batch_size = 20  # Process in batches
		
		try:
			for i in range(0, len(employees), batch_size):
				batch_employees = employees[i:i + batch_size]
				
				# Optimized query: Get only the latest salary structure assignment per employee
				# Use SQL to avoid fetching all historical records
				employee_placeholders = ','.join(['%s'] * len(batch_employees))
				salary_assignments = frappe.db.sql(f"""
					SELECT DISTINCT t1.name, t1.employee
					FROM `tabSalary Structure Assignment` t1
					INNER JOIN (
						SELECT employee, MAX(from_date) as max_date
						FROM `tabSalary Structure Assignment` 
						WHERE employee IN ({employee_placeholders}) AND docstatus = 1
						GROUP BY employee
					) t2 ON t1.employee = t2.employee AND t1.from_date = t2.max_date
					WHERE t1.docstatus = 1
				""", tuple(batch_employees), as_dict=1)
				
				# Process each salary structure assignment
				for assignment in salary_assignments:
					employee = assignment.employee
					if employee not in employee_percentages:
						continue
					
					try:
						# Update payroll cost center child table
						success = self._update_payroll_cost_center(
							assignment.name, 
							employee_percentages[employee]
						)
						
						if success:
							updated_count += 1
							
					except Exception as e:
						frappe.log_error(
							f"Error updating salary assignment {assignment.name} for employee {employee}: {str(e)}",
							"Project Monthly Effects Cost Center Update"
						)
						continue
				
				# Commit each batch
				frappe.db.commit()
			
			return updated_count
			
		except Exception as e:
			frappe.log_error(f"Error in batch updating salary structure assignments: {str(e)}", "Project Monthly Effects")
			return updated_count
	
	def _update_payroll_cost_center(self, salary_assignment_name, cost_center_percentages):
		"""
		Update payroll cost center child table for a specific salary structure assignment
		"""
		try:
			# Delete existing payroll cost center entries
			frappe.db.delete("Employee Cost Center", {
				"parent": salary_assignment_name,
				"parenttype": "Salary Structure Assignment"
			})
			
			# Insert new payroll cost center entries
			for cost_center, percentage in cost_center_percentages.items():
				# Create new payroll cost center entry
				payroll_cost_center = frappe.get_doc({
					"doctype": "Employee Cost Center",
					"parent": salary_assignment_name,
					"parenttype": "Salary Structure Assignment",
					"parentfield": "payroll_cost_centers",
					"cost_center": cost_center,
					"percentage": percentage
				})
				payroll_cost_center.insert(ignore_permissions=True)
			
			# Commit the changes
			frappe.db.commit()
			
			return True
			
		except Exception as e:
			frappe.log_error(f"Error updating payroll cost center for {salary_assignment_name}: {str(e)}", "Project Monthly Effects")
			return False
	
	def _batch_reset_salary_structure_assignments(self, employees):
		"""
		Batch reset payroll cost center percentages for employees
		"""
		if not employees:
			return 0
		
		reset_count = 0
		batch_size = 20  # Process in batches
		
		try:
			for i in range(0, len(employees), batch_size):
				batch_employees = employees[i:i + batch_size]
				
				# Optimized query: Get only the latest salary structure assignment per employee
				# Use SQL to avoid fetching all historical records
				employee_placeholders = ','.join(['%s'] * len(batch_employees))
				salary_assignments = frappe.db.sql(f"""
					SELECT DISTINCT t1.name, t1.employee
					FROM `tabSalary Structure Assignment` t1
					INNER JOIN (
						SELECT employee, MAX(from_date) as max_date
						FROM `tabSalary Structure Assignment` 
						WHERE employee IN ({employee_placeholders}) AND docstatus = 1
						GROUP BY employee
					) t2 ON t1.employee = t2.employee AND t1.from_date = t2.max_date
					WHERE t1.docstatus = 1
				""", tuple(batch_employees), as_dict=1)
				
				# Process each salary structure assignment
				for assignment in salary_assignments:
					try:
						# Reset payroll cost center child table
						success = self._reset_payroll_cost_center(assignment.name)
						
						if success:
							reset_count += 1
							
					except Exception as e:
						frappe.log_error(
							f"Error resetting salary assignment {assignment.name}: {str(e)}",
							"Project Monthly Effects Cost Center Reset"
						)
						continue
				
				# Commit each batch
				frappe.db.commit()
			
			return reset_count
			
		except Exception as e:
			frappe.log_error(f"Error in batch resetting salary structure assignments: {str(e)}", "Project Monthly Effects")
			return reset_count
	
	def _reset_payroll_cost_center(self, salary_assignment_name):
		"""
		Reset/clear payroll cost center child table for a specific salary structure assignment
		"""
		try:
			# Delete all payroll cost center entries for this salary assignment
			frappe.db.delete("Employee Cost Center", {
				"parent": salary_assignment_name,
				"parenttype": "Salary Structure Assignment"
			})
			
			# Commit the changes
			frappe.db.commit()
			
			return True
			
		except Exception as e:
			frappe.log_error(f"Error resetting payroll cost center for {salary_assignment_name}: {str(e)}", "Project Monthly Effects")
			return False
