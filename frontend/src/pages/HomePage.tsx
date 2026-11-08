import { HardDrive, Lock, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { VideoInfo } from "@/api/models";
import { Card, CardBody } from "@/components/ui/card";
import { FormatPicker } from "@/components/video/FormatPicker";
import { UrlForm } from "@/components/video/UrlForm";
import { VideoPreview } from "@/components/video/VideoPreview";

const HINTS = [
  { icon: HardDrive, text: "Saved locally to ~/Videos/VidDwn" },
  { icon: Zap, text: "Video, audio and subtitles" },
  { icon: Lock, text: "Localhost only, no account" },
];

export function HomePage() {
  const [video, setVideo] = useState<VideoInfo | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (video) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [video]);

  return (
    <div className="mx-auto w-full max-w-4xl">
      <header className="relative overflow-hidden rounded-2xl border border-edge-soft bg-panel/60 px-5 py-8 sm:px-8 sm:py-10">
        <div className="grid-noise pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative">
          <p className="text-[11px] font-medium uppercase tracking-[0.28em] text-accent">
            Local downloader
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Paste a link. Keep the file.
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            Grab video or audio from the sites yt-dlp supports. Everything stays on this
            machine.
          </p>
          <div className="mt-5">
            <UrlForm onLoaded={setVideo} busy={false} />
          </div>
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
            {HINTS.map(({ icon: Icon, text }) => (
              <span key={text} className="flex items-center gap-1.5 text-[11px] text-faint">
                <Icon size={12} /> {text}
              </span>
            ))}
          </div>
        </div>
      </header>

      <div ref={resultRef} className="scroll-mt-6">
        {video ? (
          <Card className="mt-4 animate-in">
            <CardBody className="space-y-5">
              <VideoPreview video={video} />
              <div className="border-t border-edge-soft" />
              <FormatPicker key={video.id} video={video} />
            </CardBody>
          </Card>
        ) : (
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              {
                title: "Pick a quality",
                body: "Presets resolve against the streams that actually exist, so 1080p means 1080p.",
              },
              {
                title: "Watch it live",
                body: "Progress, speed and ETA stream over a local WebSocket while yt-dlp runs.",
              },
              {
                title: "Resume safely",
                body: "Cancel, retry or restart — partial files are kept and verified before completion.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-xl border border-edge-soft bg-surface/40 p-4"
              >
                <h2 className="text-[13px] font-medium text-ink">{item.title}</h2>
                <p className="mt-1 text-xs leading-relaxed text-muted">{item.body}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
