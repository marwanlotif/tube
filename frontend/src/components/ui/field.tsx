import { cn } from "@/lib/utils";

export function Field({
  label,
  hint,
  error,
  children,
  className,
}: {
  label: string;
  hint?: React.ReactNode;
  error?: string | null;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("block space-y-1.5", className)}>
      <span className="flex items-baseline justify-between gap-3">
        <span className="text-[13px] font-medium text-ink">{label}</span>
        {hint ? <span className="text-[11px] text-faint">{hint}</span> : null}
      </span>
      {children}
      {error ? <span className="block text-xs text-danger">{error}</span> : null}
    </label>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <div>
        <div className="text-[13px] font-medium text-ink">{label}</div>
        {description ? <div className="text-xs text-muted">{description}</div> : null}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full border transition-colors",
          checked ? "border-accent/40 bg-accent" : "border-edge bg-[#1c2129]",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-4.5 w-4.5 rounded-full transition-transform",
            checked ? "translate-x-[22px] bg-accent-ink" : "translate-x-0.5 bg-muted",
          )}
          style={{ height: 18, width: 18 }}
        />
      </button>
    </div>
  );
}
