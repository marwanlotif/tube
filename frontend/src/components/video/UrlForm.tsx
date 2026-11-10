import { ArrowRight, Link2, Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/utils";

/** The link field. The page owns the probe so it can also open links itself. */
export function UrlForm({
  url,
  onUrlChange,
  onSubmit,
  onClear,
  loading,
  error,
}: {
  url: string;
  onUrlChange: (url: string) => void;
  onSubmit: (url: string) => void;
  onClear: () => void;
  loading: boolean;
  error: unknown;
}) {
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

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
            onChange={(event) => onUrlChange(event.target.value)}
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
              onClick={onClear}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-faint transition-colors hover:bg-white/5 hover:text-ink"
            >
              <X size={15} />
            </button>
          ) : null}
        </div>
        <Button type="submit" size="lg" disabled={loading || !url.trim()} className="h-12 px-6">
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Reading link
            </>
          ) : (
            <>
              Fetch <ArrowRight size={16} />
            </>
          )}
        </Button>
      </div>
      {error ? <p className="mt-2 text-sm text-danger">{errorMessage(error)}</p> : null}
    </form>
  );
}
