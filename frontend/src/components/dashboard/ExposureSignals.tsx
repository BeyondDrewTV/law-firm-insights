import type { GovernanceSignal } from "@/api/authService";
import SeverityBadge from "@/components/ui/SeverityBadge";
import { useNavigate } from "react-router-dom";
import { DashboardCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type ExposureSignalsProps = {
  signals: GovernanceSignal[];
  isLoading: boolean;
  onCreateAction: (signal: GovernanceSignal, index: number) => void;
};

const severityLabel = (severity: string) => {
  const normalized = (severity || "low").toLowerCase();
  if (normalized === "high") return "HIGH";
  if (normalized === "medium") return "MEDIUM";
  return "LOW";
};

const ExposureSignals = ({ signals, isLoading, onCreateAction }: ExposureSignalsProps) => {
  const navigate = useNavigate();

  return (
    <section aria-label="Client issues">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="section-title">Client Issues</h2>
        <span className="caption-text">Actionable client issue cards</span>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {[1, 2].map((n) => (
            <div key={n} className="flex flex-col gap-3 rounded-xl border bg-white p-6 shadow-sm">
              <div className="h-4 w-48 animate-pulse rounded bg-muted" />
              <div className="h-3.5 w-11/12 animate-pulse rounded bg-muted/70" />
              <div className="h-3.5 w-5/6 animate-pulse rounded bg-muted/70" />
              <div className="mt-1 h-6 w-28 animate-pulse rounded-full bg-muted/70" />
              <div className="mt-2 flex gap-2">
                <div className="h-8 w-24 animate-pulse rounded bg-muted" />
                <div className="h-8 w-24 animate-pulse rounded bg-muted" />
              </div>
            </div>
          ))}
        </div>
      ) : signals.length === 0 ? (
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <p className="body-text">No {DISPLAY_LABELS.clientIssuePlural.toLowerCase()} are available yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {signals.map((signal, index) => (
            <DashboardCard
              key={signal.id}
              title={
                <span className="flex items-center gap-2">
                  <span>{signal.title}</span>
                  <SeverityBadge severity={severityLabel(signal.severity)} />
                </span>
              }
              subtitle={signal.description}
              className="flex flex-col gap-3"
              subtitleClassName="body-text"
            >
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <Button type="button" variant="secondary" size="sm" onClick={() => onCreateAction(signal, index)}>
                  Create Action
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className="underline"
                  onClick={() => navigate(`/dashboard/signals/${signal.id}`)}
                >
                  View Details
                </Button>
              </div>
            </DashboardCard>
          ))}
        </div>
      )}
    </section>
  );
};

export default ExposureSignals;
