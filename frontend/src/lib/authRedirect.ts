import type { User } from "@/api/authService";

type RedirectableUser = Pick<User, "email_verified" | "onboarding_complete"> | null | undefined;

export const isUserVerified = (user: RedirectableUser): boolean => user?.email_verified === true;

export const isUserOnboardingComplete = (user: RedirectableUser): boolean =>
  user?.onboarding_complete === true;

export const getRequiredAuthenticatedDestination = (user: RedirectableUser): "/check-email" | "/onboarding" | "/dashboard" => {
  if (!isUserVerified(user)) {
    return "/check-email";
  }
  return isUserOnboardingComplete(user) ? "/dashboard" : "/onboarding";
};

export const getPostLoginDestination = (
  user: RedirectableUser,
  requestedPath?: string | null,
): string => {
  const requiredDestination = getRequiredAuthenticatedDestination(user);
  if (requiredDestination !== "/dashboard") {
    return requiredDestination;
  }
  return requestedPath && requestedPath.startsWith("/") ? requestedPath : "/dashboard";
};
