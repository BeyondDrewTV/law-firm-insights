import { describe, it, expect } from "vitest";
import {
  getRequiredAuthenticatedDestination,
  getPostLoginDestination,
} from "./authRedirect";

const unverifiedUser = { email_verified: false, onboarding_complete: false };
const verifiedIncomplete = { email_verified: true, onboarding_complete: false };
const verifiedComplete = { email_verified: true, onboarding_complete: true };

describe("getRequiredAuthenticatedDestination", () => {
  it("routes unverified user to /check-email", () => {
    expect(getRequiredAuthenticatedDestination(unverifiedUser)).toBe("/check-email");
  });
  it("routes null user to /check-email", () => {
    expect(getRequiredAuthenticatedDestination(null)).toBe("/check-email");
  });
  it("routes verified + onboarding incomplete to /onboarding", () => {
    expect(getRequiredAuthenticatedDestination(verifiedIncomplete)).toBe("/onboarding");
  });
  it("routes verified + onboarding complete to /dashboard", () => {
    expect(getRequiredAuthenticatedDestination(verifiedComplete)).toBe("/dashboard");
  });
});

describe("getPostLoginDestination", () => {
  it("unverified goes to /check-email regardless of requestedPath", () => {
    expect(getPostLoginDestination(unverifiedUser, "/dashboard")).toBe("/check-email");
  });
  it("verified + incomplete goes to /onboarding regardless of requestedPath", () => {
    expect(getPostLoginDestination(verifiedIncomplete, "/dashboard")).toBe("/onboarding");
  });
  it("verified + complete uses requestedPath when valid", () => {
    expect(getPostLoginDestination(verifiedComplete, "/dashboard/signals")).toBe("/dashboard/signals");
  });
  it("verified + complete falls back to /dashboard when requestedPath is null or empty", () => {
    expect(getPostLoginDestination(verifiedComplete, null)).toBe("/dashboard");
    expect(getPostLoginDestination(verifiedComplete, "")).toBe("/dashboard");
  });
  it("verified + complete ignores external URL as requestedPath", () => {
    expect(getPostLoginDestination(verifiedComplete, "https://evil.example.com")).toBe("/dashboard");
  });
});
