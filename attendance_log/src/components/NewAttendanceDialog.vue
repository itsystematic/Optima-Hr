<template>
  <Dialog
    :dir="lang === 'ar' ? 'rtl' : 'ltr'"
    :options="{ title: dialog.title, size: '4xl' }"
  >
    <template #body-content>
      <div
        class="grid grid-cols-2 gap-6"
        :class="lang === 'en' ? 'text-left' : 'text-right'"
      >
        <FormControl
          type="autocomplete"
          :label="__('Employee')"
          v-model="form.employee"
          :disabled="!!props.shiftAssignmentName"
          :options="employees"
        />
        <FormControl
          type="text"
          :label="__('Company')"
          v-model="form.company"
          :disabled="true"
        />
        <FormControl
          type="text"
          :label="__('Employee Name')"
          v-model="form.employee_name"
          :disabled="true"
        />
        <div class="space-y-2 text-xs">
          <label for="date">{{__('Attendance Date')}}</label>
          <DatePicker
            id="date"
            class="text-center"
            v-model="form.attendance_date"
            disabled
          />
        </div>
        <FormControl
          type="autocomplete"
          :label="__('Attendance Status')"
          v-model="form.status"
          :disabled="!!props.shiftAssignmentName"
          :options="[
            'Present',
            'Absent',
            'On Leave',
            'Half Day',
            'Work From Home',
          ]"
        />
        <FormControl
          type="autocomplete"
          :label="__('Shift Type')"
          v-model="form.shift_type"
          :disabled="!!props.shiftAssignmentName"
          :options="shift_types"
        />
      </div>

      <!-- Schedule Settings -->
      <div
        v-if="!props.shiftAssignmentName && showShiftScheduleSettings"
        class="mt-6 space-y-6"
      >
        <hr />
        <h4 class="font-semibold">Schedule Settings</h4>
        <div class="grid grid-cols-2 gap-6">
          <div class="space-y-1.5">
            <div class="text-xs text-gray-600">Repeat On Days</div>
            <div
              class="border rounded grid grid-flow-col h-7 justify-stretch overflow-clip"
            >
              <div
                v-for="(isSelected, day) of repeatOnDays"
                class="cursor-pointer flex flex-col"
                :class="{
                  'border-r': day !== 'Sunday',
                  'bg-gray-100 text-gray-500': !isSelected,
                  'pointer-events-none': !!props.shiftAssignmentName,
                }"
                @click="repeatOnDays[day] = !repeatOnDays[day]"
              >
                <div class="text-center text-sm my-auto">
                  {{ day.substring(0, 3) }}
                </div>
              </div>
            </div>
          </div>
          <FormControl
            type="select"
            :options="[
              'Every Week',
              'Every 2 Weeks',
              'Every 3 Weeks',
              'Every 4 Weeks',
            ]"
            label="Frequency"
            v-model="frequency"
            :disabled="!!props.shiftAssignmentName"
          />
        </div>
      </div>

      <Dialog
        v-model="showDeleteDialog"
        :options="{
          title: deleteDialogOptions.title,
          actions: [
            {
              label: 'Confirm',
              variant: 'solid',
              onClick: deleteDialogOptions.action,
            },
          ],
        }"
      >
        <template #body-content>
          <div v-html="deleteDialogOptions.message" />
        </template>
      </Dialog>
    </template>
    <template #actions>
      <div class="flex space-x-3 justify-end">
        <Dropdown v-if="props.shiftAssignmentName" :options="actions">
          <Button size="md" label="Delete" class="w-28 text-red-600" />
        </Dropdown>
        <Button
          size="md"
          variant="solid"
          :disabled="dialog.actionDisabled"
          class="w-28"
          @click="dialog.action"
        >
          {{ dialog.button }}
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { reactive, ref, computed, watch } from "vue";
import {
  DatePicker,
  Dialog,
  FormControl,
  Dropdown,
  createDocumentResource,
  createResource,
  createListResource,
} from "frappe-ui";

