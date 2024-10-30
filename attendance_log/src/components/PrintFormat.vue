<template>
  <div>
    <h1>Month View</h1>
    <MonthViewTable
      ref="monthViewTable"
      :firstOfMonth="props.firstOfMonth"
      :shift_types="props.shift_types || []"
      :employees="props.employees || []"
      :employeeFilters="props.employeeFilters"
      :shiftTypeFilter="props.shiftTypeFilter"
      :isPrint="true"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, render, h } from "vue";

import { dayjs } from "../utils";
import MonthViewTable from "./MonthViewTable.vue";
import { Dayjs } from "dayjs";

export type EmployeeFilters = {
  [K in
    | "status"
    | "company"
    | "department"
    | "branch"
    | "designation"]?: string;
};

const monthViewTable = ref<InstanceType<typeof MonthViewTable>>();

// RESOURCES
const props = defineProps<{
  firstOfMonth: Dayjs;
  employees: {
    [K in "name" | "employee_name" | "designation" | "image"]: string;
  }[];
  shift_types: { [K in "name"]: string }[];
  employeeFilters: { [K in keyof EmployeeFilters]?: string };
  shiftTypeFilter: string;
  isPrint?: boolean;
}>();
</script>
