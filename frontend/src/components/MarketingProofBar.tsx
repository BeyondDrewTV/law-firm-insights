type MarketingProofBarProps = {
  items: string[];
  className?: string;
};

const MarketingProofBar = ({ items, className = "" }: MarketingProofBarProps) => {
  return (
    <div
      className={[
        "mt-5 flex flex-wrap items-center gap-2 text-xs text-slate-600",
        className,
      ].join(" ")}
    >
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full border border-[#D7D0C3] bg-[#FFFDF9] px-2.5 py-1"
        >
          {item}
        </span>
      ))}
    </div>
  );
};

export default MarketingProofBar;
