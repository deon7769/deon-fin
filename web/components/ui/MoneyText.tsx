import { cn } from "@/lib/cn";
import { formatBRL } from "@/lib/format";

type MoneyTextProps = {
  value: number;
  hidden?: boolean;
  colorBySign?: boolean;
  className?: string;
};

export function MoneyText({ value, hidden = false, colorBySign = false, className }: MoneyTextProps) {
  return (
    <span
      className={cn(
        colorBySign && value > 0 && "text-positive",
        colorBySign && value < 0 && "text-negative",
        className,
      )}
    >
      {hidden ? "••••••" : formatBRL(value)}
    </span>
  );
}
