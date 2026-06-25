import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import MainLayout from "./components/MainLayout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import FMSScreeningPage from "./pages/FMSScreeningPage";
import FMSReportPage from "./pages/FMSReportPage";
import AssessmentPage from "./pages/AssessmentPage";
import AssessmentReportPage from "./pages/AssessmentReportPage";
import TrainingPage from "./pages/TrainingPage";
import LearningPage from "./pages/LearningPage";
import CheckinPage from "./pages/CheckinPage";
import ProfilePage from "./pages/ProfilePage";
import CoachPage from "./pages/CoachPage";
import AdminPage from "./pages/AdminPage";

function PrivateRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user, token } = useAuthStore();
  if (!token || !user) return <Navigate to="/login" />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/home" />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
        <Route index element={<Navigate to="/home" />} />
        <Route path="home" element={<HomePage />} />
        <Route path="fms" element={<FMSScreeningPage />} />
        <Route path="fms/report/:id" element={<FMSReportPage />} />
        <Route path="assessment" element={<AssessmentPage />} />
        <Route path="assessment/report/:id" element={<AssessmentReportPage />} />
        <Route path="training" element={<TrainingPage />} />
        <Route path="learning" element={<LearningPage />} />
        <Route path="checkin" element={<CheckinPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="coach" element={<PrivateRoute roles={["coach", "admin"]}><CoachPage /></PrivateRoute>} />
        <Route path="admin" element={<PrivateRoute roles={["admin"]}><AdminPage /></PrivateRoute>} />
      </Route>
    </Routes>
  );
}
