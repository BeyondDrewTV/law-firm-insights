import {
  PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";

import {
  clearCachedCsrfToken,
  checkBackendWiring,
  disableTwoFactor as apiDisableTwoFactor,
  enableTwoFactor as apiEnableTwoFactor,
  getAccountPlan,
  getCurrentUserWithRetry,
  login as apiLogin,
  logout as apiLogout,
  type CurrentPlan,
  type SessionTransientKind,
  type User,
  verifyTwoFactor as apiVerifyTwoFactor,
} from "@/api/authService";

interface AuthResult {
  success: boolean;
  user?: User | null;
  error?: string;
  requiresTwoFactor?: boolean;
  challengeId?: string;
  message?: string;
}

interface AuthContextValue {
  user: User | null;
  currentPlan: CurrentPlan | null;
  isLoggedIn: boolean;
  isLoading: boolean;
  logIn: (email: string, password: string) => Promise<AuthResult>;
  verifyTwoFactor: (challengeId: string, code: string) => Promise<AuthResult>;
  enableTwoFactor: (password: string) => Promise<AuthResult>;
  disableTwoFactor: (password: string) => Promise<AuthResult>;
  logOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshPlan: () => Promise<void>;
}

const defaultAuthContext: AuthContextValue = {
  user: null,
  currentPlan: null,
  isLoggedIn: false,
  isLoading: true,
  logIn: async () => ({ success: false, error: "Not initialized" }),
  verifyTwoFactor: async () => ({ success: false, error: "Not initialized" }),
  enableTwoFactor: async () => ({ success: false, error: "Not initialized" }),
  disableTwoFactor: async () => ({ success: false, error: "Not initialized" }),
  logOut: async () => undefined,
  refreshUser: async () => undefined,
  refreshPlan: async () => undefined,
};

const AuthContext = createContext<AuthContextValue>(defaultAuthContext);

export const AuthProvider = ({ children }: PropsWithChildren) => {
  const [user, setUser] = useState<User | null>(null);
  const [currentPlan, setCurrentPlan] = useState<CurrentPlan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const lastTransientToastAtRef = useRef(0);

  const refreshUser = useCallback(async () => {
    const notifyTransient = (kind: SessionTransientKind) => {
      const now = Date.now();
      if (now - lastTransientToastAtRef.current < 5000) return;
      lastTransientToastAtRef.current = now;

      if (kind === "rate_limited") {
        toast.message("Rate limited-retrying");
        return;
      }
      toast.message("Connection issue-retrying");
    };

    try {
      const currentUser = await getCurrentUserWithRetry({
        onTransientIssue: notifyTransient,
      });
      setUser(currentUser);
    } catch {
      // Preserve session state on transient failures.
    }
  }, []);

  const refreshPlan = useCallback(async () => {
    try {
      const planResult = await getAccountPlan();
      if (planResult.success && planResult.plan) {
        setCurrentPlan(planResult.plan);
      }
    } catch {
      // Preserve previous plan state on transient failures.
    }
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const wiring = await checkBackendWiring();
        if (
          import.meta.env.DEV &&
          !wiring.ok &&
          wiring.message &&
          window.sessionStorage.getItem("backend_wiring_warned") !== "1"
        ) {
          window.sessionStorage.setItem("backend_wiring_warned", "1");
          toast.error(wiring.message, { duration: 9000 });
        }
        await refreshUser();
      } finally {
        setIsLoading(false);
      }
    };

    void checkAuth();
  }, [refreshUser]);

  useEffect(() => {
    if (!user) {
      setCurrentPlan(null);
      return;
    }
    void refreshPlan();
  }, [user, refreshPlan]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      currentPlan,
      isLoggedIn: !!user,
      isLoading,
      refreshUser,
      refreshPlan,
      logIn: async (email: string, password: string) => {
        try {
          const result = await apiLogin({ email, password });
          if (result.success && result.requires_2fa && result.challenge_id) {
            return {
              success: true,
              requiresTwoFactor: true,
              challengeId: result.challenge_id,
              message: result.message,
            };
          }
          if (result.success && result.user) {
            clearCachedCsrfToken();
            setUser(result.user);
            await refreshPlan();
            return { success: true, user: result.user };
          }
          return { success: false, error: result.error || "Login failed" };
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Login failed";
          return { success: false, error: message };
        }
      },
      verifyTwoFactor: async (challengeId: string, code: string) => {
        const result = await apiVerifyTwoFactor(challengeId, code);
        if (result.success && result.user) {
          clearCachedCsrfToken();
          setUser(result.user);
          await refreshPlan();
          return { success: true, user: result.user };
        }
        return { success: false, error: result.error || "Verification failed." };
      },
      enableTwoFactor: async (password: string) => {
        const result = await apiEnableTwoFactor(password);
        if (!result.success) {
          return { success: false, error: result.error };
        }
        await refreshUser();
        await refreshPlan();
        return { success: true, message: "Two-factor authentication enabled." };
      },
      disableTwoFactor: async (password: string) => {
        const result = await apiDisableTwoFactor(password);
        if (!result.success) {
          return { success: false, error: result.error };
        }
        await refreshUser();
        await refreshPlan();
        return { success: true, message: "Two-factor authentication disabled." };
      },
      logOut: async () => {
        try {
          await apiLogout();
        } finally {
          clearCachedCsrfToken();
          setUser(null);
          setCurrentPlan(null);
        }
      },
    }),
    [user, currentPlan, isLoading, refreshUser, refreshPlan],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
