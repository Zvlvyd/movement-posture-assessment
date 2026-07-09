import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import { useAuthStore } from './stores/auth'
import 'vfonts/Lato.css'
import './styles/global.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const themeStore = useThemeStore()
themeStore.initTheme()

const authStore = useAuthStore()
if (authStore.token) {
  authStore.fetchUser().catch(() => {})
}

app.use(router)
app.mount('#app')
