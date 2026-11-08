import { Check, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";

import type {
  AudioSettings,
  NetworkSettings,
  Settings,
  SubtitleSettings,
} from "@/api/models";
import { useSaveSettings, useSettings, useSystem } from "@/api/queries";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Toggle } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { errorMessage } from "@/lib/utils";

const COOKIE_BROWSERS = [
  { value: "", label: "Off — no browser cookies" },
  { value: "firefox", label: "Firefox" },
  { value: "chrome", label: "Chrome" },
  { value: "chromium", label: "Chromium" },
  { value: "brave", label: "Brave" },
  { value: "edge", label: "Edge" },
  { value: "opera", label: "Opera" },
  { value: "vivaldi", label: "Vivaldi" },
  { value: "safari", label: "Safari" },
];

const AUDIO_QUALITY = Array.from({ length: 10 }, (_, index) => ({
  value: String(index),
  label: index === 0 ? "Best (V0)" : `V${index}`,
}));

const AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav"];

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div>
          <h2 className="text-[13px] font-semibold text-ink">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted">{description}</p>
          ) : null}
        </div>
      </CardHeader>
      <CardBody className="space-y-4">{children}</CardBody>
    </Card>
  );
}

export function SettingsPage() {
  const { data, isLoading, isError, error } = useSettings();
  const { data: system } = useSystem();
  const save = useSaveSettings();
  const [form, setForm] = useState<Settings | null>(null);

  useEffect(() => {
    if (data) setForm((previous) => previous ?? data);
  }, [data]);

  if (isLoading || (!form && !isError)) {
    return (
      <div className="mx-auto flex w-full max-w-4xl items-center justify-center gap-2 py-24 text-sm text-muted">
        <Loader2 size={15} className="animate-spin" /> Loading settings
      </div>
    );
  }

  if (isError || !form) {
    return (
      <div className="mx-auto w-full max-w-4xl rounded-xl border border-[#3d2020] bg-[#1c1010] p-5 text-sm text-danger">
        Could not load settings: {errorMessage(error)}
      </div>
    );
  }

  const updateAudio = (patch: Partial<AudioSettings>) =>
    setForm({ ...form, audio: { ...form.audio, ...patch } });
  const updateSubtitles = (patch: Partial<SubtitleSettings>) =>
    setForm({ ...form, subtitles: { ...form.subtitles, ...patch } });
  const updateNetwork = (patch: Partial<NetworkSettings>) =>
    setForm({ ...form, network: { ...form.network, ...patch } });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    save.mutate(form, { onSuccess: (updated) => setForm(updated) });
  };

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-4xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Settings</h1>
          <p className="mt-0.5 text-sm text-muted">
            Applies to new downloads. Changes save to the local database.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {save.isSuccess ? (
            <Badge tone="success">
              <Check size={11} /> Saved
            </Badge>
          ) : null}
          <Button type="submit" variant="primary" disabled={save.isPending}>
            {save.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Save size={14} />
            )}
            Save settings
          </Button>
        </div>
      </header>

      {save.isError ? (
        <p className="rounded-lg border border-[#3d2020] bg-[#1c1010] px-3.5 py-2.5 text-sm text-danger">
          {errorMessage(save.error)}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Section
          title="Storage"
          description="Directories must stay inside the allowed media roots."
        >
          <Field label="Video folder" hint={system ? "allowed root checked" : undefined}>
            <Input
              value={form.video_dir}
              onChange={(event) => setForm({ ...form, video_dir: event.target.value })}
              spellCheck={false}
              className="font-mono text-xs"
            />
          </Field>
          <Field label="Audio folder">
            <Input
              value={form.audio_dir}
              onChange={(event) => setForm({ ...form, audio_dir: event.target.value })}
              spellCheck={false}
              className="font-mono text-xs"
            />
          </Field>
          <Field
            label="Filename template"
            hint="yt-dlp fields, must end with %(ext)s"
          >
            <Input
              value={form.filename_template}
              onChange={(event) =>
                setForm({ ...form, filename_template: event.target.value })
              }
              spellCheck={false}
              className="font-mono text-xs"
            />
          </Field>
        </Section>

        <Section title="Audio" description="Defaults for audio-only downloads.">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Format">
              <Select
                value={form.audio.format}
                onChange={(event) => updateAudio({ format: event.target.value })}
              >
                {AUDIO_FORMATS.map((format) => (
                  <option key={format} value={format}>
                    {format.toUpperCase()}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Quality">
              <Select
                value={form.audio.quality}
                onChange={(event) => updateAudio({ quality: event.target.value })}
              >
                {AUDIO_QUALITY.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="rounded-lg border border-edge-soft bg-surface/60 p-3">
            <Toggle
              checked={form.subtitles.enabled}
              onChange={(enabled) => updateSubtitles({ enabled })}
              label="Download subtitles by default"
              description="Can still be changed per download."
            />
            {form.subtitles.enabled ? (
              <div className="mt-3 space-y-3">
                <Field label="Languages" hint="comma separated">
                  <Input
                    value={form.subtitles.langs}
                    onChange={(event) => updateSubtitles({ langs: event.target.value })}
                    placeholder="en"
                    className="h-9"
                  />
                </Field>
                <Toggle
                  checked={form.subtitles.auto}
                  onChange={(auto) => updateSubtitles({ auto })}
                  label="Include auto-generated"
                />
                <Toggle
                  checked={form.subtitles.embed}
                  onChange={(embed) => updateSubtitles({ embed })}
                  label="Embed into the video"
                  description="Requires a container that supports subtitle tracks."
                />
              </div>
            ) : null}
          </div>
        </Section>

        <Section title="Network" description="Tuning for slow or rate-limited sources.">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Parallel fragments" hint="1–16">
              <Input
                type="number"
                min={1}
                max={16}
                value={form.network.fragments}
                onChange={(event) =>
                  updateNetwork({ fragments: Number(event.target.value) || 1 })
                }
              />
            </Field>
            <Field label="Retries">
              <Input
                type="number"
                min={0}
                max={50}
                value={form.network.retries}
                onChange={(event) =>
                  updateNetwork({ retries: Number(event.target.value) || 0 })
                }
              />
            </Field>
            <Field label="Socket timeout (s)">
              <Input
                type="number"
                min={5}
                max={120}
                value={form.network.socket_timeout}
                onChange={(event) =>
                  updateNetwork({ socket_timeout: Number(event.target.value) || 30 })
                }
              />
            </Field>
            <Field label="Rate limit" hint="2M, 500K, empty = unlimited">
              <Input
                value={form.network.rate_limit ?? ""}
                onChange={(event) =>
                  updateNetwork({ rate_limit: event.target.value.trim() || null })
                }
                placeholder="unlimited"
                className="font-mono text-xs"
              />
            </Field>
          </div>
        </Section>

        <Section
          title="Access & performance"
          description="Browser cookies are opt-in and only used when a site needs a signed-in session."
        >
          <Field label="Cookies from browser">
            <Select
              value={form.cookies_from_browser ?? ""}
              onChange={(event) =>
                setForm({
                  ...form,
                  cookies_from_browser: event.target.value || null,
                })
              }
            >
              {COOKIE_BROWSERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Concurrent downloads" hint="1–4, restart required">
            <Select
              value={String(form.max_concurrent_downloads)}
              onChange={(event) =>
                setForm({
                  ...form,
                  max_concurrent_downloads: Number(event.target.value),
                })
              }
            >
              {[1, 2, 3, 4].map((value) => (
                <option key={value} value={value}>
                  {value} at a time
                </option>
              ))}
            </Select>
          </Field>
          <p className="text-[11px] leading-relaxed text-faint">
            The worker count is applied the next time TubeTUI starts. Raising it above 1 can
            get you rate-limited by some sites.
          </p>
        </Section>
      </div>

      <div className="flex justify-end pb-2">
        <Button type="submit" variant="primary" disabled={save.isPending}>
          {save.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Save size={14} />
          )}
          Save settings
        </Button>
      </div>
    </form>
  );
}
