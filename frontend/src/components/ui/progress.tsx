import { cn } from "@/lib/utils";

export function Progress({
  value,
  indeterminate = false,
  className,
}: {
  value: number;
  indeterminate?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-[#1b2028]", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : Math.round(value)}
    >
      <div
        className={cn(
          "h-full rounded-full bg-accent transition-[width] duration-500 ease-out",
          indeterminate && "progress-stripes relative w-1/3 animate-pulse",
        )}
        style={indeterminate ? undefined : { width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
