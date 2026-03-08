import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { PartnerBriefDeliveryStatus } from "@/api/authService";

type EmailBriefPreviewModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  averageRating: string;
  topIssue: string;
  exampleQuote: string;
  recommendedDiscussion: string;
  htmlSummary: string;
  onSend: () => void;
  isSending?: boolean;
  deliveryStatus?: PartnerBriefDeliveryStatus | null;
  deliveryStatusLoading?: boolean;
};

export default function EmailBriefPreviewModal({
  open,
  onOpenChange,
  averageRating,
  topIssue,
  exampleQuote,
  recommendedDiscussion,
  htmlSummary,
  onSend,
  isSending = false,
  deliveryStatus = null,
  deliveryStatusLoading = false,
}: EmailBriefPreviewModalProps) {
  const deliveryUnavailable = deliveryStatus && !deliveryStatus.delivery_available;
  const deliveryStateKnown = Boolean(deliveryStatus);
  const sendDisabled = isSending || deliveryStatusLoading || !deliveryStateKnown || Boolean(deliveryUnavailable);
  const sendLabel = isSending
    ? "Sending brief..."
    : deliveryStatusLoading
      ? "Checking delivery..."
      : !deliveryStateKnown
        ? "Delivery status unavailable"
        : deliveryUnavailable
          ? "Delivery unavailable"
          : "Send to configured recipients";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Email Brief to Partners</DialogTitle>
          <DialogDescription>
            Preview the partner brief email before delivery to the configured recipient list for this workspace.
          </DialogDescription>
        </DialogHeader>

        <section className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
          <h3 className="text-sm font-semibold text-[#0D1B2A]">Summary Snapshot</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="rounded-[8px] border border-[#E5E7EB] bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-[0.08em] text-[#6B7280]">Average Rating</p>
              <p className="mt-1 text-sm text-[#0D1B2A]">{averageRating}</p>
            </div>
            <div className="rounded-[8px] border border-[#E5E7EB] bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-[0.08em] text-[#6B7280]">Top Issue</p>
              <p className="mt-1 text-sm text-[#0D1B2A]">{topIssue}</p>
            </div>
            <div className="rounded-[8px] border border-[#E5E7EB] bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-[0.08em] text-[#6B7280]">Example Client Quote</p>
              <p className="mt-1 text-sm text-[#0D1B2A]">&quot;{exampleQuote}&quot;</p>
            </div>
            <div className="rounded-[8px] border border-[#E5E7EB] bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-[0.08em] text-[#6B7280]">Recommended Partner Discussion</p>
              <p className="mt-1 text-sm text-[#0D1B2A]">{recommendedDiscussion}</p>
            </div>
          </div>
        </section>

        <section className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
          <h3 className="text-sm font-semibold text-[#0D1B2A]">Delivery</h3>
          {deliveryStatusLoading ? (
            <div className="mt-3 rounded-[8px] border border-[#E5E7EB] bg-slate-50 p-3 text-sm text-[#475569]">
              Checking current delivery configuration...
            </div>
          ) : deliveryStatus ? (
            <div
              className={[
                "mt-3 rounded-[8px] border p-3 text-sm",
                deliveryUnavailable
                  ? "border-amber-200 bg-amber-50 text-amber-900"
                  : "border-[#E5E7EB] bg-slate-50 text-[#475569]",
              ].join(" ")}
            >
              <p className="font-medium text-[#0D1B2A]">
                {deliveryStatus.delivery_available
                  ? `This send goes to ${deliveryStatus.recipient_count} configured recipient${deliveryStatus.recipient_count === 1 ? "" : "s"}.`
                  : "Partner brief delivery is not configured for this deployment."}
              </p>
              <p className="mt-2">
                {deliveryStatus.delivery_available
                  ? `From: ${deliveryStatus.from_email || "Configured sender"}`
                  : "If delivery is unavailable, clicking Send would not dispatch any email."}
              </p>
              {deliveryStatus.recipients.length > 0 ? (
                <p className="mt-2 break-words">Recipients: {deliveryStatus.recipients.join(", ")}</p>
              ) : null}
              <p className="mt-2">
                {deliveryStatus.delivery_available
                  ? "Clarion sends this immediately through the configured backend sender. If provider delivery fails, the brief is not queued for retry in the UI."
                  : "Next step: configure outbound email delivery and a partner recipient list, or contact support before trying again."}
              </p>
            </div>
          ) : (
            <div className="mt-3 rounded-[8px] border border-[#E5E7EB] bg-slate-50 p-3 text-sm text-[#475569]">
              Delivery status could not be confirmed right now. Clarion will not send until the configured sender and recipient list can be confirmed.
            </div>
          )}
        </section>

        <section className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
          <h3 className="text-sm font-semibold text-[#0D1B2A]">Email Preview</h3>
          <div className="mt-3 overflow-hidden rounded-[8px] border border-[#E5E7EB] bg-white">
            <iframe
              title="Partner brief email preview"
              srcDoc={htmlSummary}
              className="h-[420px] w-full bg-white"
            />
          </div>
        </section>

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            className="gov-btn-secondary"
            onClick={() => onOpenChange(false)}
            disabled={isSending}
          >
            Cancel
          </button>
          <button
            type="button"
            className="gov-btn-primary"
            onClick={onSend}
            disabled={sendDisabled}
          >
            {sendLabel}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
