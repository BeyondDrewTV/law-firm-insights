import { DashboardCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type GovernanceGuidanceProps = {
  directive: string;
  recommendedAction: string;
  onOpenActions: () => void;
};

const GovernanceGuidance = ({ directive, recommendedAction, onOpenActions }: GovernanceGuidanceProps) => {
  return (
    <DashboardCard
      title="Next recommended move"
      subtitle="The clearest next step based on current client issues and action state."
    >
      <div className="gov-card-content">
        <p className="text-base font-medium text-neutral-900">{directive}</p>
        <div className="rounded-lg border border-[var(--border)] bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-neutral-500">Recommended next step</p>
          <p className="mt-1 text-sm font-medium text-neutral-900">{recommendedAction}</p>
        </div>
      </div>
      <div className="mt-4">
        <Button type="button" variant="primary" onClick={onOpenActions}>
          Open actions workspace
        </Button>
      </div>
    </DashboardCard>
  );
};

export default GovernanceGuidance;
