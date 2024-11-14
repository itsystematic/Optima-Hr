<template>
  <div class="h-12 bg-white border-b px-12 flex items-center">
    <a class="text-xl" href="/">{{ __("Home") }}</a>
    <Dropdown
	:class="lang === 'ar' ? 'mr-auto' : 'ml-auto'"
      :options="[
        {
          label: __('My Account'),
          onClick: () => goTo('/me'),
        },
        {
          label: __('Log Out'),
          onClick: () => logout.submit(),
        },
        {
          label: __('Switch to Desk'),
          onClick: () => goTo('/app'),
        },
      ]"
    >
      <Avatar
        :label="props.user?.full_name"
        :image="props.user?.user_image"
        size="lg"
        class="cursor-pointer"
      />
    </Dropdown>
  </div>
</template>

<script setup lang="ts">
import { Dropdown, Avatar, createResource } from "frappe-ui";
import router from "../router";

import User from "../views/Home.vue";

const props = defineProps<{
  user: User;
}>();


const lang = window?.frappe?.boot.lang ?? 'ar'

const goTo = (path: string) => {
  window.location.href = path;
};

// RESOURCES

const logout = createResource({
  url: "logout",
  onSuccess() {
    goTo("/login");
  },
  onError(error: { messages: string[] }) {
    raiseToast("error", error.messages[0]);
  },
});
</script>
