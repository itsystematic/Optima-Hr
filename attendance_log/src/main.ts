import "./index.css";

import { createApp } from "vue";
import router from "./router";
import App from "./App.vue";

import { Button, setConfig, frappeRequest, resourcesPlugin } from "frappe-ui";
// import { __ } from "./utils/translation";
import { translationsPlugin } from "./plugins/translationsPlugin"

const app = createApp(App);

setConfig("resourceFetcher", frappeRequest);

app.use(router);
app.use(resourcesPlugin);
app.use(translationsPlugin)
app.component("Button", Button);

router.isReady().then(async () => {
    if (import.meta.env.DEV) {
        await frappeRequest({
            url: "/api/method/optima_hr.api.get_context_for_dev",
        }).then(async (values) => 
        {
            if (!window.frappe) window.frappe = {}
            window.frappe.boot = values
        })
    }

    await translationsPlugin.isReady();
    app.mount("#app");
})

