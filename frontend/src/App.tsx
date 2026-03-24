import { useEffect, useState } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation, useNavigate, type Location } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import RouteErrorBoundary from "@/components/RouteErrorBoundary";
import UpgradeModal from "@/components/UpgradeModal";
import { PLAN_LIMIT_EVENT } from "@/api/authService";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/contexts/AuthContext";
import { getRequiredAuthenticatedDestination } from "@/lib/authRedirect";

/** Renders children only if the current user has is_admin === true. Otherwise redirects to /dashboard. */
const AdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user?.is_admin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
};

import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
import Contact from "./pages/Contact";
import Signup from "./pages/Signup";
import VerifyEmail from "./pages/VerifyEmail";
import VerifyComplete from "./pages/VerifyComplete";
import VerifySuccess from "./pages/VerifySuccess";
import CheckEmail from "./pages/CheckEmail";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Onboarding from "./pages/Onboarding";
import Pricing from "./pages/Pricing";
import ReportDetail from "./pages/ReportDetail";
import DashboardBilling from "./pages/DashboardBilling";
import DashboardSecurity from "./pages/DashboardSecurity";
import DashboardAccount from "./pages/DashboardAccount";
import DashboardPdfPreview from "./pages/DashboardPdfPreview";
import ExecutionPage from "./pages/ExecutionPage";
import SignalDetail from "./pages/SignalDetail";
import ReportsPage from "./pages/ReportsPage";
import SignalsPage from "./pages/SignalsPage";
import Features from "./pages/Features";
import HowItWorks from "./pages/HowItWorks";
import Docs from "./pages/Docs";
import Security from "./pages/Security";
import DemoWorkspace from "./pages/DemoWorkspace";
import DemoReportDetail from "./pages/DemoReportDetail";
import DemoPdfPreview from "./pages/DemoPdfPreview";
import DashboardTeam from "./pages/DashboardTeam";
import InviteAccept from "./pages/InviteAccept";
import ActionDetail from "./pages/ActionDetail";
import ApprovalQueuePage from "./pages/ApprovalQueuePage";

const queryClient = new QueryClient();

const DashboardRouteShell = () => (
  <ProtectedRoute>
    <WorkspaceLayout>
      <Outlet />
    </WorkspaceLayout>
  </ProtectedRoute>
);

const AppRoutes = ({ location }: { location: Location }) => (
  <Routes location={location}>
    <Route path="/" element={<Index />} />
    <Route path="/signup" element={<Signup />} />
    <Route path="/check-email" element={<CheckEmail />} />
    <Route path="/verify-success" element={<VerifySuccess />} />
    <Route path="/verify-email/:token" element={<VerifyEmail />} />
    <Route path="/verify-complete" element={<VerifyComplete />} />
    <Route path="/verified" element={<VerifyEmail />} />
    <Route path="/verified/:token" element={<VerifyEmail />} />
    <Route path="/login" element={<Login />} />
    <Route path="/forgot-password" element={<ForgotPassword />} />
    <Route path="/reset-password/:token" element={<ResetPassword />} />
    <Route path="/invite/accept" element={<InviteAccept />} />
    <Route path="/onboarding" element={<Onboarding />} />
    <Route path="/pricing" element={<Pricing />} />
    <Route path="/features" element={<Features />} />
    <Route path="/how-it-works" element={<HowItWorks />} />
    <Route path="/docs" element={<Docs />} />
    <Route path="/security" element={<Security />} />
    <Route path="/demo" element={<DemoWorkspace />} />
    <Route path="/demo/reports/:id" element={<DemoReportDetail />} />
    <Route path="/demo/reports/:id/pdf" element={<DemoPdfPreview />} />

    <Route element={<DashboardRouteShell />}>
      <Route
        path="/dashboard"
        element={
          <RouteErrorBoundary title="Dashboard failed to load">
            <Dashboard />
          </RouteErrorBoundary>
        }
      />
      <Route path="/dashboard/reports" element={<ReportsPage />} />
      <Route path="/dashboard/signals" element={<SignalsPage />} />
      <Route path="/dashboard/reports/:id" element={<ReportDetail />} />
      <Route path="/dashboard/signals/:signalId" element={<SignalDetail />} />
      <Route path="/signals/:signalId" element={<SignalDetail />} />
      <Route path="/dashboard/actions/:actionId" element={<ActionDetail />} />
      <Route
        path="/dashboard/actions"
        element={
          <RouteErrorBoundary title="Execution failed to load">
            <ExecutionPage />
          </RouteErrorBoundary>
        }
      />
      <Route path="/dashboard/billing" element={<DashboardBilling />} />
      <Route path="/dashboard/security" element={<DashboardSecurity />} />
      <Route path="/dashboard/account" element={<DashboardAccount />} />
      <Route path="/dashboard/team" element={<DashboardTeam />} />
      <Route path="/dashboard/brief-customization" element={<DashboardPdfPreview />} />
      <Route path="/dashboard/approval-queue" element={<AdminRoute><ApprovalQueuePage /></AdminRoute>} />
      <Route
        path="/upload"
        element={<Upload />}
      />
    </Route>
    <Route
      path="/dashboard/pdf-preview"
      element={<Navigate to="/dashboard/brief-customization" replace />}
    />
    <Route path="/privacy" element={<Privacy />} />
    <Route path="/terms" element={<Terms />} />
    <Route path="/contact" element={<Contact />} />
    <Route path="*" element={<NotFound />} />
  </Routes>
);

const RouteTransitionShell = () => {
  const location = useLocation();
  const transitionPath = location.pathname.toLowerCase();
  const isWorkspaceRoute = transitionPath.startsWith("/dashboard") || transitionPath === "/upload" || transitionPath.startsWith("/signals/");
  const shellClassName = isWorkspaceRoute ? "route-shell route-shell-workspace" : "route-shell route-shell-public";

  return (
    <div className={shellClassName}>
      <AppRoutes location={location} />
    </div>
  );
};

const AppLoadRedirect = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoading, isLoggedIn, user } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (!isLoggedIn || !user) return;

    const bootRedirectAllowed =
      location.pathname === "/login" ||
      location.pathname === "/signup" ||
      location.pathname === "/check-email" ||
      location.pathname === "/verify-success" ||
      location.pathname === "/verify-complete" ||
      location.pathname.startsWith("/verify-email") ||
      location.pathname === "/verified" ||
      location.pathname.startsWith("/verified");
    if (!bootRedirectAllowed) return;

    const destination = getRequiredAuthenticatedDestination(user);
    if (location.pathname !== destination) {
      navigate(destination, { replace: true });
    }
  }, [isLoading, isLoggedIn, location.pathname, navigate, user]);

  return null;
};

const App = () => {
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState("Trial limit reached");

  useEffect(() => {
    const onPlanLimit = (event: Event) => {
      const custom = event as CustomEvent<{ message?: string }>;
      setUpgradeMessage(custom.detail?.message || "Trial limit reached");
      setUpgradeModalOpen(true);
    };
    window.addEventListener(PLAN_LIMIT_EVENT, onPlanLimit as EventListener);
    return () => window.removeEventListener(PLAN_LIMIT_EVENT, onPlanLimit as EventListener);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner position="bottom-right" visibleToasts={4} expand />
          <UpgradeModal
            open={upgradeModalOpen}
            message={upgradeMessage}
            onClose={() => setUpgradeModalOpen(false)}
          />
          <BrowserRouter>
            <AppLoadRedirect />
            <RouteTransitionShell />
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;


