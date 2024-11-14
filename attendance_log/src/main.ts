import "./index.css";

import { createApp } from "vue";
import router from "./router";
import App from "./App.vue";

import { Button, setConfig, frappeRequest, resourcesPlugin } from "frappe-ui";
import { translationsPlugin } from "./plugins/translationsPlugin"

const app = createApp(App);

setConfig("resourceFetcher", frappeRequest);

app.use(router);
app.use(resourcesPlugin);
app.use(translationsPlugin)
app.component("Button", Button);



router.isReady().then(async () => {
    try {
        console.log('Updating CSRF TOKEN');
        //@ts-ignore
        const base_url = window.api_url ?? window.location.origin;
        const response = await fetch(
            `${base_url}/api/method/optima_hr.api.attendance_log.clear_cache_and_get_csrf_token`
        );
        const jsonResponse = await response.json();
        //@ts-ignore
        window.csrf_token = jsonResponse.message.csrf_token;

        if (import.meta.env.DEV) {
            console.log('Development');
            const devContext = await frappeRequest({
                url: '/api/method/optima_hr.api.get_context_for_dev',
            })
            // @ts-ignore
            if (!window.frappe) window.frappe = {}
            //@ts-ignore
            window.frappe.boot = devContext;
        }
        else {
            console.log('Prodcution');
        }
        await translationsPlugin.isReady();
    }
    catch (err: any) {
        throw new Error(err.message);
    }
    finally {
        app.mount('#app');
        console.log('All done.');
    }
})