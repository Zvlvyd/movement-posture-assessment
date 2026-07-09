import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: () => {
        const role = useAuthStore().user?.role
        return role === 'admin' ? '/admin' : role === 'coach' ? '/coach' : '/home'
      } },
      {
        path: 'home',
        name: 'Home',
        component: () => import('../views/HomeView.vue'),
        meta: { title: '首页', icon: 'home' }
      },
      {
        path: 'assessment',
        name: 'Assessment',
        component: () => import('../views/AssessmentView.vue'),
        meta: { title: '体态评估', icon: 'body', roles: ['trainee', 'admin'] }
      },
      {
        path: 'assessment/compare/:id?',
        name: 'AssessmentCompare',
        component: () => import('../views/AssessmentCompareView.vue'),
        meta: { title: '评估对比分析', icon: 'analytics', roles: ['trainee', 'coach', 'admin'] }
      },
      {
        path: 'assessment/report/:id',
        name: 'AssessmentReport',
        component: () => import('../views/AssessmentReportView.vue'),
        meta: { title: '评估报告', icon: 'body', roles: ['trainee', 'coach', 'admin'] }
      },
      {
        path: 'fms',
        name: 'FMS',
        component: () => import('../views/FMSScreeningView.vue'),
        meta: { title: 'FMS筛查', icon: 'analytics', roles: ['trainee'] }
      },
      {
        path: 'fms/report/:id',
        name: 'FMSReport',
        component: () => import('../views/FMSReportView.vue'),
        meta: { title: 'FMS报告', icon: 'analytics', roles: ['trainee'] }
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('../views/TrainingView.vue'),
        meta: { title: '计划训练', icon: 'book', roles: ['trainee'] }
      },
      {
        path: 'training/report/:id',
        name: 'TrainingReport',
        component: () => import('../views/TrainingReportView.vue'),
        meta: { title: '学习报告', icon: 'book', roles: ['trainee'] }
      },
      {
        path: 'learning',
        name: 'Learning',
        component: () => import('../views/LearningView.vue'),
        meta: { title: '标准动作学习', icon: 'school', roles: ['trainee', 'coach', 'admin'] }
      },
      {
        path: 'prescription-training',
        name: 'PrescriptionTraining',
        component: () => import('../views/PrescriptionTrainingView.vue'),
        meta: { title: 'AI处方', icon: 'list', roles: ['trainee'] }
      },
      {
        path: 'prescription',
        name: 'PrescriptionLegacy',
        component: () => import('../views/PrescriptionTrainingView.vue'),
        meta: { title: 'AI处方', icon: 'list', roles: ['trainee'] }
      },
      {
        path: 'prescription-training/report/:id',
        name: 'PrescriptionTrainingReport',
        component: () => import('../views/PrescriptionTrainingReportView.vue'),
        meta: { title: 'AI处方报告', icon: 'list', roles: ['trainee'] }
      },
      {
        path: 'prescription-training/plan/:id',
        name: 'PrescriptionPlanDetail',
        component: () => import('../views/PrescriptionPlanDetailView.vue'),
        meta: { title: '训练计划详情', icon: 'list', roles: ['trainee'] }
      },
      {
        path: 'checkin',
        name: 'Checkin',
        component: () => import('../views/CheckinView.vue'),
        meta: { title: '每日打卡', icon: 'checkmark-circle', roles: ['trainee'] }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/ProfileView.vue'),
        meta: { title: '个人中心', icon: 'person' }
      },
      {
        path: 'report/fms',
        name: 'FMSReportCenter',
        component: () => import('../views/reports/FMSReportCenterView.vue'),
        meta: { title: 'FMS 评估报告', roles: ['trainee'] }
      },
      {
        path: 'report/posture',
        name: 'PostureReportCenter',
        component: () => import('../views/reports/PostureReportCenterView.vue'),
        meta: { title: '体态评估报告', roles: ['trainee'] }
      },
      {
        path: 'report/action',
        name: 'ActionReportCenter',
        component: () => import('../views/reports/ActionReportCenterView.vue'),
        meta: { title: '动作训练报告', roles: ['trainee'] }
      },
      {
        path: 'coach',
        name: 'Coach',
        component: () => import('../views/CoachView.vue'),
        meta: { title: '教练工作台', icon: 'people', roles: ['coach', 'admin'] }
      },
      {
        path: 'coach/student/:id',
        name: 'CoachStudentDetail',
        component: () => import('../views/CoachStudentDetailView.vue'),
        meta: { title: '学员详情', icon: 'people', roles: ['coach', 'admin'] }
      },
      {
        path: 'coach/class/:id',
        name: 'CoachClassDetail',
        component: () => import('../views/CoachClassDetailView.vue'),
        meta: { title: '班级详情', icon: 'people', roles: ['coach', 'admin'] }
      },
      {
        path: 'my-classes',
        name: 'MyClasses',
        component: () => import('../views/MyClassesView.vue'),
        meta: { title: '我的班级', icon: 'people', roles: ['trainee'] }
      },
      {
        path: 'messages',
        name: 'Messages',
        component: () => import('../views/MessagesView.vue'),
        meta: { title: '消息中心', icon: 'chatbubbles', roles: ['trainee', 'coach', 'admin'] }
      },
      {
        path: 'coach/actions',
        name: 'CoachActions',
        component: () => import('../views/CoachActionsView.vue'),
        meta: { title: '动作库管理', icon: 'fitness', roles: ['coach', 'admin'] }
      },
      {
        path: 'coach/plan-review',
        name: 'CoachPlanReview',
        component: () => import('../views/CoachPlanReviewView.vue'),
        meta: { title: '计划审批', icon: 'clipboard', roles: ['coach', 'admin'] }
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('../views/AdminView.vue'),
        meta: { title: '系统管理', icon: 'settings', roles: ['admin'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && authStore.isLoggedIn) {
    next(authStore.user?.role === 'admin' ? '/admin' : authStore.user?.role === 'coach' ? '/coach' : '/home')
  } else {
    const roles = to.meta.roles as string[] | undefined
    if (roles && authStore.user && !roles.includes(authStore.user.role)) {
      next('/home')
    } else {
      next()
    }
  }
})

export default router
