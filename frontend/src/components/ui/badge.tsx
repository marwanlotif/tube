import { cn } from "@/lib/utils";

const tones = {
  accent: "border-accent/25 bg-accent/10 text-accent",
  success: "border-[#2c5f3a] bg-[#152b1c] text-[#8ee6a1]",
  muted: "border-edge bg-white/[0.03] text-muted",
  danger: "border-[#4a2424] bg-[#2a1414] text-danger",
  warn: "border-[#4d3a1d] bg-[#2a2013] text-warn",
  info: "border-[#233c5a] bg-[#122030] text-info",
};

export function Badge({
  tone = "muted",
  className,
  children,
}: {
  tone?: keyof typeof tones;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium tracking-wide",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
