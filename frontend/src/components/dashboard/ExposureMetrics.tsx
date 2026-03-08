import { DashboardCard } from "@/components/ui/card";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type ExposureMetricsProps = {
  status: "Low" | "Moderate" | "High";
  asOf?: string | null;
  loading?: boolean;
  metrics: {
    feedbackSignals: number;
    newSignals: number;
    openActions: number;
    overdueActions: number;
  };
};

const statusClassMap: Record<ExposureMetricsProps["status"], string> = {
  Low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  Moderate: "border-amber-200 bg-amber-50 text-amber-700",
  High: "border-red-200 bg-red-50 text-red-700",
};

const metricItems = (metrics: ExposureMetricsProps["metrics"]) => [
  { label: DISPLAY_LABELS.clientIssuePlural, value: metrics.feedbackSignals },
  { label: `New ${DISPLAY_LABELS.clientIssuePlural}`, value: metrics.newSignals },
  { label: "Open actions", value: metrics.openActions },
  { label: "Overdue actions", value: metrics.overdueActions },
];

const ExposureMetrics = ({ status, asOf, loading = false, metrics }: ExposureMetricsProps) => {
  return (
    <DashboardCard
      title="Exposure Status"
      subtitle="Governance risk posture and operational counts"
      actions={
        <span className={["rounded-md border px-3 py-1 text-sm font-semibold", statusClassMap[status]].join(" ")}>
          {status} Risk
        </span>
      }
    >
      <div className="mb-5">
        <p className="text-sm text-neutral-600">Firm Exposure Status</p>
        <p className="mt-1 text-2xl font-semibold text-neutral-900">{status}</p>
        <p className="mt-1 text-xs text-neutral-500">As of: {asOf ? new Date(asOf).toLocaleString() : "Not available"}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {metricItems(metrics).map((metric) => (
          <div key={metric.label} className="rounded-lg border border-[var(--border)] bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-neutral-500">{metric.label}</p>
            <p className="mt-2 text-3xl font-semibold text-neutral-900">
              {loading ? "--" : metric.value}
            </p>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
};

export default ExposureMetrics;
