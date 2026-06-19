const DEFAULT_BACKEND_URL = "http://localhost:8000/api/download-mp3";

async function getBackendUrl() {
  const stored = await chrome.storage.local.get(["audiofetchBackendUrl"]);
  return stored.audiofetchBackendUrl || DEFAULT_BACKEND_URL;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "AUDIOFETCH_DOWNLOAD_MP3") return;

  (async () => {
    try {
      const url = String(msg.url || "").trim();
      if (!url) {
        sendResponse({ ok: false, error: "Missing URL" });
        return;
      }

      const backendUrl = await getBackendUrl();
      // Use the GET endpoint so Chrome can download "normally" from a URL.
      const downloadUrl = `${backendUrl}?url=${encodeURIComponent(url)}`;

      chrome.downloads.download(
        {
          url: downloadUrl,
          saveAs: true,
          conflictAction: "uniquify",
        },
        (downloadId) => {
          const err = chrome.runtime.lastError?.message;
          if (err || !downloadId) {
            sendResponse({ ok: false, error: err || "Download failed" });
          } else {
            sendResponse({ ok: true, downloadId });
          }
        }
      );
      return;

    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
  })();

  return true; // keep message channel open for async sendResponse
});

