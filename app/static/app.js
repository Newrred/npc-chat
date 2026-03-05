const form = document.getElementById("chatForm");
const messageEl = document.getElementById("message");
const comfyToggle = document.getElementById("comfyToggle");
const statusBadge = document.getElementById("statusBadge");

const replyEl = document.getElementById("reply");
const faceEl = document.getElementById("face");
const tagsEl = document.getElementById("tags");
const portraitEl = document.getElementById("portrait");
const portraitFallbackEl = document.getElementById("portraitFallback");

const history = [];
const API_BASE_URL = String(window.NPC_API_BASE_URL || "").replace(/\/$/, "");
const CHAT_API_URL = API_BASE_URL ? `${API_BASE_URL}/api/chat` : "/api/chat";
const IMAGE_STATUS_API_URL = API_BASE_URL ? `${API_BASE_URL}/api/image/status` : "/api/image/status";

let imagePollController = null;
let sessionId = null;

function stopImagePolling() {
  if (!imagePollController) return;
  imagePollController.abort();
  imagePollController = null;
}

function setPortrait(url) {
  if (!url) {
    portraitEl.style.display = "none";
    portraitEl.removeAttribute("src");
    portraitFallbackEl.style.display = "block";
    return;
  }

  portraitEl.src = url;
  portraitEl.style.display = "block";
  portraitFallbackEl.style.display = "none";
}

portraitEl.addEventListener("error", () => {
  portraitEl.style.display = "none";
  portraitEl.removeAttribute("src");
  portraitFallbackEl.style.display = "block";
});

function setComfyBadge(isOn) {
  statusBadge.textContent = `Comfy: ${isOn ? "on" : "off"}`;
}

comfyToggle.addEventListener("change", () => setComfyBadge(comfyToggle.checked));
setComfyBadge(false);

async function pollImageStatus(sessionId, face) {
  stopImagePolling();
  const controller = new AbortController();
  imagePollController = controller;

  const maxAttempts = 10;
  const intervalMs = 2000;

  for (let i = 0; i < maxAttempts; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    if (controller.signal.aborted) return;

    const url = `${IMAGE_STATUS_API_URL}?session_id=${encodeURIComponent(sessionId)}&face=${encodeURIComponent(face)}`;

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) continue;
      const data = await response.json();

      if (data.image_url) {
        setPortrait(data.image_url);
      }
      if (data.comfy_status === "generated" || data.comfy_status === "error") {
        return;
      }
    } catch (error) {
      if (controller.signal.aborted) return;
    }
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageEl.value.trim();
  if (!message) return;

  replyEl.textContent = "응답 생성 중...";

  try {
    const response = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history,
        session_id: sessionId,
        comfy_on: comfyToggle.checked,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    sessionId = data.session_id || sessionId;

    replyEl.textContent = data.reply;
    faceEl.textContent = `face: ${data.face} (${data.comfy_status}/${data.image_source || "none"})`;
    tagsEl.textContent = `tags: ${(data.tags || []).join(", ") || "-"}`;

    setPortrait(data.image_url || null);
    if (data.comfy_status === "queued" && data.session_id) {
      void pollImageStatus(data.session_id, data.face);
    } else {
      stopImagePolling();
    }

    history.push({ role: "user", content: message });
    history.push({ role: "assistant", content: data.reply });
    if (history.length > 20) {
      history.splice(0, history.length - 20);
    }
  } catch (error) {
    replyEl.textContent = `오류: ${error.message}`;
  }

  messageEl.value = "";
  messageEl.focus();
});
