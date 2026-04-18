import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "@/context/auth-provider";
import { Toaster } from "sonner";

import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Toaster richColors position="bottom-right" theme="dark" />
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
