<template>
  <div class="hidden print:block w-full my-2 text-center font-medium text-3xl">Attendance Log</div>
  <div
    class="rounded-lg border overflow-auto break-before-avoid"
    :class="loading && 'animate-pulse pointer-events-none'"
  >
    <table class="border-separate border-spacing-0">
      <thead>
        <tr class="sticky top-0 bg-white z-10">
          <!-- Employee Search -->
          <th class="p-2 border-b">
            <Autocomplete
              class="print:hidden"
              :options="employeeSearchOptions"
              v-model="employeeSearch"
              placeholder="Search Employee"
              :multiple="true"
            />
          </th>

          <!-- Day/Date Row -->
          <th
            v-for="(day, idx) in daysOfMonth"
            :key="idx"
            class="font-medium border-b"
            :class="{ 'border-l': idx }"
          >
            {{ day.dayName }} {{ dayjs(day.date).format("DD") }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(employee, rowIdx) in employees" :key="employee.name">
          <!-- Employee Column -->
          <td
            v-if="
              !employeeSearch?.length ||
              employeeSearch?.some((item) => item.value === employee?.name)
            "
            class="px-2 py-7 z-[5]"
            :class="{ 'border-t': rowIdx }"
          >
            <div class="flex" :class="!employee.designation && 'items-center'">
              <Avatar
                class="print:hidden"
                :label="employee.employee_name"
                :image="employee.image"
                size="2xl"
              />
              <div class="flex flex-col ml-2 my-0.5 truncate">
                <div class="truncate text-base">
                  {{ employee.employee_name }}
                </div>
                <div class="mt-auto text-xs text-gray-500 truncate">
                  {{ employee.designation }}
                </div>
              </div>
            </div>
          </td>

          <!-- Events -->
          <td
            v-if="
              !employeeSearch?.length ||
              employeeSearch?.some((item) => item.value === employee?.name)
            "
            v-for="(day, colIdx) in daysOfMonth"
            :key="colIdx"
            class="p-1 align-middle text-xs print:max-w-6 print:min-w-6 max-w-32 min-w-32 text-[0.875rem];"
            :class="{
              'border-l': colIdx,
              'border-t': rowIdx,
              'align-top': events.data?.[employee.name]?.[day.date],
              'align-middle bg-blue-50':
                events.data?.[employee.name]?.[day.date]?.holiday,
              'align-middle bg-pink-50':
                events.data?.[employee.name]?.[day.date]?.leave,
              'bg-gray-50':
                dropCell.employee === employee.name &&
                dropCell.date === day.date &&
                !(
                  isHolidayOrLeave(employee.name, day.date) ||
                  hasSameShift(employee.name, day.date)
                ),
              'align-middle bg-red-200': isAbsent(employee.name, day.date),
              'align-middle bg-green-200': isPresent(employee.name, day.date),
              'align-middle bg-blue-200': isOnLeave(employee.name, day.date),
              'align-middle bg-orange-200': isHalfDay(employee.name, day.date),
              'align-middle bg-yellow-200': isWorkFromHome(
                employee.name,
                day.date
              ),
            }"
            @mouseenter="
              hoveredCell.employee = employee.name;
              hoveredCell.date = day.date;
            "
            @mouseleave="
              hoveredCell.employee = '';
              hoveredCell.date = '';
            "
            @dragover.prevent
            @dragenter="
              dropCell.employee = employee.name;
              dropCell.date = day.date;
            "
            @drop="
              () => {
                if (!isPresent(employee.name, day.date)) {
                  loading = true;
                }
              }
            "
          >
            <!-- Holiday -->
            <div
              v-if="events.data?.[employee.name]?.[day.date]?.holiday"
              class="blocked-cell text-xs"
            >
              <span class="print:hidden">
                {{
                  events.data[employee.name][day.date].weekly_off
                    ? "WO"
                    : events.data[employee.name][day.date].description
                }}
              </span>
			  <span class="print:block hidden font-bold">
                {{
                  events.data[employee.name][day.date].weekly_off
                    ? "X"
                    : events.data[employee.name][day.date].description
                }}
              </span>
            </div>

            <!-- Leave -->
            <div
              v-else-if="events.data?.[employee.name]?.[day.date]?.leave"
              class="blocked-cell"
            >
              {{ events.data[employee.name][day.date].leave_type }}
            </div>

            <div
              v-else-if="events?.data?.[employee.name]?.[day.date]?.[0]?.status"
              class="blocked-cell text-xs"
            >
              <span class="print:hidden">
                {{ events.data[employee.name][day.date][0].status }}
              </span>
              <span class="print:block hidden">
                {{ events.data[employee.name][day.date][0].status.charAt(0) }}
              </span>
            </div>
            <!-- Shifts -->
            <div
              v-else
              class="flex flex-col space-y-1 translate-x-0 translate-y-0"
            >
              <!-- Add Shift -->
              <Button
                variant="outline"
                icon="plus"
                class="border-2 active:bg-white w-full text-xs"
                :class="
                  hoveredCell.employee === employee.name &&
                  hoveredCell.date === day.date &&
                  !dropCell.employee
                    ? 'visible'
                    : 'invisible'
                "
                @click="
                  shiftAssignment = '';
                  showShiftAssignmentDialog = true;
                "
              />
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <NewAttendanceDialog
    v-model="showShiftAssignmentDialog"
    :isDialogOpen="showShiftAssignmentDialog"
    :shiftAssignmentName="shiftAssignment"
    :selectedCell="{ employee: hoveredCell.employee, date: hoveredCell.date }"
    :employees="employees"
    :shift_types="shift_types"
    @fetchEvents="
      events.fetch();
      showShiftAssignmentDialog = false;
    "
  />
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import colors from "tailwindcss/colors";
import { Avatar, Autocomplete, createResource } from "frappe-ui";
import { Dayjs } from "dayjs";

