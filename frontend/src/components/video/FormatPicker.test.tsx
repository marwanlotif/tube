import { fireEvent, screen, waitFor } from "@testing-library/react";
import { type MockInstance, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { makeDownload, makeVideoInfo } from "@/test/fixtures";
import { renderWithApp } from "@/test/render";

import { FormatPicker } from "./FormatPicker";

describe("FormatPicker", () => {
  let createDownload: MockInstance<typeof api.createDownload>;

  beforeEach(() => {
    createDownload = vi.spyOn(api, "createDownload").mockResolvedValue(makeDownload());
  });

  async function submitted() {
    fireEvent.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() => expect(createDownload).toHaveBeenCalledTimes(1));
    return createDownload.mock.calls[0][0];
  }

  it("downloads the 1080p preset by default and opens the queue", async () => {
    renderWithApp(<FormatPicker video={makeVideoInfo()} />);
    expect(await submitted()).toEqual({
      url: "https://www.youtube.com/watch?v=abc123",
      mode: "video",
      preset: "best_1080",
      subtitles: false,
      subtitle_langs: null,
    });
    expect(await screen.findByText("downloads page")).toBeDefined();
  });

  it("uses the chosen preset and keeps unavailable ones disabled", async () => {
    renderWithApp(<FormatPicker video={makeVideoInfo()} />);
    expect(screen.getByRole("button", { name: /Up to 4K/ })).toHaveProperty("disabled", true);
    fireEvent.click(screen.getByRole("button", { name: /Up to 720p/ }));
    expect(await submitted()).toMatchObject({ preset: "best_720" });
  });

  it("extracts audio in the chosen format", async () => {
    renderWithApp(<FormatPicker video={makeVideoInfo()} />);
    fireEvent.click(screen.getByRole("button", { name: "Audio" }));
    fireEvent.change(screen.getByLabelText(/^Audio format/), { target: { value: "flac" } });
    expect(await submitted()).toEqual({
      url: "https://www.youtube.com/watch?v=abc123",
      mode: "audio",
      preset: "audio",
      audio_format: "flac",
      subtitles: false,
      subtitle_langs: null,
    });
  });

  it("sends exact stream ids in custom mode", async () => {
    renderWithApp(<FormatPicker video={makeVideoInfo()} />);
    fireEvent.click(screen.getByRole("button", { name: "Choose exact formats" }));
    fireEvent.change(screen.getByLabelText(/^Audio stream/), { target: { value: "140" } });
    expect(await submitted()).toMatchObject({ video_id: "137", audio_id: "140" });
  });

  it("sends subtitle languages when subtitles are on", async () => {
    renderWithApp(<FormatPicker video={makeVideoInfo()} />);
    fireEvent.click(screen.getByRole("switch", { name: "Download subtitles" }));
    fireEvent.change(screen.getByLabelText(/^Languages/), { target: { value: " en,de " } });
    expect(await submitted()).toMatchObject({ subtitles: true, subtitle_langs: "en,de" });
  });

  it("shows why the server refused", async () => {
    createDownload.mockRejectedValue(new Error("That quality is not available"));
    renderWithApp(<FormatPicker video={makeVideoInfo()} />);
    fireEvent.click(screen.getByRole("button", { name: "Download" }));
    expect(await screen.findByText("That quality is not available")).toBeDefined();
  });
});
