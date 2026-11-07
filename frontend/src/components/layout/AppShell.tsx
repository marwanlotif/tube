import {
  Activity,
  AlertTriangle,
  Clapperboard,
  Download,
  Settings2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useSystem } from "@/api/queries";
import { cn } from "@/lib/utils";
import { useRealtimeStatus } from "@/realtime/RealtimeProvider";

const NAV = [
  { to: "/", label: "Downloader", icon: Download, end: true },
  { to: "/downloads", label: "Downloads", icon: Activity, end: false },
  { to: "/settings", label: "Settings", icon: Settings2, end: false },
];

function NavItem({
  to,
  label,
  icon: Icon,
  end,
}: {
  to: string;
  label: string;
  icon: typeof Download;
  end: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-white/[0.06] text-ink"
            : "text-muted hover:bg-white/[0.03] hover:text-ink",
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            size={16}
            className={cn("transition-colors", isActive ? "text-accent" : "text-faint")}
          />
          <span>{label}</span>
        </>
      )}
    </NavLink>
  );
}

function HealthWarning() {
  const { data } = useSystem();
  if (!data) return null;
  const missing = [
    !data.ytdlp_ok ? "yt-dlp" : null,
    !data.ffmpeg_ok ? "FFmpeg" : null,
  ].filter(Boolean);
  if (missing.length === 0) return null;
  return (
    <div className="flex items-start gap-3 border-b border-[#4d3a1d] bg-[#221a0e] px-5 py-3 text-sm text-warn lg:px-10">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <p>
        {missing.join(" and ")} {missing.length > 1 ? "are" : "is"} not available. Downloads
        that need {missing.length > 1 ? "them" : "it"} will fail. Install it and restart
        TubeTUI.
      </p>
    </div>
  );
}

export function AppShell() {
  const connected = useRealtimeStatus();
  const { data: system } = useSystem();

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <aside className="flex shrink-0 flex-col border-b border-edge-soft bg-surface/60 lg:sticky lg:top-0 lg:h-screen lg:w-60 lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between px-5 py-4 lg:py-6">
          <NavLink to="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-ink">
              <Clapperboard size={17} strokeWidth={2.4} />
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-ink">TubeTUI</span>
          </NavLink>
          <span
            className="flex items-center gap-1.5 text-[11px] text-faint lg:hidden"
            title={connected ? "Live updates connected" : "Reconnecting"}
          >
            {connected ? <Wifi size={13} /> : <WifiOff size={13} />}
            {connected ? "live" : "offline"}
          </span>
        </div>

        <nav className="flex gap-1 px-3 pb-3 lg:flex-col lg:pb-0">
          {NAV.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>

        <div className="mt-auto hidden border-t border-edge-soft p-4 lg:block">
          <div className="flex items-center justify-between text-[11px] text-faint">
            <span className="flex items-center gap-1.5">
              {connected ? (
                <Wifi size={12} className="text-accent" />
              ) : (
                <WifiOff size={12} className="text-warn" />
              )}
              {connected ? "Live updates" : "Reconnecting"}
            </span>
            <span className="font-mono">v1.0</span>
          </div>
          {system ? (
            <p className="mt-2 truncate text-[11px] text-faint" title={system.video_dir}>
              {system.video_dir}
            </p>
          ) : null}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <HealthWarning />
        <main className="flex-1 px-5 py-6 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
