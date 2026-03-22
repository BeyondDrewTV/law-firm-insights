import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, ShieldCheck, Upload } from "lucide-react";
import { toast } from "sonner";

import { createFirm, uploadCsv } from "@/api/authService";
import { completeOnboarding } from "@/api/authService";
import { DISPLAY_LABELS } from "@/constants/displayLabels";
import { useAuth } from "@/contexts/AuthContext";
import { getRequiredAuthenticatedDestination, isUserOnboardingComplete } from "@/lib/authRedirect";

type Step = 1 | 2 | 3 | 4 | "done";

const TRANSITION_MS = 220;

const Onboarding = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refreshUser, user, isLoading, isLoggedIn } = useAuth();
  const requestedPreview = searchParams.get("preview") === "true";
  const previewStepParam = searchParams.get("step");
  const isAdmin = user?.is_admin === true;
  const isPreview = requestedPreview && isAdmin;
  const previewStartStep = useMemo<Step>(() => {
    if (!isPreview) return 1;
    if (previewStepParam === "2") return 2;
    if (previewStepParam === "3") return 3;
    if (previewStepParam === "4") return 4;
    return 1;
  }, [isPreview, previewStepParam]);
  const onboardingComplete = useMemo(() => isUserOnboardingComplete(user), [user]);

  const [step, setStep] = useState<Step>(previewStartStep);
  const [visible, setVisible] = useState(true);

  const [firmName, setFirmName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedReportId, setUploadedReportId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const firmNameInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (user?.has_firm_context) {
      setFirmName((prev) => prev || user.firm_name || "");
    }
  }, [user?.firm_name, user?.has_firm_context]);

  useEffect(() => {
    if (step === 1) {
      window.setTimeout(() => {
        firmNameInputRef.current?.focus();
      }, 30);
    }
  }, [step]);

  useEffect(() => {
    if (isLoading) return;
    if (!isLoggedIn || !user) {
      navigate("/login", { replace: true });
      return;
    }
    const requiredDestination = getRequiredAuthenticatedDestination(user);
    if (requiredDestination === "/check-email") {
      navigate(requiredDestination, { replace: true });
      return;
    }
    if (requestedPreview && !isAdmin) {
      navigate(requiredDestination, { replace: true });
      return;
    }
    if (onboardingComplete && !isPreview) {
      navigate("/dashboard", { replace: true });
      return;
    }
  }, [isAdmin, isLoading, isLoggedIn, user, onboardingComplete, isPreview, navigate, requestedPreview]);

  useEffect(() => {
    setStep(previewStartStep);
    setVisible(true);
  }, [previewStartStep]);

  const stepIndex = useMemo(() => {
    if (step === "done") return 4;
    return step;
  }, [step]);

  const transitionTo = (next: Step) => {
    setVisible(false);
    window.setTimeout(() => {
      setStep(next);
      setVisible(true);
    }, TRANSITION_MS);
  };

  const handleContinueFromFirm = () => {
    if (!firmName.trim()) {
      toast.error("Enter your firm name to continue.");
      return;
    }
    transitionTo(2);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] || null;
    setSelectedFile(nextFile);
    setUploadedReportId(null);
  };

  const handleConfirmSetup = async () => {
    if (!firmName.trim()) {
      toast.error("Firm name is required.");
      transitionTo(1);
      return;
    }

    setIsSaving(true);

    try {
      if (isPreview) {
        transitionTo("done");
        return;
      }

      if (!user?.has_firm_context) {
        const firmResult = await createFirm({ name: firmName.trim() });
        if (!firmResult.success) {
          toast.error(firmResult.error || "Unable to create firm.");
          setIsSaving(false);
          return;
        }
      }

      if (selectedFile) {
        const uploadResult = await uploadCsv(selectedFile);
        if (!uploadResult.success) {
          toast.error(uploadResult.error || "Unable to upload CSV.");
          setIsSaving(false);
          return;
        }
        setUploadedReportId(uploadResult.data?.summary.report_id ?? null);
        window.dispatchEvent(new Event("reports:uploaded"));
      }

      const completeResult = await completeOnboarding();
      if (!completeResult.success) {
        toast.error(completeResult.error || "Unable to finish onboarding.");
        setIsSaving(false);
        return;
      }

      await refreshUser();
      window.sessionStorage.setItem("onboarding_just_completed", "1");
      transitionTo("done");
    } finally {
      setIsSaving(false);
    }
  };

  const openNextWorkspaceStep = () => {
    navigate(uploadedReportId ? `/dashboard/reports/${uploadedReportId}` : "/dashboard", { replace: true });
  };

  if (isLoading || !isLoggedIn || !user) {
    return null;
  }

  return (
    <main className="workspace-onboarding-shell fade-enter flex min-h-screen items-center justify-center px-6 py-12">
      <section className="workspace-onboarding-card w-full max-w-[560px] rounded-2xl border bg-white p-8 shadow-[0_20px_50px_rgba(0,0,0,0.14)] transition-all motion-slow ease-out">
        <header className="mb-8 space-y-2">
          {isPreview ? (
            <p className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-800">
              Internal Preview
            </p>
          ) : null}
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Step {stepIndex} of 4
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Start the first governance cycle</h1>
          <p className="max-w-xl text-[14px] font-normal text-[#6B7280]">
            Set up the workspace, confirm how feedback is handled, and bring in the first review export when you are ready.
          </p>
          {isPreview ? (
            <p className="text-[13px] text-slate-600">
              Internal owner preview. This walk-through is read-only and does not change firm setup or upload live data.
            </p>
          ) : null}
        </header>

        <div
          className={[
            "transition-all ease-out",
            visible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
            visible ? "animate-fade-in" : "",
          ].join(" ")}
          style={{ transitionDuration: `${TRANSITION_MS}ms` }}
        >
          {step === 1 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Name the workspace</h2>
                <p className="text-sm leading-relaxed text-slate-600">
                  Use the firm name partners and team leads will recognize in briefs and workspace review.
                </p>
              </div>
              <div className="space-y-2">
                <label htmlFor="firm_name" className="block text-sm font-medium text-slate-800">
                  Firm name
                </label>
                <input
                  ref={firmNameInputRef}
                  id="firm_name"
                  type="text"
                  value={firmName}
                  onChange={(event) => setFirmName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      handleContinueFromFirm();
                    }
                  }}
                  placeholder="Smith & Associates"
                  className="h-11 w-full rounded-lg border border-slate-300 px-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <button type="button" className="gov-btn-primary w-full justify-center" onClick={handleContinueFromFirm}>
                Continue
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Confirm feedback handling</h2>
                <p className="text-sm font-medium text-slate-700">Your client feedback stays firm-specific.</p>
                <p className="text-sm leading-relaxed text-slate-600">
                  Uploaded review data is stored securely and used only to generate client issues for your firm.
                  Clarion does not share client feedback across firms and does not use uploaded data to train
                  external models.
                </p>
              </div>

              <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-[13px] text-[#374151]">
                  <ShieldCheck className="h-4 w-4 text-[#0EA5C2]" />
                  <span>Secure encrypted storage</span>
                </div>
                <div className="flex items-center gap-2 text-[13px] text-[#374151]">
                  <ShieldCheck className="h-4 w-4 text-[#0EA5C2]" />
                  <span>Firm-isolated data processing</span>
                </div>
                <div className="flex items-center gap-2 text-[13px] text-[#374151]">
                  <ShieldCheck className="h-4 w-4 text-[#0EA5C2]" />
                  <span>Never used for external model training</span>
                </div>
              </div>

              <button type="button" className="gov-btn-primary w-full justify-center" onClick={() => transitionTo(3)}>
                Continue to first upload
              </button>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Start the first review cycle</h2>
                <p className="text-sm leading-relaxed text-slate-600">
                  Upload one CSV from the current review period now, or continue into the workspace and upload later.
                </p>
              </div>
              <div className="rounded-[10px] border border-[#D1D5DB] bg-white p-5">
                <p className="text-sm font-semibold text-slate-900">Upload one review export</p>
                <p className="mt-1 text-xs text-slate-600">Include columns for rating and review text. CSV format.</p>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-4 flex h-28 w-full flex-col items-center justify-center gap-2 rounded-[10px] border-2 border-dashed border-slate-300 bg-white text-sm text-slate-700 transition-colors hover:border-[#0EA5C2]"
                >
                  <Upload className="h-5 w-5" />
                  {selectedFile ? selectedFile.name : "Choose CSV file"}
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
              <div>
                <Link
                  to="/demo"
                  className="text-[13px] text-[#6B7280] transition-colors hover:text-slate-700 hover:underline"
                >
                  Or review the sample workspace &rarr;
                </Link>
              </div>

              <div className="flex items-center gap-3">
                <button type="button" className="gov-btn-primary flex-1 justify-center" onClick={() => transitionTo(4)}>
                  Continue
                </button>
                <button type="button" className="gov-btn-secondary" onClick={() => transitionTo(2)}>
                  Back
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Review before opening the workspace</h2>
                <p className="text-sm leading-relaxed text-slate-600">
                  Confirm the workspace name and whether you want Clarion to start the first cycle now.
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                <p>
                  <span className="font-medium text-slate-900">Firm:</span> {firmName.trim()}
                </p>
                <p className="mt-2">
                  <span className="font-medium text-slate-900">CSV:</span>{" "}
                  {selectedFile ? selectedFile.name : "No file selected (you can upload later)."}
                </p>
                <p className="mt-2 text-xs leading-5 text-slate-600">
                  {selectedFile
                    ? "If you continue with this file, Clarion will create the first report packet during setup and you can open it directly after onboarding."
                    : "If you continue without a file, Clarion will open workspace home and you can start the first upload from there."}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="gov-btn-primary flex-1 justify-center"
                  onClick={() => void handleConfirmSetup()}
                  disabled={isSaving}
                >
                  {isSaving ? "Finalizing..." : "Confirm setup"}
                </button>
                <button
                  type="button"
                  className="gov-btn-secondary"
                  onClick={() => transitionTo(3)}
                  disabled={isSaving}
                >
                  Back
                </button>
              </div>
            </div>
          )}

                    {step === "done" && (
            <div className="space-y-6 text-center">
              <div className="flex justify-center">
                <CheckCircle2 className="h-10 w-10 text-[#0EA5C2]" />
              </div>
              <h2 className="text-2xl font-bold text-[#0D1B2A]">Your workspace is ready.</h2>
              <p className="text-[14px] text-[#6B7280]">
                {uploadedReportId
                  ? `Clarion created the first report packet for ${firmName.trim() || "your firm"}. Open it first to review signals, decisions, and follow-through for the current cycle.`
                  : `Clarion is ready for ${firmName.trim() || "your firm"} to review the current cycle, latest brief, and follow-through.`}
              </p>

              <div className="space-y-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#9CA3AF]">
                  What Clarion does next
                </p>
                <div className="flex items-start justify-center gap-2">
                  {["Upload Feedback", `Review ${DISPLAY_LABELS.clientIssuePlural}`, "Assign Follow-Through", "Bring Brief Into Meetings"].map((label, index) => (
                    <div key={label} className="flex items-start">
                      <div className="w-[86px] text-center">
                        <span className="mx-auto inline-flex h-6 w-6 items-center justify-center rounded-full bg-[#0EA5C2] text-[11px] font-semibold text-white">
                          {index + 1}
                        </span>
                        <p className="mt-1 text-[12px] text-[#374151]">{label}</p>
                      </div>
                      {index < 3 ? <span className="px-1 pt-[3px] text-[14px] text-[#D1D5DB]">&rarr;</span> : null}
                    </div>
                  ))}
                </div>
              </div>

              <button type="button" className="gov-btn-primary h-12 w-full justify-center text-base" onClick={openNextWorkspaceStep}>
                {isPreview ? "Return to workspace" : uploadedReportId ? "Open first report" : "Open workspace home"}
              </button>
              {isPreview ? (
                <button
                  type="button"
                  className="gov-btn-secondary h-12 w-full justify-center text-base"
                  onClick={() => {
                    setStep(previewStartStep);
                    setVisible(true);
                  }}
                >
                  Restart internal preview
                </button>
              ) : null}
            </div>
          )}
        </div>
      </section>
    </main>
  );
};

export default Onboarding;


