import { useContext } from "react";

import { AuthStateContext } from "./auth-state-context";
import type { AuthContextValue } from "./auth-types";

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthStateContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
