import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { darkTheme, lightTheme, type GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#2563eb',
    primaryColorPressed: '#1d4ed8',
    primaryColorSuppl: '#3b82f6',
    borderRadius: '8px',
    borderRadiusSmall: '6px'
  },
  Layout: {
    headerColor: 'rgba(255, 255, 255, 0.85)',
    siderColor: 'rgba(255, 255, 255, 0.95)',
    headerColorDark: 'rgba(16, 24, 40, 0.85)',
    siderColorDark: 'rgba(16, 24, 40, 0.95)'
  },
  Card: {
    borderRadius: '12px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
  },
  Button: {
    borderRadiusMedium: '8px'
  },
  Input: {
    borderRadius: '8px'
  },
  Menu: {
    borderRadius: '8px'
  }
}

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(false)

  const theme = computed(() => (isDark.value ? darkTheme : lightTheme))

  function initTheme() {
    const saved = localStorage.getItem('theme')
    if (saved) {
      isDark.value = saved === 'dark'
    } else {
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
  }

  function toggleTheme() {
    isDark.value = !isDark.value
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  }

  return {
    isDark,
    theme,
    themeOverrides,
    initTheme,
    toggleTheme
  }
})
