<template>
  <div :dir="lang === 'ar' ? 'rtl' : 'ltr'" v-if="user.data" class="bg-gray-50 min-h-screen">
    <NavBar :user="user.data" />
    <MonthView />
    <Toasts />
  </div>
</template>

<script setup lang="ts">
import { Toasts, createResource } from "frappe-ui";

import NavBar from "../components/NavBar.vue";
import MonthView from "./MonthView.vue";
import { onBeforeMount } from "vue";

export type User = {
  [K in "name" | "first_name" | "full_name" | "user_image"]: string;
} & {
  roles: string[];
};

//@ts-ignore
const lang = window.frappe.boot.lang;

const user = createResource({
  url: "optima_hr.api.get_current_user_info",
  auto: true,
  onError() {
    window.location.href = "/login?redirect-to=%2Fattendance_log";
  },
});
</script>
<style>
*{
  font-family: "Almarai", serif;
}
</style>