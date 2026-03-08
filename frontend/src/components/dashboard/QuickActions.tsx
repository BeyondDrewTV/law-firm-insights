import { Button } from "@/components/ui/button";

type QuickActionsProps = {
  onUploadFeedback: () => void;
  onCreateAction: () => void;
  onGenerateGovernanceBrief: () => void;
};

const QuickActions = ({
  onUploadFeedback,
  onCreateAction,
  onGenerateGovernanceBrief,
}: QuickActionsProps) => {
  return (
    <div className="flex items-center gap-4" aria-label="Quick actions">
      <Button
        type="button"
        variant="secondary"
        onClick={onUploadFeedback}
      >
        Upload Feedback
      </Button>
      <Button
        type="button"
        variant="primary"
        onClick={onCreateAction}
      >
        Create Action
      </Button>
      <Button
        type="button"
        variant="secondary"
        onClick={onGenerateGovernanceBrief}
      >
        Generate Governance Brief
      </Button>
    </div>
  );
};

export default QuickActions;