import { dayjs, raiseToast } from "../utils";

type Status = "Present" | "Absent" | "On Leave" | "Half Day" | "Work From Home";

type Form = {
  [K in
    | "company"
    | "employee_name"
    | "employee"
    | "attendance_date"
    | "shift_type"]: string | { value: string; label?: string };
} & {
  status: Status | string | { value: Status; label?: Status };
  // schedule?: string;
};

interface Props {
  isDialogOpen: boolean;
  shiftAssignmentName?: string;
  selectedCell?: {
    employee: string;
    date: string;
  };
  employees?: {
    name: string;
    employee_name: string;
  }[];
  shift_types?: {
    name: string;
  }[];
}

const props = withDefaults(defineProps<Props>(), {
  employees: () => [],
  shift_types: () => [],
});

const lang = frappe.boot.lang;

const emit = defineEmits<{
  (e: "fetchEvents"): void;
}>();

const formObject: Form = {
  employee: "",
  company: "",
  employee_name: "",
  attendance_date: "",
  status: "",
  shift_type: "",
};

const repeatOnDaysObject = {
  Monday: false,
  Tuesday: false,
  Wednesday: false,
  Thursday: false,
  Friday: false,
  Saturday: false,
  Sunday: false,
};

const form = reactive({ ...formObject });
const repeatOnDays = reactive({ ...repeatOnDaysObject });

const shiftAssignment = ref();
const selectedDate = ref();
const frequency = ref("Every Week");
const showDeleteDialog = ref(false);
const deleteDialogOptions = ref({ title: "", message: "", action: () => {} });

const dialog = computed(() => {
  if (props.shiftAssignmentName)
    return {
      title: `[${selectedDate.value}] Attendance ${props.shiftAssignmentName}`,
      button: "Update",
      action: updateShiftAssigment,
      actionDisabled: form.status === shiftAssignment.value?.doc?.status,
    };
  return {
    title: lang === "ar" ? "إضافة حضور" : "New Attendance",
    button: lang === "ar" ? "إضافة" : "Submit",
    action: createAttendance,
    actionDisabled: false,
  };
});

const actions = computed(() => {
  const options = [
    {
      label: `Shift for ${selectedDate.value}`,
      onClick: () => {
        deleteDialogOptions.value = {
          title: "Delete Shift?",
          message: `This will remove the Attendance: <a href='/app/shift-assignment/${props.shiftAssignmentName}' target='_blank'><u>${props.shiftAssignmentName}</u></a> scheduled for <b>${selectedDate.value}</b>.`,
          action: () => deleteCurrentShift.submit(),
        };
        showDeleteDialog.value = true;
      },
    },
    {
      label: "All Consecutive Shifts",
      onClick: () => {
        deleteDialogOptions.value = {
          title: "Delete Shift Assignment?",
          message: `This will delete Shift Assignment: <a href='/app/shift-assignment/${
            props.shiftAssignmentName
          }' target='_blank'><u>${
            props.shiftAssignmentName
          }</u></a> (scheduled from <b>${form.start_date}</b>${
            form.end_date ? ` to <b>${form.end_date}</b>` : ""
          }).`,
          action: async () => {
            await shiftAssignment.value.setValue.submit({ docstatus: 2 });
            shiftAssignments.delete.submit(props.shiftAssignmentName);
          },
        };
        showDeleteDialog.value = true;
      },
    },
  ];
  if (form.schedule)
    options.push({
      label: "Shift Assignment Schedule",
      onClick: () => {
        deleteDialogOptions.value = {
          title: "Delete Shift Assignment Schedule?",
          message: `This will delete Shift Assignment Schedule: <a href='/app/shift-assignment-schedule/${form.schedule}' target='_blank'><u>${form.schedule}</u></a> and all the shifts associated with it.`,
          action: () => deleteShiftAssignmentSchedule.submit(),
        };
        showDeleteDialog.value = true;
      },
    });
  return options;
});

