type UpgradeModalProps = {
  open: boolean;
  message?: string;
  onClose: () => void;
};

const UpgradeModal = ({ open, message, onClose }: UpgradeModalProps) => {
  if (!open) return null;

  const detailMessage =
    message && message.trim().length > 0
      ? message
      : "Free plans include one governance brief per month. Upgrade to Team or Firm to run ongoing governance cycles and track improvements over time.";
  const handleUpgrade = () => {
    onClose();
    window.location.assign("/pricing");
  };

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/35 px-4" role="dialog" aria-modal="true">
      <div className="gov-level-2 w-full max-w-md p-6">
        <h2 className="gov-h2">Trial Limit Reached</h2>
        <p className="mt-2 text-sm text-neutral-700">{detailMessage}</p>
        <div className="mt-5 flex items-center justify-end gap-2">
          <button type="button" className="gov-btn-secondary px-3 py-1.5 text-sm" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="gov-btn-primary px-3 py-1.5 text-sm" onClick={handleUpgrade}>
            Upgrade Plan
          </button>
        </div>
      </div>
    </div>
  );
};

export default UpgradeModal;
