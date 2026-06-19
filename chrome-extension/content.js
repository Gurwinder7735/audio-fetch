const BUTTON_ID = "audiofetch-floating-mp3-btn";

function isWatchPage() {
  return (
    location.hostname.includes("youtube.com") &&
    location.pathname === "/watch" &&
    new URLSearchParams(location.search).get("v")
  );
}

function getCanonicalYouTubeUrl() {
  const u = new URL(location.href);

  // youtube.com/watch?v=VIDEO_ID
  if (u.hostname.includes("youtube.com") && u.pathname === "/watch") {
    const v = u.searchParams.get("v");
    if (v) return `https://www.youtube.com/watch?v=${encodeURIComponent(v)}`;
    return null;
  }

  // youtu.be/VIDEO_ID
  if (u.hostname === "youtu.be") {
    const id = u.pathname.replace(/^\/+/, "").split("/")[0];
    if (id) return `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
    return null;
  }

  return null;
}

function ensureButton() {
  if (!isWatchPage() && location.hostname !== "youtu.be") return;
  if (document.getElementById(BUTTON_ID)) return;

  const btn = document.createElement("button");
  btn.id = BUTTON_ID;
  btn.type = "button";
  btn.textContent = "MP3";

  Object.assign(btn.style, {
    position: "fixed",
    right: "18px",
    bottom: "18px",
    zIndex: "2147483647",
    width: "56px",
    height: "56px",
    borderRadius: "999px",
    border: "none",
    cursor: "pointer",
    background: "#111827",
    color: "#fff",
    fontSize: "16px",
    fontFamily:
      "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
    boxShadow: "0 8px 24px rgba(0,0,0,.35)",
  });

  let busy = false;

  async function run() {
    if (busy) return;
    busy = true;
    btn.textContent = "…";
    btn.style.opacity = "0.8";

    try {
      const url = getCanonicalYouTubeUrl();
      if (!url) {
        btn.textContent = "ERR";
        btn.title = "Could not detect YouTube video ID on this page";
        setTimeout(() => {
          btn.textContent = "MP3";
          btn.title = "";
        }, 1500);
        return;
      }
      const res = await chrome.runtime.sendMessage({
        type: "AUDIOFETCH_DOWNLOAD_MP3",
        url,
      });
      if (!res?.ok) {
        const msg = res?.error || "Download failed";
        btn.textContent = "ERR";
        btn.title = msg;
        setTimeout(() => {
          btn.textContent = "MP3";
          btn.title = "";
        }, 1500);
        return;
      }

      btn.textContent = "OK";
      setTimeout(() => {
        btn.textContent = "MP3";
      }, 900);
    } catch (e) {
      btn.textContent = "ERR";
      btn.title = String(e);
      setTimeout(() => {
        btn.textContent = "MP3";
        btn.title = "";
      }, 1500);
    } finally {
      busy = false;
      btn.style.opacity = "1";
    }
  }

  btn.addEventListener("click", run);
  document.documentElement.appendChild(btn);
}

// YouTube is a SPA; re-check on navigation changes.
ensureButton();
setInterval(ensureButton, 1000);

