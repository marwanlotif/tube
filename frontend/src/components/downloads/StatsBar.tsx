import { CheckCircle2, Database, HardDrive, Loader2 } from "lucide-react";

import { useStats } from "@/api/queries";
import { cn, formatBytes } from "@/lib/utils";

function Tile({
  icon: Icon,
  label,
  value,
  detail,
  tone = "default",
}: {
  icon: typeof HardDrive;
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "accent";
}) {
  return (
    <div className="rounded-xl border border-edge-soft bg-panel/70 p-4">
      <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">
        <Icon size={12} className={tone === "accent" ? "text-accent" : undefined} />
        {label}
      </div>
      <div
        className={cn(
          "mt-1.5 text-xl font-semibold tracking-tight",
          tone === "accent" ? "text-accent" : "text-ink",
        )}
      >
        {value}
      </div>
      {detail ? <div className="mt-0.5 text-[11px] text-faint">{detail}</div> : null}
    </div>
  );
}

export function StatsBar() {
  const { data } = useStats();
  const counts = data?.counts ?? {};
  const active = data?.active_total ?? 0;
  const completed = data?.completed_total ?? 0;
  const failed = counts.failed ?? 0;
  const diskFree = data?.disk_free ?? null;
  const diskTotal = data?.disk_total ?? null;
  const usedPercent =
    diskFree !== null && diskTotal ? ((diskTotal - diskFree) / diskTotal) * 100 : null;

  return (
    <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
      <Tile
        icon={active > 0 ? Loader2 : CheckCircle2}
        label="Active"
        value={String(active)}
        detail={active > 0 ? "in the queue right now" : "queue is idle"}
        tone={active > 0 ? "accent" : "default"}
      />
      <Tile
        icon={CheckCircle2}
        label="Completed"
        value={String(completed)}
        detail={failed > 0 ? `${failed} failed` : "all time"}
      />
      <Tile
        icon={Database}
        label="Last 7 days"
        value={formatBytes(data?.bytes_last_7d)}
        detail="downloaded"
      />
      <div className="rounded-xl border border-edge-soft bg-panel/70 p-4">
        <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">
          <HardDrive size={12} /> Disk free
        </div>
        <div className="mt-1.5 text-xl font-semibold tracking-tight text-ink">
          {formatBytes(diskFree)}
        </div>
        <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-[#1b2028]">
          <div
            className={cn(
              "h-full rounded-full",
              (usedPercent ?? 0) > 90 ? "bg-danger" : "bg-muted",
            )}
            style={{ width: `${Math.min(100, Math.max(0, usedPercent ?? 0))}%` }}
          />
        </div>
        <div className="mt-1 text-[11px] text-faint">
          {diskTotal ? `of ${formatBytes(diskTotal)}` : "storage info"}
        </div>
      </div>
    </div>
  );
}
