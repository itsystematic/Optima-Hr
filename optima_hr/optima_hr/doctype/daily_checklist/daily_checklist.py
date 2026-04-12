# Copyright (c) 2026, IT Systematic Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, date
from calendar import monthrange


class DailyChecklist(Document):
	def on_submit(self):
		"""
		Create or update Project Monthly Effects records when Daily Checklist is submitted
		"""
  
		self.process_project_monthly_effects()
		self.create_attendance()

	
	def on_cancel(self):
		"""
		Reverse Project Monthly Effects records when Daily Checklist is cancelled
		"""
  
		self.reverse_project_monthly_effects()
		self.cancel_attendance()

	
	def process_project_monthly_effects(self):
		"""
		Main orchestrator that processes each row in Daily Checklist Details.
		Creates or updates Project Monthly Effects records for each unique employee_project.
		"""
		try:
			if not self.date or not self.table_chlk:
				frappe.log_error("Missing date or table_chlk in Daily Checklist", "Daily Checklist")
				return
			
			month_info = self._get_month_info()

			# Validate that no submitted record exists for the month before proceeding
			self._validate_no_submitted_record(month_info)
			
			# Check if monthly record exists
			existing_record = self._get_existing_record(month_info)
			
			if existing_record:
				# Update existing monthly record
				pme_doc = frappe.get_doc("Project Monthly Effects", existing_record.name)
			else:
				# Create new monthly record
				pme_doc = self._create_pme_doc(month_info)
			
			# Process each row individually
			for row in self.table_chlk:
				if not row.employee_project or not row.employee:
					frappe.log_error(f"Missing employee_project or employee in row: {row.idx}", "Daily Checklist")
					continue
				
				# Validate employee_project exists
				if not self._validate_employee_project(row.employee_project):
					frappe.log_error(f"Employee Project '{row.employee_project}' not found for row {row.idx}", "Daily Checklist")
					continue
				
				frappe.msgprint(f"Processing Employee: {row.employee} in Project: {row.employee_project}")
				self._add_or_update_employee(pme_doc, row)
			
			# Save the monthly record
			self._save_pme(pme_doc, month_info, is_new=(not existing_record))
		
		except Exception as e:
			frappe.log_error(f"Error in process_project_monthly_effects: {str(e)}", "Daily Checklist")
			raise e
	
	def reverse_project_monthly_effects(self):
		"""
		Reverse the Project Monthly Effects by subtracting values when canceling.
		"""
		try:
			if not self.date or not self.table_chlk:  
				frappe.log_error("Missing date or table_chlk in Daily Checklist", "Daily Checklist")
				return
			
			month_info = self._get_month_info()
			
			# Get existing record
			existing_record = self._get_existing_record(month_info)
			
			if not existing_record:
				frappe.log_error(f"No existing Project Monthly Effects record found to reverse for {month_info['month_name']}", "Daily Checklist")
				return
				
			# Get the PME document
			pme_doc = frappe.get_doc("Project Monthly Effects", existing_record.name)
			
			# Map daily checklist rows with PME doc rows and subtract values
			for row in self.table_chlk:
				if not row.employee_project or not row.employee:
					frappe.log_error(f"Missing employee_project or employee in row: {row.idx}", "Daily Checklist")
					continue
					
				# Use dedicated method for subtraction
				self._subtract_employee_values(pme_doc, row)
			
			# Save the PME record
			self._save_pme(pme_doc, month_info, is_new=False, action_type="reversed")
		
		except Exception as e:
			frappe.log_error(f"Error in reverse_project_monthly_effects: {str(e)}", "Daily Checklist")
			raise e
	
	def cancel_attendance(self):
		"""
		Cancel attendance records for employees in the daily checklist.
		Only cancels submitted attendance records that match the date and employees.
		"""
		try:
			if not self.date or not self.table_chlk:
				frappe.log_error("Missing date or table_chlk in Daily Checklist", "Daily Checklist")
				return
			
			# Extract all employees from checklist
			employees = [row.employee for row in self.table_chlk if row.employee]
			if not employees:
				return
			
			# Get submitted attendance records for these employees on this date
			attendance_to_cancel = self._get_submitted_attendance_records(employees)
			
			# Cancel attendance records
			cancelled_count = self._bulk_cancel_attendance(attendance_to_cancel)
			
			# Show summary message
			if cancelled_count > 0:
				frappe.msgprint(f"Attendance cancelled: {cancelled_count} records")
			else:
				frappe.msgprint("No attendance records found to cancel")
				
		except Exception as e:
			frappe.log_error(f"Error in cancel_attendance: {str(e)}", "Daily Checklist")
			raise e
	
	def _get_submitted_attendance_records(self, employees):
		"""
		Get all submitted attendance records for the given employees on the checklist date.
		Returns list of attendance record names.
		"""
		try:
			attendance_records = frappe.get_all(
				"Attendance",
				filters={
					"employee": ["in", employees],
					"attendance_date": self.date,
					"docstatus": 1  # Only submitted records
				},
				fields=["name", "employee"],
				limit_page_length=0
			)
			return attendance_records
		except Exception as e:
			frappe.log_error(f"Error in _get_submitted_attendance_records: {str(e)}", "Daily Checklist")
			return []
	
	def _bulk_cancel_attendance(self, attendance_records):
		"""
		Cancel multiple attendance records in batches for better performance.
		Returns the count of successfully cancelled records.
		"""
		if not attendance_records:
			return 0
		
		cancelled_count = 0
		batch_size = 50  # Process in batches
		
		try:
			for i in range(0, len(attendance_records), batch_size):
				batch = attendance_records[i:i + batch_size]
				
				for record in batch:
					try:
						attendance_doc = frappe.get_doc("Attendance", record.name)
						attendance_doc.cancel()
						cancelled_count += 1
					except Exception as e:
						frappe.log_error(
							f"Error cancelling attendance {record.name} for employee {record.employee}: {str(e)}", 
							"Daily Checklist Attendance Cancel"
						)
						continue
				
				# Commit batch to database
				frappe.db.commit()
			
			return cancelled_count
			
		except Exception as e:
			frappe.log_error(f"Error in _bulk_cancel_attendance: {str(e)}", "Daily Checklist")
			return cancelled_count
	
	def create_attendance(self):
		"""
		Create attendance records for each employee in the daily checklist.
		Optimized for performance with batch operations.
		"""
		try:
			if not self.date or not self.table_chlk:
				frappe.log_error("Missing date or table_chlk in Daily Checklist", "Daily Checklist")
				return
			
			# Extract all employees from checklist
			employees = [row.employee for row in self.table_chlk if row.employee]
			if not employees:
				return
			
			# Batch check existing attendance for all employees
			existing_employees = self._get_existing_attendance_employees(employees)
			
			# Prepare attendance records for bulk creation with unique employees
			employee_status = {}  # Track unique employees and their status + employee_project
			attendance_records = []
			skipped_count = 0
			
			# Group employees and determine status (Present if any row is present)
			for row in self.table_chlk:
				if not row.employee:
					continue
				
				if row.employee in existing_employees:
					if row.employee not in employee_status:  # Count skipped only once per employee
						skipped_count += 1
						employee_status[row.employee] = {"status": "skipped", "employee_project": row.employee_project}
					continue
				
				# If employee not processed yet, initialize as absent
				if row.employee not in employee_status:
					employee_status[row.employee] = {"status": "Absent", "employee_project": row.employee_project}
				
				# If any row shows present, override to Present (keep original employee_project)
				if row.present and employee_status[row.employee]["status"] != "skipped":
					employee_status[row.employee]["status"] = "Present"
			
			# Create unique attendance records
			for employee, data in employee_status.items():
				if data["status"] != "skipped":
					attendance_records.append({
						"doctype": "Attendance",
						"employee": employee,
						"attendance_date": self.date,
						"status": data["status"],
						"custom_employee_project": data["employee_project"]  # Use employee_project from row
					})
			
			# Bulk create and submit attendance records
			created_count = self._bulk_create_attendance(attendance_records)
			
			# Show summary message
			if created_count > 0 or skipped_count > 0:
				message = f"✅ Attendance processed: {created_count} created"
				if skipped_count > 0:
					message += f", {skipped_count} skipped (already exists)"
				frappe.msgprint(message)
				
		except Exception as e:
			frappe.log_error(f"Error in create_attendance: {str(e)}", "Daily Checklist")
			raise e
	
	def _get_existing_attendance_employees(self, employees):
		"""
		Batch query to get all employees who already have submitted attendance for the date.
		Returns a set of employee IDs.
		"""
		try:
			existing_attendance = frappe.get_all(
				"Attendance",
				filters={
					"employee": ["in", employees],
					"attendance_date": self.date,
					"docstatus": 1
				},
				fields=["employee"],
				pluck="employee"
			)
			return set(existing_attendance)
		except Exception as e:
			frappe.log_error(f"Error in _get_existing_attendance_employees: {str(e)}", "Daily Checklist")
			return set()  # Return empty set if error occurs
	
	def _bulk_create_attendance(self, attendance_records):
		"""
		Bulk create and submit attendance records for better performance.
		Returns the count of successfully created records.
		"""
		if not attendance_records:
			return 0
		
		created_count = 0
		batch_size = 50  # Process in batches to avoid memory issues
		
		try:
			for i in range(0, len(attendance_records), batch_size):
				batch = attendance_records[i:i + batch_size]
				
				for record_data in batch:
					try:
						attendance_doc = frappe.get_doc(record_data)
						attendance_doc.insert()
						attendance_doc.submit()
						created_count += 1
					except Exception as e:
						frappe.log_error(
							f"Error creating attendance for employee {record_data.get('employee')}: {str(e)}", 
							"Daily Checklist Attendance"
						)
						continue
				
				# Commit batch to database
				frappe.db.commit()
			
			return created_count
			
		except Exception as e:
			frappe.log_error(f"Error in _bulk_create_attendance: {str(e)}", "Daily Checklist")
			return created_count

	def _get_month_info(self):
		"""
		Extract and calculate month information from the checklist date.
		Returns a dictionary with year, month_num, month_name, start_date, and end_date.
		"""
		try:
			# Convert string date to date object if necessary
			if isinstance(self.date, str):
				checklist_date = datetime.strptime(self.date, '%Y-%m-%d').date()
			else:
				checklist_date = self.date
			
			year = checklist_date.year
			month_num = checklist_date.month
			month_name = datetime(year, month_num, 1).strftime("%B")
			
			start_date = date(year, month_num, 1)
			last_day = monthrange(year, month_num)[1]
			end_date = date(year, month_num, last_day)
			
			return {
				"year": year,
				"month_num": month_num,
				"month_name": month_name,
				"start_date": start_date,
				"end_date": end_date
			}
		except Exception as e:
			frappe.log_error(f"Error in _get_month_info: {str(e)}", "Daily Checklist")
			raise e
	
	def _get_existing_record(self, month_info):
		"""
		Query and return an existing Project Monthly Effects record.
		Returns the record if found, None otherwise.
		"""
		
		# Now check for draft records
		existing = frappe.get_list(
			"Project Monthly Effects",
			filters={
				"month": month_info["month_name"],
				"start_date": month_info["start_date"],
				"end_date": month_info["end_date"],
				"docstatus": 0
			},
			limit=1
		)
		return existing[0] if existing else None
	
	def _validate_no_submitted_record(self, month_info):
		"""
		Check if a submitted Project Monthly Effects record already exists.
		Throws an error if a submitted record is found.
		"""
		submitted_records = frappe.get_list(
			"Project Monthly Effects",
			filters={
				"month": month_info["month_name"],
				"start_date": month_info["start_date"],
				"end_date": month_info["end_date"],
				"docstatus": 1
			},
			limit=1
		)
		if submitted_records:
			frappe.throw(f"A submitted Effects already exists for {month_info['month_name']} {month_info['year']} , It cannot have a retroactive effect.")
	
	def _create_pme_doc(self, month_info):
		"""
		Create a new Project Monthly Effects document with initial data.
		"""
		try:
			pme_doc = frappe.get_doc({
				"doctype": "Project Monthly Effects",
				"start_date": month_info["start_date"],
				"end_date": month_info["end_date"],
				"month": month_info["month_name"]
			})
			
			# pme_doc.append("table_iogy", {
			# 	"employee": row.employee,
			# 	"total_overtime": float(row.overtime) if row.overtime else 0.0,
			# 	"total_deduction": float(row.deduction) if row.deduction else 0.0
			# })
			
			return pme_doc
		except Exception as e:
			frappe.log_error(f"Error in _create_pme_doc: {str(e)}", "Daily Checklist")
			raise e
	
	def _add_or_update_employee(self, pme_doc, row):
		"""
		Add a new employee entry or update existing one in the child table.
		"""
		try:
			for table_row in pme_doc.table_iogy:
				if table_row.employee == row.employee and table_row.employee_project == row.employee_project:
					frappe.msgprint(f"Updating existing entry for Employee: {row.employee} in Project: {row.employee_project}")
					# Make it cumulative - add to existing values
					table_row.total_overtime += float(row.overtime) if row.overtime else 0.0
					table_row.total_deduction += float(row.deduction) if row.deduction else 0.0
					return True
			
			# Employee not found, add new row
			pme_doc.append("table_iogy", {
				"employee": row.employee,
				"employee_project": row.employee_project,	
				"total_overtime": float(row.overtime) if row.overtime else 0.0,
				"total_deduction": float(row.deduction) if row.deduction else 0.0
			})
			return False
		except Exception as e:
			frappe.log_error(f"Error in _add_or_update_employee: {str(e)}", "Daily Checklist")
			raise e
	
	def _subtract_employee_values(self, pme_doc, row):
		"""
		Subtract employee values from existing records (for cancellation).
		Improved performance with better matching logic.
		"""
		try:
			rows_to_remove = []
			matched = False
			
			# Find matching row by employee and employee_project
			for idx, table_row in enumerate(pme_doc.table_iogy):
				if table_row.employee == row.employee and table_row.employee_project == row.employee_project:
					# Subtract values
					table_row.total_overtime -= float(row.overtime) if row.overtime else 0.0
					table_row.total_deduction -= float(row.deduction) if row.deduction else 0.0
					
					# Ensure values don't go below 0
					table_row.total_overtime = max(0.0, table_row.total_overtime)
					table_row.total_deduction = max(0.0, table_row.total_deduction)
					
					# If both values are 0, mark row for removal
					if table_row.total_overtime == 0.0 and table_row.total_deduction == 0.0:
						rows_to_remove.append(idx)
					
					matched = True
					break  # Early exit for performance
			
			# Remove rows with zero values (in reverse order to maintain indices)
			for idx in reversed(rows_to_remove):
				pme_doc.table_iogy.pop(idx)
			
			return matched
		except Exception as e:
			frappe.log_error(f"Error in _subtract_employee_values: {str(e)}", "Daily Checklist")
			raise e
	
	def _validate_employee_project(self, employee_project):
		"""
		Validate that employee_project exists.
		Returns True if valid, False otherwise.
		"""
		try:
			# Check if employee_project exists (adjust doctype name as needed)
			exists = frappe.db.exists("Employee Project", employee_project)
			if not exists:
				# Try alternative doctype names
				exists = frappe.db.exists("Project", employee_project)
			return bool(exists)
		except Exception as e:
			frappe.log_error(f"Error validating employee_project {employee_project}: {str(e)}", "Daily Checklist")
			return False
	
	def _save_pme(self, pme_doc, month_info, is_new=False, action_type="updated"):
		"""
		Save the Project Monthly Effects document and handle errors.
		"""
		try:
			if is_new:
				pme_doc.insert()
				action = "created"
			else:
				pme_doc.save()
				action = action_type if action_type else "updated"
			
			frappe.msgprint(
				f"✅ Project Monthly Effects record {action} for {month_info['month_name']} "
				f"{month_info['year']} "
			)
			return True
		except Exception as e:
			error_msg = str(e)
			# Truncate error message to avoid log title length issues
			if len(error_msg) > 100:
				error_msg = error_msg[:97] + "..."
				
			frappe.log_error(f"PME save error: {error_msg}", "Daily Checklist PME Save")
			frappe.msgprint(f"Warning: Could not save PME record. Check error logs.", alert=True)
			return False


@frappe.whitelist()
def get_filtered_employees(date, department=None, designation=None, employee_project=None, branch=None):
	"""
	Fetch employees based on filter criteria and date.
	
	Args:
		date: The date for the daily checklist
		department: Filter by department
		designation: Filter by designation
		employee_project: Filter by employee project
		branch: Filter by branch
	
	Returns:
		List of employee records matching the criteria
	"""
	try:
		 # Only active employees with a project assigned should be fetched
		filters = {"status": "Active", "custom_employee_project" : ["!=", ""]} 
		
		if department:
			filters["department"] = department
		
		if designation:
			filters["designation"] = designation
		
		if branch:
			filters["branch"] = branch
   
		if employee_project:
			filters["custom_employee_project"] = employee_project
		
		# Query Employee with standard fields
		employees = frappe.get_list(
			"Employee",
			filters=filters,
			fields=["name", "employee_name", "department", "designation", "branch" ,"custom_employee_project"],
			limit_page_length=500
		)
		
		return employees
	except Exception as e:
		frappe.log_error(f"Error in get_filtered_employees: {str(e)}", "Daily Checklist")
		frappe.throw(f"Error fetching employees: {str(e)}")