const showShiftScheduleSettings = computed(() => {
  if (
    !form.start_date ||
    dayjs(form.end_date).diff(dayjs(form.start_date), "d") < 7
  ) {
    frequency.value = "Every Week";
    return false;
  }
  return true;
});

const employees = computed(() => {
  return props.employees.map((employee) => ({
    label: `${employee.name}: ${employee.employee_name}`,
    value: employee.name,
    employee_name: employee.employee_name,
  }));
});

const shift_types = computed(() => {
  return props.shift_types.map((type) => ({
    value: type.name,
    label: type.name,
  }));
});

watch(
  () => props.isDialogOpen,
  (val) => {
    if (!val) return;

    showDeleteDialog.value = false;

    if (props.shiftAssignmentName) {
      shiftAssignment.value = getShiftAssignment(props.shiftAssignmentName);
      if (props.selectedCell) selectedDate.value = props.selectedCell.date;
    } else {
      Object.assign(form, formObject);
      if (!props.selectedCell) return;
      form.employee = { value: props.selectedCell.employee };
      form.attendance_date = props.selectedCell.date;
      form.status = "Present";
    }
  }
);

watch(
  () => form.employee,
  (val) => {
    if (props.shiftAssignmentName) return;
    if (val) {
      employee.fetch();
    } else {
      form.employee_name = "";
      form.company = "";
    }
  }
);

watch(
  () => form.attendance_date,
  () => {
    Object.assign(repeatOnDays, repeatOnDaysObject);
    if (!form.attendance_date) return;
    const day = dayjs(form.attendance_date).format("dddd");
    repeatOnDays[day as keyof typeof repeatOnDays] = true;
  },
  { immediate: true }
);

const updateShiftAssigment = () => {
  shiftAssignment.value.setValue.submit({
    status: form.status,
    end_date: form.end_date,
  });
};

// const createShiftAssigment = () => {
// 	if (
// 		showShiftScheduleSettings.value &&
// 		(Object.values(repeatOnDays).some((day) => !day) || frequency.value !== "Every Week")
// 	)
// createShiftAssignmentSchedule.submit();
// 	else insertShift.submit();
// };

const createAttendance = () => {
  createNewAttendace.submit();
};

// RESOURCES

const getShiftAssignment = (name: string) =>
  createDocumentResource({
    doctype: "Shift Assignment",
    name: name,
    onSuccess: (data: Record<string, any>) => {
      Object.keys(form).forEach((key) => {
        form[key as keyof Form] = data[key];
      });
      // if (form.schedule) getShiftAssignmentSchedule(form.schedule);
    },
    onError(error: { messages: string[] }) {
      raiseToast("error", error.messages[0]);
    },
    setValue: {
      onSuccess() {
        raiseToast("success", "Shift Assignment updated successfully!");
        emit("fetchEvents");
      },
      onError(error: { messages: string[] }) {
        raiseToast("error", error.messages[0]);
      },
    },
  });

const getShiftAssignmentSchedule = (name: string) =>
  createDocumentResource({
    doctype: "Shift Assignment Schedule",
    name: name,
    onSuccess: (data: Record<string, any>) => {
      frequency.value = data.frequency;
      const days = data.repeat_on_days.map(
        (day: { day: keyof typeof repeatOnDays }) => day.day
      );
      for (const day in repeatOnDays) {
        repeatOnDays[day as keyof typeof repeatOnDays] = days.includes(day);
      }
    },
    onError(error: { messages: string[] }) {
      raiseToast("error", error.messages[0]);
    },
  });

