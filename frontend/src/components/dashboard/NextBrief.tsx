import { DashboardCard } from "@/components/ui/card";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type NextBriefProps = {
  scheduledFor: string;
  onGenerateBrief: () => void;
};

const NextBrief = ({ scheduledFor, onGenerateBrief }: NextBriefProps) => {
  return (
    <DashboardCard
      title="Next Governance Brief"
      subtitle={`Scheduled for ${scheduledFor}`}
      className=""
    >
      <p className="body-text">
        Prepare now by reviewing {DISPLAY_LABELS.clientIssuePlural.toLowerCase()} and actions.
      </p>
      <div className="mt-4">
        <button type="button" className="gov-btn-primary px-3 py-1.5 text-xs" onClick={onGenerateBrief}>
          Generate Brief
        </button>
      </div>
    </DashboardCard>
  );
};

export default NextBrief;
