import { Info } from "lucide-react";

type InfoTipProps = {
  label: string;
};

export function InfoTip({ label }: InfoTipProps) {
  return (
    <span
      title={label}
      aria-label={label}
      className="inline-flex h-5 w-5 items-center justify-center rounded-md text-muted"
    >
      <Info size={15} aria-hidden />
    </span>
  );
}