const employee = createResource({
  url: "hrms.api.roster.get_values",
  makeParams() {
    const employee = (form.employee as { value: string }).value;
    return {
      doctype: "Employee",
      name: employee,
      fields: ["employee_name", "company", "department", "default_shift"],
    };
  },
  onSuccess: (data: {
    [K in "employee_name" | "company" | "department" | "default_shift"]: string;
  }) => {
    form.employee_name = data.employee_name;
    form.company = data.company;
    form.shift_type = data.default_shift;
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});

const shiftAssignments = createListResource({
  doctype: "Shift Assignment",
  insert: {
    onSuccess() {
      raiseToast("success", "Shift Assignment created successfully!");
      emit("fetchEvents");
    },
    onError(error: { messages: string[] }) {
      raiseToast("error", error.messages[0]);
    },
  },
  delete: {
    onSuccess() {
      raiseToast("success", "Shift Assignment deleted successfully!");
      emit("fetchEvents");
    },
    onError(error: { messages: string[] }) {
      raiseToast("error", error.messages[0]);
    },
  },
});

const insertShift = createResource({
  url: "hrms.api.roster.insert_shift",
  makeParams() {
    return {
      employee: (form.employee as { value: string }).value,
      shift_type: (form.shift_type as { value: string }).value,
      company: form.company,
      status: form.status,
      start_date: form.start_date,
      end_date: form.end_date,
    };
  },
  onSuccess: () => {
    raiseToast("success", "Shift Assignment created successfully!");
    emit("fetchEvents");
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});

const deleteCurrentShift = createResource({
  url: "hrms.api.roster.break_shift",
  makeParams() {
    return {
      assignment: props.shiftAssignmentName,
      date: selectedDate.value,
    };
  },
  onSuccess: () => {
    raiseToast("success", "Shift deleted successfully!");
    emit("fetchEvents");
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});

const createNewAttendace = createResource({
  url: "optima_hr.api.attendance_log.create_attendance",
  makeParams() {
    return {
      employee: (form.employee as { value: string }).value,
      company: form.company,
      attendance_date: form.attendance_date,
      shift_type:
        (form.shift_type as { value: string }).value || form.shift_type,
      status: (form.status as { value: string }).value || form.status,
    };
  },
  onSuccess: () => {
    raiseToast("success", "Attendance created successfully!");
    emit("fetchEvents");
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});

// const createShiftAssignmentSchedule = createResource({
// 	url: "hrms.api.roster.create_shift_assignment_schedule",
// 	makeParams() {
// 		return {
// 			employee: (form.employee as { value: string }).value,
// 			shift_type: (form.shift_type as { value: string }).value,
// 			company: form.company,
// 			status: form.status,
// 			start_date: form.start_date,
// 			end_date: form.end_date,
// 			repeat_on_days: Object.keys(repeatOnDays).filter(
// 				(day) => repeatOnDays[day as keyof typeof repeatOnDays],
// 			),
// 			frequency: frequency.value,
// 		};
// 	},
// 	onSuccess: () => {
// 		raiseToast("success", "Shift Assignment Schedule created successfully!");
// 		emit("fetchEvents");
// 	},
// 	onError(error: { messages: string[] }) {
// 		raiseToast("error", error.messages[0]);
// 	},
// });
const createAttendanceSchedule = createResource({
  url: "optima_payment.api.attendance_log.create_attendance",
  makeParams() {
    return {
      employee: (form.employee as { value: string }).value,
      company: form.company,
      status: form.status,
      attendance_date: form.attendance_date,
      repeat_on_days: Object.keys(repeatOnDays).filter(
        (day) => repeatOnDays[day as keyof typeof repeatOnDays]
      ),
    };
  },
  onSuccess: () => {
    raiseToast("success", "Shift Assignment Schedule created successfully!");
    emit("fetchEvents");
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});

const deleteShiftAssignmentSchedule = createResource({
  url: "hrms.api.roster.delete_shift_assignment_schedule",
  makeParams() {
    return { schedule: form.schedule };
  },
  onSuccess: () => {
    raiseToast("success", "Shift Assignment Schedule deleted successfully!");
    emit("fetchEvents");
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});
</script>
