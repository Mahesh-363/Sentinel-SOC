import test from "node:test";
import assert from "node:assert/strict";
import type * as DateHelpers from "./date";

const dateModuleSpecifier = "./date.ts";
const loadDateHelpers = (): Promise<typeof DateHelpers> =>
  import(dateModuleSpecifier) as Promise<typeof DateHelpers>;

test("parseUtcTimestamp treats naive ISO timestamps and 'Z' timestamps identically as UTC", async () => {
  const { parseUtcTimestamp } = await loadDateHelpers();
  const fromZ = parseUtcTimestamp("2026-11-25T07:37:35Z");
  const fromNaive = parseUtcTimestamp("2026-11-25T07:37:35");
  const fromSpaceNaive = parseUtcTimestamp("2026-11-25 07:37:35.123456");

  assert.ok(fromZ instanceof Date);
  assert.ok(fromNaive instanceof Date);
  assert.ok(fromSpaceNaive instanceof Date);

  assert.equal(fromZ.toISOString(), "2026-11-25T07:37:35.000Z");
  assert.equal(fromNaive.toISOString(), "2026-11-25T07:37:35.000Z");
  assert.equal(fromSpaceNaive.toISOString(), "2026-11-25T07:37:35.123Z");
});

test("parseUtcTimestamp preserves explicit timezone offsets and rejects invalid inputs", async () => {
  const { parseUtcTimestamp } = await loadDateHelpers();
  const fromIst = parseUtcTimestamp("2026-11-25T13:07:35+05:30");
  assert.ok(fromIst instanceof Date);
  assert.equal(fromIst.toISOString(), "2026-11-25T07:37:35.000Z");

  const validDate = new Date("2026-11-25T07:37:35Z");
  assert.equal(parseUtcTimestamp(validDate)?.getTime(), validDate.getTime());

  assert.equal(parseUtcTimestamp(null), null);
  assert.equal(parseUtcTimestamp(undefined), null);
  assert.equal(parseUtcTimestamp(""), null);
  assert.equal(parseUtcTimestamp("   "), null);
  assert.equal(parseUtcTimestamp("not-a-timestamp"), null);
  assert.equal(parseUtcTimestamp(new Date("invalid")), null);
});

test("format helpers render accurate local timezone output regardless of 'Z' suffix", async () => {
  const { formatLocalTime, formatLocalDateTime, formatLocalDate } = await loadDateHelpers();
  const utcWithZ = "2026-11-25T07:37:35Z";
  const utcNaive = "2026-11-25T07:37:35";

  // Explicit Asia/Kolkata check (07:37:35 UTC == 13:07:35 IST)
  const istTimeOptions: Intl.DateTimeFormatOptions = {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  };
  assert.equal(formatLocalTime(utcWithZ, istTimeOptions, "en-GB"), "13:07:35");
  assert.equal(formatLocalTime(utcNaive, istTimeOptions, "en-GB"), "13:07:35");

  // Also verify process/runtime local timezone conversion when TZ is set (e.g., TZ=Asia/Kolkata)
  const expectedLocalTime = new Date(utcWithZ).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  assert.equal(
    formatLocalTime(utcNaive, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }, "en-GB"),
    expectedLocalTime
  );

  // If running under TZ=Asia/Kolkata, naive UTC must display 13:07:35, never 07:37:35
  if (Intl.DateTimeFormat().resolvedOptions().timeZone === "Asia/Kolkata") {
    assert.equal(expectedLocalTime, "13:07:35");
  }

  // Date & DateTime formatting match explicit UTC Instant in local TZ
  assert.equal(
    formatLocalDateTime(utcNaive, { timeZone: "Asia/Kolkata", hour12: true }, "en-US"),
    formatLocalDateTime(utcWithZ, { timeZone: "Asia/Kolkata", hour12: true }, "en-US")
  );
  assert.equal(
    formatLocalDate("2026-11-25T20:30:00Z", { timeZone: "Asia/Kolkata" }, "en-GB"),
    "26/11/2026"
  );
  assert.equal(
    formatLocalDate("2026-11-25T20:30:00", { timeZone: "Asia/Kolkata" }, "en-GB"),
    "26/11/2026"
  );
});

test("format helpers return 'Never' for missing or invalid timestamps", async () => {
  const { formatLocalTime, formatLocalDateTime, formatLocalDate } = await loadDateHelpers();
  assert.equal(formatLocalTime(null), "Never");
  assert.equal(formatLocalDateTime(undefined), "Never");
  assert.equal(formatLocalDate("invalid-date"), "Never");
});
