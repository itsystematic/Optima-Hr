<template>
  <div v-if="user.data" class="bg-gray-50 min-h-screen">
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

// RESOURCES
onBeforeMount(async () => {
  try {
    console.log("Updating CSRF Token....");
    const base_url = window.api_url;
    const response = await fetch(
      `${base_url}/api/method/optima_hr.api.attendance_log.clear_cache_and_get_csrf_token`
    );
    const reformatted_response = await response.json();
    if (response.ok) {
      window.csrf_token = reformatted_response.message.csrf_token;
      console.log("CSRF Token Updated");
    } else {
      console.error("Failed to update CSRF Token");
    }

    console.log("Getting User Settings....");
  } catch (err) {
    console.log(err);
  }
});
const user = createResource({
  url: "hrms.api.get_current_user_info",
  auto: true,
  onError() {
    window.location.href = "/login?redirect-to=%2Fattendance_log";
  },
});
</script>
