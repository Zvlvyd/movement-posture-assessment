import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spin } from "antd";
import { useAuthStore } from "./store/auth";
import { roleToPath } from "./hooks/useRoleNavigate";
import ErrorBoundary from "./components/ErrorBoundary";
import MainLayout from "./components/MainLayout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import FMSScreeningPage from "./pages/FMSScreeningPage";
import FMSReportPage from "./pages/FMSReportPage";
import AssessmentPage from "./pages/AssessmentPage";
import AssessmentReportPage from "./pages/AssessmentReportPage";
import LearningPage from "./pages/LearningPage";
import CheckinPage from "./pages/CheckinPage";
import ProfilePage from "./pages/ProfilePage";
import CoachPage from "./pages/CoachPage";
import StudentDetailPage from "./pages/StudentDetailPage";
import AdminPage from "./pages/AdminPage";
import ActionLibraryPage from "./pages/coach/ActionLibraryPage";
import PrescriptionPage from "./pages/PrescriptionPage";
import PrescriptionTrainingPage from "./pages/PrescriptionTrainingPage";
import MyClassesPage from "./pages/MyClassesPage";
import MessagesPage from "./pages/MessagesPage";
import PlanReviewPage from "./pages/coach/PlanReviewPage";

function AppLoading() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Spin size="large" tip="加载中..." />
    </div>
  );
}

function PrivateRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const token = useAuthStore(s => s.token);
  const user = useAuthStore(s => s.user);
  const fetchUser = useAuthStore(s => s.fetchUser);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    // On mount, if we have a token but no user, try to fetch the user profile
    if (token && !user) {
      fetchUser().finally(() => setInitializing(false));
    } else {
      setInitializing(false);
    }
  }, []); // Run only on mount

  if (initializing && token && !user) {
    return <AppLoading />;
  }

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/home" replace />;
  }
  return <>{children}</>;
}

function RoleIndexRedirect() {
  const user = useAuthStore(s => s.user);
  return <Navigate to={roleToPath(user?.role)} replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
          <Route index element={<RoleIndexRedirect />} />
          <Route path="home" element={<HomePage />} />
          <Route path="fms" element={<FMSScreeningPage />} />
          <Route path="fms/report/:id" element={<FMSReportPage />} />
          <Route path="assessment" element={<AssessmentPage />} />
          <Route path="assessment/report/:id" element={<AssessmentReportPage />} />
          <Route path="learning" element={<LearningPage />} />
          <Route path="checkin" element={<CheckinPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="my-classes" element={<MyClassesPage />} />
          <Route path="messages" element={<MessagesPage />} />
          <Route path="coach" element={<PrivateRoute roles={["coach", "admin"]}><CoachPage /></PrivateRoute>} />
          <Route path="coach/student/:studentId" element={<PrivateRoute roles={["coach", "admin"]}><StudentDetailPage /></PrivateRoute>} />
          <Route path="coach/actions" element={<PrivateRoute roles={["coach", "admin"]}><ActionLibraryPage /></PrivateRoute>} />
          <Route path="coach/plan-review" element={<PrivateRoute roles={["coach", "admin"]}><PlanReviewPage /></PrivateRoute>} />
          <Route path="admin" element={<PrivateRoute roles={["admin"]}><AdminPage /></PrivateRoute>} />
          <Route path="prescription" element={<PrescriptionPage />} />
          <Route path="training" element={<PrescriptionTrainingPage />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}
