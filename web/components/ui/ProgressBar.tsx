import { cn } from "@/lib/cn";

type ProgressBarProps = {
  value: number;
  color?: string;
  className?: string;
};

export function ProgressBar({ value, color = "var(--color-accent)", className }: ProgressBarProps) {
  const width = Math.max(0, Math.min(100, value));

  return (
    <div className={cn("h-2 overflow-hidden rounded-pill bg-surface2", className)}>
      <div
        className="h-full rounded-pill transition-[width]"
        style={{ width: `${width}%`, backgroundColor: color }}
      />
    </div>
  );
}
