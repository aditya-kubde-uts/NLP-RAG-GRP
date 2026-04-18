import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/common/ProtectedRoute";
import DashboardLayout from "@/components/layout/DashboardLayout";
import LoginPage from "@/pages/auth/LoginPage";
import SignupPage from "@/pages/auth/SignupPage";
import BusinessAdminDashboard from "@/pages/business-admin/BusinessAdminDashboard";
import ChatPortal from "@/pages/chat/ChatPortal";
import HomePage from "@/pages/HomePage";
import CreateBusinessPage from "@/pages/super-admin/CreateBusinessPage";
import DashboardPage from "@/pages/super-admin/DashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute requireSuperAdmin>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="businesses/new" element={<CreateBusinessPage />} />
      </Route>
      <Route
        path="/b/:slug/admin"
        element={
          <ProtectedRoute requireBusinessAdminSlug>
            <BusinessAdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/b/:slug" element={<ChatPortal />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
