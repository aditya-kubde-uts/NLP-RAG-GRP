import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/common/ProtectedRoute";
import LoginPage from "@/pages/auth/LoginPage";
import SignupPage from "@/pages/auth/SignupPage";
import BusinessAdminDashboard from "@/pages/business-admin/BusinessAdminDashboard";
import ChatPortal from "@/pages/chat/ChatPortal";
import HomePage from "@/pages/HomePage";
import SuperAdminDashboard from "@/pages/super-admin/SuperAdminDashboard";

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
            <SuperAdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/b/:slug/admin"
        element={
          <ProtectedRoute>
            <BusinessAdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/b/:slug" element={<ChatPortal />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
