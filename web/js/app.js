import { parseExportFile, summarizePosts } from "./parser.js";
import { buildPythonDownloader } from "./generate-script.js";

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const results = document.getElementById("results");
const errorBox = document.getElementById("error");
const videoCount = document.getElementById("video-count");
const dateRange = document.getElementById("date-range");
const sampleList = document.getElementById("sample-list");
const btnDownloadScript = document.getElementById("btn-download-script");
const btnCopySteps = document.getElementById("btn-copy-steps");
const privacyNote = document.getElementById("privacy-note");

/** @type {{ date: string, link: string, variant: number }[] | null} */
let currentPosts = null;

function showError(message) {
  errorBox.hidden = !message;
  errorBox.textContent = message || "";
}

function downloadBlob(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function handleFile(file) {
  showError("");
  results.hidden = true;
  currentPosts = null;
  btnDownloadScript.disabled = true;
  btnCopySteps.disabled = true;

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const posts = parseExportFile(String(reader.result), file.name);
      currentPosts = posts;
      const summary = summarizePosts(posts);

      videoCount.textContent = String(summary.count);
      dateRange.textContent = `${summary.oldest} → ${summary.newest}`;
      sampleList.innerHTML = summary.samples
        .map((name) => `<li><code>${escapeHtml(name)}</code></li>`)
        .join("");

      results.hidden = false;
      btnDownloadScript.disabled = false;
      btnCopySteps.disabled = false;
    } catch (err) {
      showError(err.message || "Could not read this file.");
    }
  };
  reader.onerror = () => showError("Failed to read the file.");
  reader.readAsText(file);
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getRunSteps() {
  const n = currentPosts?.length ?? 0;
  return `TikTok export download (${n} videos)

1. Save the downloaded file as download_my_tiktok_videos.py
2. Open Terminal in that folder
3. Run:
   python3 download_my_tiktok_videos.py

Videos save to ./downloaded_videos/
Names look like: TikTok video - 2025-04-05 at 01-36-32.mp4

Tip: pip install certifi  (if you see SSL errors on Mac)
Links expire — use a fresh TikTok data export if you get HTTP 403.

CLI repo: https://github.com/nimitamishra/tiktok-export-downloader`;
}

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) handleFile(file);
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFile(file);
});

btnDownloadScript.addEventListener("click", () => {
  if (!currentPosts?.length) return;
  const script = buildPythonDownloader(currentPosts);
  downloadBlob("download_my_tiktok_videos.py", script, "text/x-python");
});

btnCopySteps.addEventListener("click", async () => {
  if (!currentPosts?.length) return;
  const text = getRunSteps();
  try {
    await navigator.clipboard.writeText(text);
    btnCopySteps.textContent = "Copied!";
    setTimeout(() => {
      btnCopySteps.textContent = "Copy run instructions";
    }, 2000);
  } catch {
    showError("Could not copy — select and copy the GitHub README steps instead.");
  }
});

// Optional: configure for portfolio embed (set data-repo on <body>)
const repo = document.body.dataset.repo;
if (repo) {
  const githubLink = document.getElementById("github-link");
  if (githubLink) githubLink.href = repo;
}
