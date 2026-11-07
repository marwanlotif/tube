import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Link2, Loader2, X } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import type { VideoInfo } from "@/api/models";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/utils";

export function UrlForm({
  onLoaded,
  busy,
}: {
  onLoaded: (video: VideoInfo) => void;
  busy?: boolean;
}) {
  const [url, setUrl] = useState("");
  const mutation = useMutation({
    mutationFn: api.videoInfo,
    onSuccess: onLoaded,
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;
    mutation.mutate(trimmed);
  };

  const loading = mutation.isPending || busy;

  return (
    <form onSubmit={submit} className="w-full">
      <div className="relative flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Link2
            size={16}
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-faint"
          />
          <Input
            value={url}
            onChange={(event) => {
              setUrl(event.target.value);
              if (mutation.isError) mutation.reset();
            }}
            placeholder="https://www.youtube.com/watch?v=..."
            aria-label="Video URL"
            inputMode="url"
            spellCheck={false}
            autoFocus
            className="h-12 pl-10 pr-10 text-[15px]"
          />
          {url ? (
            <button
              type="button"
              aria-label="Clear URL"
              onClick={() => {
                setUrl("");
                mutation.reset();
              }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-faint transition-colors hover:bg-white/5 hover:text-ink"
            >
              <X size={15} />
            </button>
          ) : null}
        </div>
        <Button type="submit" size="lg" disabled={loading || !url.trim()} className="h-12 px-6">
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Reading video
            </>
          ) : (
            <>
              Fetch <ArrowRight size={16} />
            </>
          )}
        </Button>
      </div>
      {mutation.isError ? (
        <p className="mt-2 text-sm text-danger">{errorMessage(mutation.error)}</p>
      ) : null}
    </form>
  );
}
