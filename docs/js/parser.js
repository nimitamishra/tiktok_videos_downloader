/**
 * Parse TikTok data-export files entirely in the browser.
 * Your file is never uploaded to any server.
 */

export function formatPostDateLabel(dateStr) {
  const cleaned = dateStr.replace(/ UTC$/, "").trim();
  const [datePart, timePart] = cleaned.split(" ");
  const [y, mo, d] = datePart.split("-").map(Number);
  const [hh, mm, ss] = timePart.split(":").map(Number);
  const pad = (n) => String(n).padStart(2, "0");
  return `${y}-${pad(mo)}-${pad(d)} at ${pad(hh)}-${pad(mm)}-${pad(ss)}`;
}

export function filenameForPost(date, variant = 1) {
  let label = `TikTok video - ${formatPostDateLabel(date)}`;
  if (variant > 1) label += ` (${variant})`;
  return `${label}.mp4`;
}

export function assignUniqueVariants(entries) {
  const seen = new Map();
  return entries.map(({ date, link }) => {
    const key = formatPostDateLabel(date);
    const variant = (seen.get(key) || 0) + 1;
    seen.set(key, variant);
    return { date, link, variant };
  });
}

export function parsePostsTxt(text) {
  const entries = [];
  let currentDate = null;

  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith("Date:")) {
      currentDate = line.slice(5).trim();
    } else if (line.startsWith("Link:") && currentDate) {
      const link = line.slice(5).trim();
      if (link) entries.push({ date: currentDate, link });
      currentDate = null;
    }
  }
  return entries;
}

export function parseUserDataJson(text) {
  const data = JSON.parse(text);
  const list = data?.Video?.Videos?.VideoList;
  if (!Array.isArray(list)) {
    throw new Error(
      "Could not find Video.Videos.VideoList in this JSON file. Is it a TikTok user_data.json export?"
    );
  }
  return list
    .filter((item) => item?.Link)
    .map((item) => ({ date: item.Date, link: item.Link }));
}

export function parseExportFile(text, filename) {
  const lower = (filename || "").toLowerCase();
  const isJson =
    lower.endsWith(".json") ||
    text.trimStart().startsWith("{");

  const raw = isJson ? parseUserDataJson(text) : parsePostsTxt(text);
  if (raw.length === 0) {
    throw new Error(
      "No video links found. Check that you selected Posts.txt or user_data.json from your TikTok export."
    );
  }
  return assignUniqueVariants(raw);
}

export function summarizePosts(posts) {
  const labels = posts.map((p) => formatPostDateLabel(p.date));
  const sorted = [...labels].sort();
  return {
    count: posts.length,
    oldest: sorted[0],
    newest: sorted[sorted.length - 1],
    samples: posts.slice(0, 5).map((p) => filenameForPost(p.date, p.variant)),
  };
}
