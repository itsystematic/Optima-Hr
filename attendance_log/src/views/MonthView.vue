<template>
  <div class="px-12 py-6 space-y-6">
    <div class="flex items-center">
      <FeatherIcon name="calendar" class="h-7 w-7 text-gray-500 mr-3" />
      <span class="font-semibold text-2xl mr-1">{{ __("Month View") }}</span>
      <Button
        :class="lang === 'ar' ? 'mr-auto' : 'ml-auto'"
        class="px-4"
        :variant="'solid'"
        :ref_for="true"
        theme="gray"
        size="md"
        label="Button"
        :loading="false"
        :loadingText="null"
        :disabled="false"
        :link="null"
        :onclick="handlePrint"
      >
        {{__("Print")}}
      </Button>
      <!-- <Dropdown
        :options="[
          {
            label: __('New Attendace'),
            onClick: () => {
              showShiftAssignmentDialog = true;
            },
          },
          {
            label: __('Print'),
            onClick: () => {
              handlePrint();
            },
          },
        ]"
        :button="{
          label: __('Create'),
          variant: 'solid',
          iconRight: 'chevron-down',
          size: 'md',
        }"
        :class="lang === 'ar' ? 'mr-auto' : 'ml-auto'"
      /> -->
    </div>
    <div ref="print" :dir="lang === 'ar' ? 'rtl' : 'ltr'" class="bg-white rounded-lg border p-4">
      <MonthViewHeader
        :lang="lang"
        :firstOfMonth="firstOfMonth"
        @updateFilters="updateFilters"
        @addToMonth="addToMonth"
      />
      <MonthViewTable
        :lang="lang"
        ref="monthViewTable"
        :firstOfMonth="firstOfMonth"
        :shift_types="shift_types.data || []"
        :employees="employees.data || []"
        :employeeFilters="employeeFilters"
        :shiftTypeFilter="shiftTypeFilter"
      />
    </div>
  </div>
  <ShiftAssignmentDialog
    :shift_types="shift_types.data"
    v-model="showShiftAssignmentDialog"
    :isDialogOpen="showShiftAssignmentDialog"
    :employees="employees.data"
    @fetchEvents="
      monthViewTable?.events.fetch();
      showShiftAssignmentDialog = false;
    "
  />
</template>

<script setup lang="ts">
import { ref, reactive, render, h } from "vue";
import { Dropdown, FeatherIcon, createListResource, Button } from "frappe-ui";
import { useVueToPrint } from "vue-to-print";
import { dayjs, raiseToast } from "../utils";
import MonthViewTable from "../components/MonthViewTable.vue";
import MonthViewHeader from "../components/MonthViewHeader.vue";
import ShiftAssignmentDialog from "../components/NewAttendanceDialog.vue";

export type EmployeeFilters = {
  [K in
    | "status"
    | "company"
    | "department"
    | "branch"
    | "designation"]?: string;
};

const monthViewTable = ref<InstanceType<typeof MonthViewTable>>();
const showShiftAssignmentDialog = ref(false);
const firstOfMonth = ref(dayjs().date(1).startOf("D"));
const shiftTypeFilter = ref("");
const employeeFilters = reactive<EmployeeFilters>({
  status: "Active",
});
const print = ref();
const addToMonth = (change: number) => {
  firstOfMonth.value = firstOfMonth.value.add(change, "M");
};

const lang = frappe.boot.lang;

const { handlePrint } = useVueToPrint({
  content: print,
});

// const handlePrintClick = () => {
//   // Create a container element to render the Vue component
//   const el = document.createElement("div");
//   const props = {
//     firstOfMonth: firstOfMonth.value,
//     shift_types: shift_types.data || [],
//     employees: employees.data || [],
//     employeeFilters: employeeFilters,
//     shiftTypeFilter: shiftTypeFilter,
//   };
//   render(h(PrintFormat, props), el); // Render the component into the element
//   // Open a new window for printing
//   const printWindow = window.open("", "_blank");

//   if (!printWindow) {
//     console.error("Failed to open print window.");
//     return;
//   }

//   // Write the HTML content into the new window
//   printWindow.document.write(`
//     <html>
//       <head>
//         <title>Print</title>
//         <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
//         <style>
//           .text-base {
//             font-size: 12px;
//           }
//           .rounded-full {
//           display: none;
//           }
//           th, td {
//           min-width: 1rem;
//           font-size: 0.875rem;
//           }
//           /* Optional: Add styles for your print content */
//           body {
//             font-family: Arial, sans-serif;
//             margin: 10px;
//           }
//         </style>
//       </head>
//       <body>
//       ${el.innerHTML}
//       </body>
//     </html>
//   `);

//   printWindow.document.close();
//   // Wait for the new window to load before printing
//   printWindow.onload = () => {
//     const contentReady = printWindow.document.body.children;
//     if (!contentReady) return;
//     printWindow.print(); // Trigger the print dialog
//     // printWindow.close();
//     // setTimeout(() => {
//     //   printWindow.close();
//     // }, 5000);
//   };
// };

const updateFilters = (
  newFilters: EmployeeFilters & { shift_type: string }
) => {
  let employeeUpdated = false;
  (
    Object.entries(newFilters) as [
      keyof EmployeeFilters | "shift_type",
      string,
    ][]
  ).forEach(([key, value]) => {
    if (key === "shift_type") {
      shiftTypeFilter.value = value;
      return;
    }

    if (value) employeeFilters[key] = value;
    else delete employeeFilters[key];
    employeeUpdated = true;
  });
  if (employeeUpdated) employees.fetch();
};

// RESOURCES

const employees = createListResource({
  doctype: "Employee",
  fields: ["name", "employee_name", "designation", "image"],
  filters: employeeFilters,
  auto: true,
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});

const shift_types = createListResource({
  doctype: "Shift Type",
  fields: ["name"],
  auto: true,
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});
</script>
