import { ChevronRight } from "lucide-react";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

const GovernanceLoop = () => {
  return (
    <div className="flex items-center gap-2 text-sm text-neutral-500" aria-label="Governance product loop">
      <span>Feedback</span>
      <ChevronRight aria-hidden="true" size={14} />
      <span className="font-semibold text-neutral-900">{DISPLAY_LABELS.clientIssuePlural}</span>
      <ChevronRight aria-hidden="true" size={14} />
      <span>Actions</span>
      <ChevronRight aria-hidden="true" size={14} />
      <span>Governance Brief</span>
    </div>
  );
};

export default GovernanceLoop;