import { dayjs, raiseToast } from "../utils";
import { EmployeeFilters } from "../views/MonthView.vue";
import ShiftAssignmentDialog from "./NewAttendanceDialog.vue";
import NewAttendanceDialog from "./NewAttendanceDialog.vue";

interface Holiday {
  holiday: string;
  description: string;
  weekly_off: 0 | 1;
}

interface HolidayWithDate extends Holiday {
  holiday_date: string;
}

interface Leave {
  leave: string;
  leave_type: string;
}

interface LeaveApplication extends Leave {
  from_date: string;
  to_date: string;
}

type Color =
  | "blue"
  | "cyan"
  | "fuchsia"
  | "green"
  | "lime"
  | "orange"
  | "pink"
  | "red"
  | "violet"
  | "yellow";

type Attendance = {
  [K in "name" | "status" | "start_time" | "end_time"]: string;
} & {
  color?: Color;
};

interface ShiftAssignment extends Attendance {
  attendance_date: string;
}

type Events = Record<
  string,
  (HolidayWithDate | LeaveApplication | ShiftAssignment)[]
>;
type MappedEvents = Record<
  string,
  Record<string, Holiday | Leave | Attendance[]>
>;

const props = defineProps<{
  firstOfMonth: Dayjs;
  employees: {
    [K in "name" | "employee_name" | "designation" | "image"]: string;
  }[];
  employeeFilters: { [K in keyof EmployeeFilters]?: string };
  shift_types: { [K in "name"]: string }[];
  shiftTypeFilter: string;
}>();

const loading = ref(true);
const employeeSearch = ref<{ value: string; label: string }[]>();
const shiftAssignment = ref<string>();
const showShiftAssignmentDialog = ref(false);
const hoveredCell = ref({
  employee: "",
  date: "",
  shift: "",
  shift_type: "",
  shift_status: "",
});
const dropCell = ref({ employee: "", date: "", shift: "" });

const daysOfMonth = computed(() => {
  const daysOfMonth = [];
  for (let i = 1; i <= props.firstOfMonth.daysInMonth(); i++) {
    const date = props.firstOfMonth.date(i);
    daysOfMonth.push({
      dayName: date.format("ddd"),
      date: date.format("YYYY-MM-DD"),
    });
  }
  return daysOfMonth;
});

const employeeSearchOptions = computed(() => {
  return props.employees.map(
    (employee: { name: string; employee_name: string }) => ({
      value: employee.name,
      label: `${employee.name}: ${employee.employee_name}`,
    })
  );
});

watch(
  () => [props.firstOfMonth, props.employeeFilters, props.shiftTypeFilter],
  () => {
    loading.value = true;
    events.fetch();
  },
  { deep: true }
);

watch(loading, (val) => {
  if (!val) dropCell.value = { employee: "", date: "", shift: "" };
});

const isHolidayOrLeave = (employee: string, day: string) =>
  events.data?.[employee]?.[day]?.holiday ||
  events.data?.[employee]?.[day]?.leave;

const hasSameShift = (employee: string, day: string) =>
  Array.isArray(events.data?.[employee]?.[day]) &&
  events.data?.[employee]?.[day].some(
    (shift: Attendance) => shift.status === hoveredCell.value.shift_status
  );

const isPresent = (employee: string, day: string) => {
  if (events.data?.[employee]?.[day]?.length) {
    return events.data?.[employee]?.[day]?.[0].status === "Present";
  }
};

