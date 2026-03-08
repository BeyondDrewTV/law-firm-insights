type MarketingProofBarProps = {
  items: string[];
  className?: string;
};

const MarketingProofBar = ({ items, className = "" }: MarketingProofBarProps) => {
  return (
    <div
      className={[
        "mt-5 flex flex-wrap items-center gap-2 text-xs text-slate-200",
        className,
      ].join(" ")}
    >
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border border-white/20 bg-white/5 px-2.5 py-1"
        >
          {item}
        </span>
      ))}
    </div>
  );
};

export default MarketingProofBar;
