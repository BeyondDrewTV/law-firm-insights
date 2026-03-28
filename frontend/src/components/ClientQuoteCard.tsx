type ClientQuoteCardProps = {
  quote: string;
  issue: string;
  sentiment: "complaint" | "praise";
  meta?: string;
  className?: string;
};

const sentimentStyles = (sentiment: "complaint" | "praise") => {
  if (sentiment === "complaint") {
    return {
      chip: "border border-rose-200 bg-rose-50 text-rose-700",
      accent: "border-l-rose-500",
      label: "Complaint",
    };
  }
  return {
    chip: "border border-emerald-200 bg-emerald-50 text-emerald-700",
    accent: "border-l-emerald-500",
    label: "Praise",
  };
};

const normalizeQuote = (value: string) =>
  value
    .trim()
    .replace(/^[“”"']+|[“”"']+$/g, "")
    .replace(/\s+/g, " ")
    .replace(/\s+([,.;!?])/g, "$1")
    .replace(/([.!?])([A-Z])/g, "$1 $2");

export default function ClientQuoteCard({
  quote,
  issue,
  sentiment,
  meta,
  className = "",
}: ClientQuoteCardProps) {
  const styles = sentimentStyles(sentiment);
  const normalizedQuote = normalizeQuote(quote);

  return (
    <article
      className={[
        "rounded-[10px] border border-[#E5E7EB] border-l-[3px] bg-white p-4 shadow-sm",
        styles.accent,
        className,
      ].join(" ")}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-neutral-500">{issue}</p>
        <span className={["inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold", styles.chip].join(" ")}>
          {styles.label}
        </span>
      </div>
      <p className="text-[14px] leading-relaxed text-[#0D1B2A]">&quot;{normalizedQuote}&quot;</p>
      {meta ? <p className="mt-2 text-[11px] text-[#6B7280]">{meta}</p> : null}
    </article>
  );
}