const isAbsent = (employee: string, day: string) => {
  if (events.data?.[employee]?.[day]?.length) {
    return events.data?.[employee]?.[day]?.[0].status === "Absent";
  }
};

const isOnLeave = (employee: string, day: string) => {
  if (events.data?.[employee]?.[day]?.length) {
    return events.data?.[employee]?.[day]?.[0].status === "On Leave";
  }
};

const isHalfDay = (employee: string, day: string) => {
  if (events.data?.[employee]?.[day]?.length) {
    return events.data?.[employee]?.[day]?.[0].status === "Half Day";
  }
};

const isWorkFromHome = (employee: string, day: string) => {
  if (events.data?.[employee]?.[day]?.length) {
    return events.data?.[employee]?.[day]?.[0].status === "Work From Home";
  }
};

// RESOURCES

const events = createResource({
  url: "optima_hr.api.attendance_log.get_events",
  auto: true,
  makeParams() {
    return {
      month_start: props.firstOfMonth.format("YYYY-MM-DD"),
      month_end: props.firstOfMonth.endOf("month").format("YYYY-MM-DD"),
      employee_filters: props.employeeFilters,
    };
  },
  onSuccess() {
    loading.value = false;
  },
  onError(error: { message: string }) {
    raiseToast("error", error.message);
  },
  transform: (data: Events) => {
    const mappedEvents: MappedEvents = {};
    for (const employee in data) {
      mapEventsToDates(data, mappedEvents, employee);
    }
    return mappedEvents;
  },
});
defineExpose({ events });

const mapEventsToDates = (
  data: Events,
  mappedEvents: MappedEvents,
  employee: string
) => {
  mappedEvents[employee] = {};
  for (let d = 1; d <= props.firstOfMonth.daysInMonth(); d++) {
    const date = props.firstOfMonth.date(d);
    const key = date.format("YYYY-MM-DD");

    for (const event of Object.values(data[employee])) {
      let result: Holiday | Leave | undefined;
      if ("holiday" in event) {
        result = handleHoliday(event, date);
        if (result) {
          mappedEvents[employee][key] = result;
          break;
        }
      } else if ("leave" in event) {
        result = handleLeave(event, date);
        if (result) {
          mappedEvents[employee][key] = result;
          break;
        }
      } else handleAttendance(event, date, mappedEvents, employee, key);
    }
    sortShiftsByStartTime(mappedEvents, employee, key);
  }
};
const handleAttendance = (
  event: ShiftAssignment,
  date: Dayjs,
  mappedEvents: MappedEvents,
  employee: string,
  key: string
) => {
  if (
    dayjs(event.attendance_date).isSameOrBefore(date) &&
    (dayjs(event.attendance_date).isSameOrAfter(date) || !event.attendance_date)
  ) {
    if (!Array.isArray(mappedEvents[employee][key]))
      mappedEvents[employee][key] = [];
    mappedEvents[employee][key].push({
      name: event.name,
      status: event.status,
      start_time: event.attendance_date.split(":").slice(0, 2).join(":"),
      end_time: event.attendance_date.split(":").slice(0, 2).join(":"),
    });
  }
};

const handleHoliday = (event: HolidayWithDate, date: Dayjs) => {
  if (date.isSame(event.holiday_date)) {
    return {
      holiday: event.holiday,
      description: event.description,
      weekly_off: event.weekly_off,
    };
  }
};

const handleLeave = (event: LeaveApplication, date: Dayjs) => {
  if (
    dayjs(event.from_date).isSameOrBefore(date) &&
    dayjs(event.to_date).isSameOrAfter(date)
  )
    return {
      leave: event.leave,
      leave_type: event.leave_type,
    };
};

const sortShiftsByStartTime = (
  mappedEvents: MappedEvents,
  employee: string,
  key: string
) => {
  if (Array.isArray(mappedEvents[employee][key]))
    mappedEvents[employee][key].sort((a: Attendance, b: Attendance) =>
      a.start_time.localeCompare(b.start_time)
    );
};
</script>

<style>
th:first-child,
td:first-child {
  @apply sticky left-0 print:max-w-28 print:min-w-28 max-w-64 min-w-64 bg-white border-r;
}

.blocked-cell {
  @apply text-sm text-gray-500 text-center p-2;
}

@media print {
  table {
    width: 100%;
    page-break-inside: avoid;
  }

  th,
  td {
    font-size: 10px; /* Adjust as necessary */
    padding: 4px; /* Further reduce padding for print */
  }
  .border-separate {
    border-collapse: collapse; /* Change to collapse for a cleaner print */
  }
  /* Hide elements that should not be printed */
  .print\:hidden {
    display: none !important;
  }
}
</style>
