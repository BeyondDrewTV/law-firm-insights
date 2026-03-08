import { ReactNode, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { getRequiredAuthenticatedDestination, isUserOnboardingComplete } from "@/lib/authRedirect";

interface ProtectedRouteProps {
  children: ReactNode;
  requireFirmContext?: boolean;
}

const ProtectedRoute = ({ children, requireFirmContext = true }: ProtectedRouteProps) => {
  const { isLoading, isLoggedIn, user, logOut } = useAuth();
  const location = useLocation();
  const [isForcingLogout, setIsForcingLogout] = useState(false);

  useEffect(() => {
    if (isLoading || !isLoggedIn) return;
    if (!user?.firm_membership_disabled) return;
    if (isForcingLogout) return;
    setIsForcingLogout(true);
    void logOut();
  }, [isForcingLogout, isLoading, isLoggedIn, logOut, user?.firm_membership_disabled]);

  if (isLoading || isForcingLogout) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-6">
        <p className="text-muted-foreground">
          {isForcingLogout ? "Ending stale session..." : "Checking your session..."}
        </p>
      </div>
    );
  }

  if (!isLoggedIn || user?.firm_membership_disabled) {
    return <Navigate to="/login" replace state={{ from: location.pathname, reason: "session_expired" }} />;
  }

  const requiredDestination = getRequiredAuthenticatedDestination(user);
  if (requiredDestination === "/check-email") {
    return <Navigate to="/check-email" replace />;
  }

  if (requireFirmContext && !isUserOnboardingComplete(user)) {
    return <Navigate to="/onboarding" replace />;
  }

  if (!requireFirmContext && isUserOnboardingComplete(user)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
