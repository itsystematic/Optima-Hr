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
		try:
			self.process_project_monthly_effects()
			self.create_attendance()
		except Exception as e:
			frappe.log_error(f"Error in on_submit: {str(e)}", "Daily Checklist on_submit")
			frappe.throw(f"Error processing Project Monthly Effects: {str(e)}")
	
	def on_cancel(self):
		"""
		Reverse Project Monthly Effects records when Daily Checklist is cancelled
		"""
		try:
			self.reverse_project_monthly_effects()
			self.cancel_attendance()
		except Exception as e:
			frappe.log_error(f"Error in on_cancel: {str(e)}", "Daily Checklist on_cancel")
			frappe.throw(f"Error reversing Project Monthly Effects: {str(e)}")
	
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
			
			# Group rows by employee_project for efficient processing
			projects_data = {}
			for row in self.table_chlk:
				if not row.employee_project or not row.employee:
					frappe.log_error(f"Missing employee_project or employee in row: {row.idx}", "Daily Checklist")
					continue
				
				if row.employee_project not in projects_data:
					projects_data[row.employee_project] = []
				projects_data[row.employee_project].append(row)
			
			# Process each project
			for employee_project, rows in projects_data.items():
				try:
					existing_record = self._get_existing_record(employee_project, month_info)
					
					if existing_record:
						# Update existing record
						pme_doc = frappe.get_doc("Project Monthly Effects", existing_record.name)
						for row in rows:
							self._add_or_update_employee(pme_doc, row)
						self._save_pme(pme_doc, month_info, employee_project, is_new=False)
					else:
						# Create new record for first row of this project
						pme_doc = self._create_pme_doc(employee_project, month_info, rows[0])
						
						# Add remaining rows
						for row in rows[1:]:
							pme_doc.append("table_iogy", {
								"employee": row.employee,
								"total_overtime": float(row.overtime) if row.overtime else 0.0,
								"total_deduction": float(row.deduction) if row.deduction else 0.0
							})
						
						self._save_pme(pme_doc, month_info, employee_project, is_new=True)
				except Exception as e:
					frappe.log_error(f"Error processing project {employee_project}: {str(e)}", "Daily Checklist")
					continue  # Continue with other projects even if one fails
		
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
			
			# Group rows by employee_project for efficient processing
			projects_data = {}
			for row in self.table_chlk:
				if not row.employee_project or not row.employee:
					frappe.log_error(f"Missing employee_project or employee in row: {row.idx}", "Daily Checklist")
					continue
				
				if row.employee_project not in projects_data:
					projects_data[row.employee_project] = []
				projects_data[row.employee_project].append(row)
			
			# Process each project
			for employee_project, rows in projects_data.items():
				try:
					existing_record = self._get_existing_record(employee_project, month_info)
					
					if existing_record:
						# Update existing record by subtracting values
						pme_doc = frappe.get_doc("Project Monthly Effects", existing_record.name)
						for row in rows:
							self._subtract_employee_values(pme_doc, row)
						self._save_pme(pme_doc, month_info, employee_project, is_new=False, action_type="reversed")
					else:
						frappe.log_error(f"No existing Project Monthly Effects record found to reverse for project {employee_project}", "Daily Checklist")
				except Exception as e:
					frappe.log_error(f"Error reversing project {employee_project}: {str(e)}", "Daily Checklist")
					continue  # Continue with other projects even if one fails
		
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
			
			# Prepare attendance records for bulk creation
			attendance_records = []
			skipped_count = 0
			
			for row in self.table_chlk:
				if not row.employee:
					continue
				
				if row.employee in existing_employees:
					skipped_count += 1
					continue
				
				attendance_records.append({
					"doctype": "Attendance",
					"employee": row.employee,
					"attendance_date": self.date,
					"status": "Present" if row.present else "Absent"
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
	
	def _get_existing_record(self, employee_project, month_info):
		"""
		Query and return an existing Project Monthly Effects record.
		Returns the record if found, None otherwise.
		"""
		try:
			existing = frappe.get_list(
				"Project Monthly Effects",
				filters={
					"employee_project": employee_project,
					"month": month_info["month_name"],
					"start_date": month_info["start_date"],
					"end_date": month_info["end_date"]
				},
				limit=1
			)
			return existing[0] if existing else None
		except Exception as e:
			frappe.log_error(f"Error in _get_existing_record: {str(e)}", "Daily Checklist")
			return None
	
	def _create_pme_doc(self, employee_project, month_info, row):
		"""
		Create a new Project Monthly Effects document with initial data.
		"""
		try:
			pme_doc = frappe.get_doc({
				"doctype": "Project Monthly Effects",
				"employee_project": employee_project,
				"start_date": month_info["start_date"],
				"end_date": month_info["end_date"],
				"month": month_info["month_name"]
			})
			
			pme_doc.append("table_iogy", {
				"employee": row.employee,
				"total_overtime": float(row.overtime) if row.overtime else 0.0,
				"total_deduction": float(row.deduction) if row.deduction else 0.0
			})
			
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
				if table_row.employee == row.employee:
					# Make it cumulative - add to existing values
					table_row.total_overtime += float(row.overtime) if row.overtime else 0.0
					table_row.total_deduction += float(row.deduction) if row.deduction else 0.0
					return True
			
			# Employee not found, add new row
			pme_doc.append("table_iogy", {
				"employee": row.employee,
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
		"""
		try:
			rows_to_remove = []
			for idx, table_row in enumerate(pme_doc.table_iogy):
				if table_row.employee == row.employee:
					# Subtract values
					table_row.total_overtime -= float(row.overtime) if row.overtime else 0.0
					table_row.total_deduction -= float(row.deduction) if row.deduction else 0.0
					
					# Ensure values don't go below 0
					table_row.total_overtime = max(0.0, table_row.total_overtime)
					table_row.total_deduction = max(0.0, table_row.total_deduction)
					
					# If both values are 0, mark row for removal
					if table_row.total_overtime == 0.0 and table_row.total_deduction == 0.0:
						rows_to_remove.append(idx)
					
					return True
			
			# Remove rows with zero values (in reverse order to maintain indices)
			for idx in reversed(rows_to_remove):
				pme_doc.table_iogy.pop(idx)
			
			return False  # Employee not found
		except Exception as e:
			frappe.log_error(f"Error in _subtract_employee_values: {str(e)}", "Daily Checklist")
			raise e
	
	def _save_pme(self, pme_doc, month_info, employee_project, is_new=False, action_type="updated"):
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
				f"{month_info['year']} - Project: {employee_project}"
			)
			return True
		except Exception as e:
			frappe.log_error(f"Error saving Project Monthly Effects: {str(e)}", "Daily Checklist")
			frappe.msgprint(f"Warning: Could not save Project Monthly Effects record. Error: {str(e)}", alert=True)
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
		filters = {"status": "Active"}
		
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
