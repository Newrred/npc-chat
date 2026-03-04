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

function setComfyBadge(isOn) {
  statusBadge.textContent = `Comfy: ${isOn ? "on" : "off"}`;
}

comfyToggle.addEventListener("change", () => setComfyBadge(comfyToggle.checked));
setComfyBadge(false);

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
        comfy_on: comfyToggle.checked,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    replyEl.textContent = data.reply;
    faceEl.textContent = `face: ${data.face}`;
    tagsEl.textContent = `tags: ${(data.tags || []).join(", ") || "-"}`;

    setPortrait(data.image_url || null);

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
