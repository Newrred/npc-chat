let sessionId = localStorage.getItem("npc_session_id") || "";
let imagePollController = null;
let currentFace = "neutral";

const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const replyEl = document.getElementById("reply");
const metaEl = document.getElementById("meta");
const faceChip = document.getElementById("faceChip");
const heroine = document.getElementById("heroine");
const placeholder = document.getElementById("placeholder");
const comfyToggle = document.getElementById("comfyToggle");

const history = [];
const API_BASE_URL = String(window.NPC_API_BASE_URL || "").replace(/\/$/, "");
const CHAT_API_URL = API_BASE_URL ? `${API_BASE_URL}/api/chat` : "";
const IMAGE_STATUS_API_URL = API_BASE_URL ? `${API_BASE_URL}/api/image/status` : "";
const FACE_ASSET_BASE_URL = String(window.NPC_FACE_ASSET_BASE_URL || "./faces").replace(/\/$/, "");
const FACE_ASSET_EXT = String(window.NPC_FACE_EXT || "png").replace(/^\./, "");
const POLL_INTERVAL_MS = Math.max(500, Number(window.NPC_POLL_INTERVAL_MS) || 2000);
const POLL_MAX_ATTEMPTS = Math.max(1, Number(window.NPC_POLL_MAX_ATTEMPTS) || 10);

function stopImagePolling() {
  if (!imagePollController) return;
  imagePollController.abort();
  imagePollController = null;
}

function faceToSlug(face) {
  return String(face || "neutral").trim().toLowerCase().replace(/\s+/g, "_");
}

function getBaseFaceUrl(face) {
  return `${FACE_ASSET_BASE_URL}/${faceToSlug(face)}.${FACE_ASSET_EXT}`;
}

function showImage(url, { bustCache = false, kind = "base" } = {}) {
  if (!url) {
    heroine.removeAttribute("src");
    heroine.dataset.kind = "none";
    heroine.style.display = "none";
    placeholder.style.display = "block";
    return;
  }
  const finalUrl = bustCache ? `${url}${url.includes("?") ? "&" : "?"}_=${Date.now()}` : url;
  heroine.dataset.kind = kind;
  heroine.src = finalUrl;
  heroine.style.display = "block";
  placeholder.style.display = "none";
}

function showBaseFace(face) {
  currentFace = face || "neutral";
  showImage(getBaseFaceUrl(currentFace), { kind: "base" });
}

function setMeta(data) {
  const aff = Number.isFinite(Number(data.affection_total)) ? Number(data.affection_total) : 0;
  const tags = (data.tags || []).join(", ") || "-";
  const flags = (data.flags || []).join(", ") || "-";
  const memo = data.memory_1line || "-";
  const comfy = data.comfy_status || (comfyToggle.checked ? "on" : "off");
  const src = data.image_source || "none";
  metaEl.textContent = `호감도: ${aff} | tags: ${tags} | flags: ${flags} | memo: ${memo} | comfy: ${comfy} | img: ${src}`;
}

async function pollImageStatus(face) {
  if (!IMAGE_STATUS_API_URL || !sessionId) return;
  stopImagePolling();

  const controller = new AbortController();
  imagePollController = controller;

  for (let i = 0; i < POLL_MAX_ATTEMPTS; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    if (controller.signal.aborted) return;

    const statusUrl = `${IMAGE_STATUS_API_URL}?session_id=${encodeURIComponent(sessionId)}&face=${encodeURIComponent(face)}`;
    try {
      const response = await fetch(statusUrl, { signal: controller.signal });
      if (!response.ok) continue;

      const data = await response.json();
      if (data.comfy_status === "generated" && data.image_url) {
        showImage(data.image_url, { bustCache: true, kind: "generated" });
        return;
      }
      if (data.comfy_status === "error") {
        showBaseFace(face);
        return;
      }
    } catch (_error) {
      if (controller.signal.aborted) return;
    }
  }
}

heroine.addEventListener("error", () => {
  if (heroine.dataset.kind === "generated") {
    showBaseFace(currentFace);
    return;
  }
  heroine.removeAttribute("src");
  heroine.dataset.kind = "none";
  heroine.style.display = "none";
  placeholder.style.display = "block";
});

if (!CHAT_API_URL) {
  replyEl.textContent = "config.js에서 NPC_API_BASE_URL을 설정하세요.";
}

showBaseFace("neutral");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  if (!CHAT_API_URL) {
    replyEl.textContent = "백엔드 주소가 비어 있습니다. config.js를 확인하세요.";
    return;
  }

  input.disabled = true;
  replyEl.textContent = "생각 중...";
  metaEl.textContent = "응답 생성 중";

  try {
    const response = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId || null,
        message,
        history,
        comfy_on: comfyToggle.checked,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`HTTP ${response.status} ${errText}`.trim());
    }

    const data = await response.json();
    if (data.session_id) {
      sessionId = data.session_id;
      localStorage.setItem("npc_session_id", sessionId);
    }

    const face = data.face || "neutral";
    replyEl.textContent = data.reply || "(빈 응답)";
    faceChip.textContent = `face: ${face} (${data.comfy_status || "n/a"})`;
    setMeta(data);

    // Base face is always local frontend asset.
    showBaseFace(face);

    // Generated image can overlay when ready.
    if (data.comfy_status === "generated" && data.image_url) {
      showImage(data.image_url, { bustCache: true, kind: "generated" });
      stopImagePolling();
    } else if (data.comfy_status === "queued") {
      void pollImageStatus(face);
    } else {
      stopImagePolling();
    }

    history.push({ role: "user", content: message });
    history.push({ role: "assistant", content: data.reply || "" });
    if (history.length > 20) {
      history.splice(0, history.length - 20);
    }
  } catch (error) {
    replyEl.textContent = "오류가 발생했어. 서버 로그를 확인해줘.";
    metaEl.textContent = String(error);
  } finally {
    input.disabled = false;
    input.value = "";
    input.focus();
  }
});

input.focus();
