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
		except Exception as e:
			frappe.log_error(f"Error in on_submit: {str(e)}", "Project Monthly Effects on_submit")
			frappe.throw(f"Error creating Additional Salary: {str(e)}")
	
	def on_cancel(self):
		"""
		Cancel Additional Salary records when Project Monthly Effects is cancelled
		"""
		try:
			self.cancel_additional_salary()
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
								"amount": overtime_amount
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
								"amount": deduction_amount
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
							"ref_docname": self.name
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
	
	def _create_additional_salary_record(self, employee, salary_component, amount, is_recurring=0):
		"""
		Create Additional Salary record for the employee
		"""
		try:
			# Check if Additional Salary already exists for this employee and month
			existing = frappe.get_list(
				"Additional Salary",	
				filters={
					"employee": employee,
					"salary_component": salary_component,
					"payroll_date": self.end_date,
					"docstatus": ["!=", 2]  # Not cancelled
				},
				limit=1
			)
			
			if existing:
				frappe.log_error(f"Additional Salary already exists for {employee} - {salary_component}", "Project Monthly Effects")
				frappe.throw(f"🟡 Additional Salary already exists for {employee} - {salary_component}. please recheck and update the existing record.")
				return
			
			additional_salary = frappe.get_doc({
				"doctype": "Additional Salary",
				"employee": employee,
				"salary_component": salary_component,
				"amount": amount,
				"payroll_date": self.end_date,
				"is_recurring": is_recurring,
				"ref_doctype": "Project Monthly Effects",
				"ref_docname": self.name
			})
			
			additional_salary.insert()
			additional_salary.submit()
			
		except Exception as e:
			frappe.log_error(f"Error creating Additional Salary for {employee}: {str(e)}", "Project Monthly Effects")
			raise e
