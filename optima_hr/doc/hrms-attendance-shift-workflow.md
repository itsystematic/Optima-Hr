# HRMS Attendance System - Shift, Checkin & Attendance Workflow

## Table of Contents

1. [Entity Overview](#entity-overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Attendance Marking Workflow](#attendance-marking-workflow)
4. [Key Control Fields](#key-control-fields)
5. [Overlapping Shift Detection](#overlapping-shift-detection)
6. [Date Range Logic (Processing Window)](#date-range-logic-processing-window)
7. [Absent Marking Logic](#absent-marking-logic)
8. [Auto Update Mechanism](#auto-update-mechanism)
9. [Critical Filters That Skip Checkins](#critical-filters-that-skip-checkins)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## Entity Overview

### 1. Employee Checkin (`tabEmployee Checkin`)
Physical clock-in/clock-out log from biometric devices or manual entry.

| Field | Description |
|-------|-------------|
| `employee` | FK to Employee |
| `time` | Actual clock time |
| `log_type` | IN or OUT |
| `shift` | FK to Shift Type (auto-assigned on save) |
| `shift_start` | Calculated shift start datetime |
| `shift_end` | Calculated shift end datetime |
| `shift_actual_start` | shift_start - early checkin buffer |
| `shift_actual_end` | shift_end + late checkout buffer |
| `attendance` | FK to Attendance (set when processed) |
| `skip_auto_attendance` | If 1, excluded from auto processing |
| `offshift` | If 1, checkin is outside any shift window |

**Source**: `hrms/hr/doctype/employee_checkin/employee_checkin.py`

### 2. Shift Type (`tabShift Type`)
Defines shift hours and auto-attendance configuration.

| Field | Description |
|-------|-------------|
| `start_time` | Shift start (e.g., 09:00) |
| `end_time` | Shift end (e.g., 17:30) |
| `begin_check_in_before_shift_start_time` | Buffer minutes before shift |
| `allow_check_out_after_shift_end_time` | Buffer minutes after shift |
| `enable_auto_attendance` | Master toggle for auto-attendance |
| `process_attendance_after` | Start date of processing window |
| `last_sync_of_checkin` | End datetime of processing window |
| `auto_update_last_sync` | Auto-advance last_sync daily |

**Source**: `hrms/hr/doctype/shift_type/shift_type.py`

### 3. Shift Assignment (`tabShift Assignment`)
Links an employee to a shift type for a date range.

| Field | Description |
|-------|-------------|
| `employee` | FK to Employee |
| `shift_type` | FK to Shift Type |
| `start_date` | Assignment starts |
| `end_date` | Assignment ends (NULL = open-ended) |
| `status` | Active / Inactive |

**Source**: `hrms/hr/doctype/shift_assignment/shift_assignment.py`

### 4. Attendance (`tabAttendance`)
Final attendance record for an employee on a date.

| Field | Description |
|-------|-------------|
| `employee` | FK to Employee |
| `attendance_date` | The date |
| `shift` | FK to Shift Type (optional) |
| `status` | Present / Absent / Half Day / On Leave / Work From Home |
| `working_hours` | Calculated from checkin logs |
| `late_entry` | Boolean flag |
| `early_exit` | Boolean flag |

**Source**: `hrms/hr/doctype/attendance/attendance.py`

---

## Entity Relationship Diagram

```
+------------------+          +-------------------+
|    Employee      |          |    Shift Type     |
|------------------|          |-------------------|
| name (ID)        |          | name (ID)         |
| employee_name    |          | start_time        |
| date_of_joining  |          | end_time          |
| relieving_date   |          | early_buffer (min) |
+--------+---------+          | late_buffer (min)  |
         |                    | enable_auto_attend |
         |                    | process_attend_after|
         |  1                 | last_sync_of_checkin|
         |                    | auto_update_last_sync|
         +--------+          +--------+-----------+
                  |                    |
          +-------+------+    +-------+------+
          |              |    |              |
          v              v    v              |
+-------------------+  +-------------------+ |
| Shift Assignment  |  | Employee Checkin  | |
|-------------------|  |-------------------| |
| employee      FK  |  | employee      FK  | |
| shift_type    FK -+->| shift         FK -+-+
| start_date        |  | time              |
| end_date          |  | log_type (IN/OUT) |
| status            |  | shift_start       |
+-------------------+  | shift_end         |
                       | shift_actual_start |
                       | shift_actual_end   |
                       | attendance     FK -+--+
                       | skip_auto_attend   |  |
                       +-------------------+   |
                                               |
                       +-------------------+   |
                       |   Attendance      |<--+
                       |-------------------|
                       | employee      FK  |
                       | attendance_date   |
                       | shift         FK  |
                       | status            |
                       | working_hours     |
                       | late_entry        |
                       | early_exit        |
                       +-------------------+
```

**Relationships Summary:**
- **Employee** 1 --- N **Shift Assignment** (employee can have many assignments over time)
- **Shift Type** 1 --- N **Shift Assignment** (a shift type can be assigned to many employees)
- **Employee** 1 --- N **Employee Checkin** (employee can have many checkins)
- **Shift Type** 1 --- N **Employee Checkin** (checkin is assigned to one shift)
- **Attendance** 1 --- N **Employee Checkin** (one attendance record links to multiple checkins for that shift)
- **Employee** 1 --- N **Attendance** (one attendance per employee per date)

---

## Attendance Marking Workflow

```
                    +---------------------------------+
                    | TRIGGER: One of these happens   |
                    |---------------------------------|
                    | A) Manual: "Mark Attendance"    |
                    |    button on Shift Type form    |
                    | B) Auto: Cron job runs          |
                    |    process_auto_attendance      |
                    +--------------+------------------+
                                   |
                                   v
                    +-----------------------------+
                    | 1. Validate Shift Config    |
                    |    has_incorrect_shift_config|
                    +-----------------------------+
                    | Checks:                     |
                    | - enable_auto_attendance=1  |
                    | - process_attendance_after   |
                    |   is set                    |
                    | - last_sync_of_checkin      |
                    |   is set                    |
                    +-------------+---------------+
                                  |
                                  v
                    +-----------------------------+
                    | 2. Fetch Employee Checkins  |
                    |    get_employee_checkins()   |
                    |    shift_type.py:181         |
                    +-----------------------------+
                    | Filters:                    |
                    | - skip_auto_attendance = 0  |
                    | - attendance IS NOT SET     |
                    | - time >= process_attend_   |
                    |   after                     |
                    | - shift_actual_end <        |
                    |   last_sync_of_checkin      |
                    | - shift = this shift type   |
                    | - offshift = 0              |
                    +-------------+---------------+
                                  |
                                  v
                    +-----------------------------+
                    | 3. Group Checkins           |
                    |    By (employee, shift_start)|
                    +-----------------------------+
                    | Each group = one shift      |
                    | occurrence for one employee |
                    | Contains IN and OUT logs    |
                    +-------------+---------------+
                                  |
                                  v
              +-------------------+-------------------+
              |                                       |
              v                                       v
+-----------------------------+     +-----------------------------+
| 4a. For each group:        |     | 4b. Mark Absent for dates   |
|     get_attendance()        |     |     with no attendance      |
|     shift_type.py:207       |     |     shift_type.py:246       |
+-----------------------------+     +-----------------------------+
| - Calculate working hours   |     | - Get date range from       |
| - Determine status:         |     |   process_attendance_after  |
|   Present / Half Day /      |     |   to last_sync_of_checkin   |
|   Absent                    |     | - For each employee with    |
| - Detect late_entry,        |     |   active shift assignment:  |
|   early_exit                |     |   Check if attendance       |
| - Get IN time, OUT time     |     |   exists for each working   |
+-------------+---------------+     |   day. If not, create       |
              |                     |   Absent attendance         |
              v                     +-------------+---------------+
+-----------------------------+                   |
| 5. mark_attendance_and_     |                   v
|    link_log()               |     +-----------------------------+
|    employee_checkin.py:197  |     | Same as step 5 but with    |
+-----------------------------+     | status = "Absent"          |
| - Create Attendance record  |     +-----------------------------+
| - Link all checkin logs     |
|   to this attendance        |
| - Handle overlapping shift  |
|   errors (skip + warn)      |
+-----------------------------+
              |
              v
+-----------------------------+
| 6. Commit & Update          |
+-----------------------------+
| - frappe.db.commit()        |
| - Show results/warnings     |
|   to user                   |
+-----------------------------+
```

---

## Key Control Fields

### The Processing Window

The two most critical fields on Shift Type control which checkins get processed:

```
Timeline:
==========================================================================
|<-- process_attendance_after          last_sync_of_checkin -->|
|         (Date)                           (Datetime)         |
|                                                             |
|  [=====  PROCESSING WINDOW  =====]                         |
|                                                             |
|  Checkins in this window          Checkins here are         |
|  ARE processed                    IGNORED until             |
|                                   last_sync advances        |
==========================================================================

Filter Logic (shift_type.py:196-203):
  - checkin.time >= process_attendance_after       (start boundary)
  - checkin.shift_actual_end < last_sync_of_checkin (end boundary)
```

**Example with shift "الرئيسى ( مكة )":**
- Shift: 09:00 - 17:30
- Early buffer: 60 min -> actual_start = 08:00
- Late buffer: 60 min -> actual_end = 18:30
- `last_sync_of_checkin` = 2026-02-08 17:02:53

```
Feb 7 checkin: shift_actual_end = 2026-02-07 18:30:00
              18:30 < Feb 8 17:02:53 ? YES -> PROCESSED

Feb 8 checkin: shift_actual_end = 2026-02-08 18:30:00
              18:30 < Feb 8 17:02:53 ? NO  -> SKIPPED!

Feb 9+ checkins: all SKIPPED (same reason)
```

---

## Overlapping Shift Detection

When creating an Attendance record with a shift, the system checks for overlaps:

```
                 +------------------------------+
                 | Creating Attendance for      |
                 | Employee X, Date D, Shift A  |
                 +-------------+----------------+
                               |
                               v
                 +------------------------------+
                 | Query: Any existing Attendance|
                 | for Employee X, Date D,      |
                 | Shift != A, docstatus < 2 ?  |
                 +-------------+----------------+
                               |
                    +----------+----------+
                    |                     |
                    v                     v
               No results            Found records
               -> Proceed            -> Check timing overlap
                                          |
                                          v
                              +------------------------+
                              | has_overlapping_timings|
                              | (shift_assignment.py)  |
                              +------------------------+
                              | Shift A: 09:00 - 17:30 |
                              | Shift B: 09:00 - 17:00 |
                              |                        |
                              | Overlap = A.end > B.start|
                              |    AND  A.start < B.end |
                              | 17:30 > 09:00? YES     |
                              | 09:00 < 17:00? YES     |
                              | -> OVERLAP DETECTED     |
                              +----------+-------------+
                                         |
                                         v
                              +------------------------+
                              | OverlappingShift       |
                              | AttendanceError raised |
                              | -> Attendance NOT      |
                              |    created             |
                              | -> Warning shown       |
                              +------------------------+
```

**Midnight shift handling:** If `end_time <= start_time`, the system adds 1 day to `end_time` before comparing.

---

## Date Range Logic (Processing Window)

### For Checkin Processing (`get_employee_checkins`)

```python
# shift_type.py:196-203
filters = {
    "time": (">=", self.process_attendance_after),         # START
    "shift_actual_end": ("<", self.last_sync_of_checkin),  # END (strict <)
}
```

### For Absent Marking (`get_start_and_end_dates`)

```
start_date = MAX(process_attendance_after, employee.date_of_joining)
end_date   = MIN(shift_before_last_sync - 1 day, employee.relieving_date)
```

```
shift_type.py:290-322

Timeline for absent marking:
==========================================================================
  process_attendance_after    last_sync - 1 day    last_sync_of_checkin
         |                          |                      |
         |   [== ABSENT WINDOW ==]  |                      |
         |                          |                      |
         |   Working days with no   |   Not marked absent  |
         |   attendance -> Absent   |   (too recent)       |
==========================================================================
```

---

## Auto Update Mechanism

### `update_last_sync_of_checkin()` (shift_type.py:405-424)

Called by scheduler hooks to auto-advance the processing window:

```
Conditions to update:
  1. enable_auto_attendance = 1
  2. auto_update_last_sync = 1   <-- MUST BE ENABLED
  3. Current time > shift_actual_end of today's shift
  4. last_sync_of_checkin < shift_actual_end

New value = shift_actual_end + 1 minute

Example:
  Shift actual_end = 18:30
  Current time = 19:00 (shift has ended)
  Old last_sync = 2026-02-08 18:31:00
  New last_sync = 2026-02-09 18:31:00  (next day's shift end + 1 min)
```

```
Day 1: last_sync = Day 0 18:31 -> processes Day 0 checkins
Day 2: last_sync auto-updates to Day 1 18:31 -> processes Day 1 checkins
Day 3: last_sync auto-updates to Day 2 18:31 -> processes Day 2 checkins
...and so on
```

**If `auto_update_last_sync = 0`, you must manually update `last_sync_of_checkin` to process newer checkins.**

---

## Critical Filters That Skip Checkins

A checkin will be **SKIPPED** (not processed into attendance) if ANY of these are true:

| # | Filter | Field | Condition |
|---|--------|-------|-----------|
| 1 | Already processed | `attendance` | IS SET (already linked) |
| 2 | Manually excluded | `skip_auto_attendance` | = 1 |
| 3 | Too old | `time` | < `process_attendance_after` |
| 4 | **Too new** | **`shift_actual_end`** | **>= `last_sync_of_checkin`** |
| 5 | Wrong shift | `shift` | != current Shift Type name |
| 6 | Off-shift | `offshift` | = 1 |
| 7 | Auto-attendance off | Shift Type `enable_auto_attendance` | = 0 |

**Filter #4 is the most common cause of "missing" attendance records.**

---

## Troubleshooting Guide

### Problem: Attendance stops at a certain date

**Symptom**: Checkins exist beyond date X, but attendance only goes up to date X.

**Diagnosis**:
1. Open the Shift Type document
2. Check `last_sync_of_checkin` value
3. Calculate `shift_actual_end` = `end_time` + `allow_check_out_after_shift_end_time`
4. If `shift_actual_end` >= `last_sync_of_checkin` for checkins on date X+1, that's the problem

**Fix**:
1. Update `last_sync_of_checkin` to a datetime **after** the latest `shift_actual_end` you want to process (e.g., today's date + 19:00:00)
2. Enable `auto_update_last_sync` checkbox to prevent this from happening again
3. Click "Mark Attendance" button

### Problem: Overlapping Shift Attendance error

**Symptom**: "Attendance for employee X is already marked for an overlapping shift Y: ATT-xxxx"

**Diagnosis**:
1. Check the referenced attendance record (ATT-xxxx)
2. Verify if it belongs to a shift with overlapping hours
3. Check if the employee's shift assignment dates are correct

**Fix options**:
- Cancel the erroneous attendance record if it was created under wrong shift
- Correct the shift assignment date ranges to not overlap
- If both shifts are legitimate, check HR Settings > `allow_multiple_shift_assignments`

### Problem: Checkins show old dates in terminal

**Symptom**: Terminal prints checkin data from months/years ago.

**Diagnosis**: The query fetches ALL unprocessed checkins from `process_attendance_after` onwards. If old checkins never got attendance linked, they keep showing up.

**Fix**: Either process the old checkins or set `skip_auto_attendance = 1` on them.

---

## Key Source File References

| File | Key Functions | Lines |
|------|--------------|-------|
| `hrms/hr/doctype/shift_type/shift_type.py` | `process_auto_attendance()` | ~110 |
| | `_process()` | ~137 |
| | `get_employee_checkins()` | ~181 |
| | `get_attendance()` | ~207 |
| | `mark_absent_for_dates_with_no_attendance()` | ~246 |
| | `get_start_and_end_dates()` | ~290 |
| | `update_last_sync_of_checkin()` | ~405 |
| `hrms/hr/doctype/employee_checkin/employee_checkin.py` | `mark_attendance_and_link_log()` | ~197 |
| | `calculate_working_hours()` | ~292 |
| `hrms/hr/doctype/attendance/attendance.py` | `get_overlapping_shift_attendance()` | ~127 |
| `hrms/hr/doctype/shift_assignment/shift_assignment.py` | `has_overlapping_timings()` | ~150 |
| | `get_employee_shift()` | ~406 |

---

*Document created: 2026-02-18*
*Based on HRMS app at: `/home/erpnext/fawaz_py311/apps/hrms/hrms/`*
