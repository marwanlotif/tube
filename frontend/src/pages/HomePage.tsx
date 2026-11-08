import { HardDrive, ListVideo, Lock, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useProbe } from "@/api/queries";
import { CollectionPicker } from "@/components/collection/CollectionPicker";
import { CollectionPreview } from "@/components/collection/CollectionPreview";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { FormatPicker } from "@/components/video/FormatPicker";
import { UrlForm } from "@/components/video/UrlForm";
import { VideoPreview } from "@/components/video/VideoPreview";

const HINTS = [
  { icon: HardDrive, text: "Saved locally to ~/Videos/VidDwn" },
  { icon: Zap, text: "Videos, playlists and channels" },
  { icon: Lock, text: "Localhost only, no account" },
];

export function HomePage() {
  const [url, setUrl] = useState("");
  const probe = useProbe();
  const result = probe.data;
  const sourceUrl = probe.variables?.url ?? "";
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [result]);

  const load = (target: string, playlist = false) => {
    setUrl(target);
    probe.mutate({ url: target, playlist });
  };

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
            <UrlForm
              url={url}
              onUrlChange={(value) => {
                setUrl(value);
                if (probe.isError) probe.reset();
              }}
              onSubmit={(value) => load(value)}
              onClear={() => {
                setUrl("");
                probe.reset();
              }}
              loading={probe.isPending}
              error={probe.error}
            />
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
        {result?.kind === "video" ? (
          <Card className="mt-4 animate-in">
            <CardBody className="space-y-5">
              <VideoPreview video={result} />
              {result.playlist_hint ? (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-edge-soft bg-surface/60 px-3.5 py-2.5">
                  <p className="flex items-center gap-2 text-[13px] text-muted">
                    <ListVideo size={14} className="text-faint" />
                    This video is part of a playlist.
                  </p>
                  <Button size="sm" variant="outline" onClick={() => load(sourceUrl, true)}>
                    Load the playlist
                  </Button>
                </div>
              ) : null}
              <div className="border-t border-edge-soft" />
              <FormatPicker key={result.id} video={result} />
            </CardBody>
          </Card>
        ) : result?.kind === "collection" ? (
          <Card className="mt-4 animate-in">
            <CardBody className="space-y-5">
              <CollectionPreview collection={result} onOpen={(target) => load(target)} />
              <CollectionPicker
                key={`${result.id}:${sourceUrl}`}
                collection={result}
                sourceUrl={sourceUrl}
              />
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
