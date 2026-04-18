import { createContext } from "react";

import type { AuthContextValue } from "./auth-types";

export const AuthStateContext = createContext<AuthContextValue | null>(null);
