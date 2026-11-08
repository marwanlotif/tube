import { describe, expect, it } from "vitest";

import { formatBytes, formatDuration, formatEta, formatSpeed, statusMeta } from "./utils";

describe("formatBytes", () => {
  it("handles missing values and small sizes", () => {
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(undefined)).toBe("—");
    expect(formatBytes(Number.NaN)).toBe("—");
    expect(formatBytes(512)).toBe("512 B");
  });

  it("scales through units and drops decimals at three digits", () => {
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(5 * 1024 ** 2)).toBe("5.0 MB");
    expect(formatBytes(150 * 1024 ** 3)).toBe("150 GB");
    expect(formatBytes(3 * 1024 ** 5)).toBe("3072 TB");
  });
});

describe("durations", () => {
  it("formats clock-style durations", () => {
    expect(formatDuration(0)).toBe("—");
    expect(formatDuration(65)).toBe("1:05");
    expect(formatDuration(3725)).toBe("1:02:05");
  });

  it("formats remaining time", () => {
    expect(formatEta(null)).toBe("");
    expect(formatEta(42)).toBe("42s left");
    expect(formatEta(125)).toBe("2m 5s left");
    expect(formatEta(7260)).toBe("2h 1m left");
  });

  it("formats speed only when known", () => {
    expect(formatSpeed(0)).toBeNull();
    expect(formatSpeed(2048)).toBe("2.0 KB/s");
  });
});

describe("statusMeta", () => {
  it("describes known statuses and falls back for unknown ones", () => {
    expect(statusMeta("downloading")).toMatchObject({ label: "Downloading", active: true });
    expect(statusMeta("interrupted").active).toBe(false);
    expect(statusMeta("something-new")).toEqual(statusMeta("queued"));
  });
});
