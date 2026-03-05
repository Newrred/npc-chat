let sessionId = localStorage.getItem("npc_session_id") || "";

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

function showImage(url) {
  if (!url) {
    heroine.removeAttribute("src");
    heroine.style.display = "none";
    placeholder.style.display = "block";
    return;
  }
  heroine.src = `${url}${url.includes("?") ? "&" : "?"}_=${Date.now()}`;
  heroine.style.display = "block";
  placeholder.style.display = "none";
}

function setMeta(data) {
  const aff = Number.isFinite(Number(data.affection_total)) ? data.affection_total : 0;
  const tags = (data.tags || []).join(", ") || "-";
  const flags = (data.flags || []).join(", ") || "-";
  const memo = data.memory_1line || "-";
  const comfy = data.comfy_status || (comfyToggle.checked ? "on" : "off");
  metaEl.textContent = `호감도: ${aff} | tags: ${tags} | flags: ${flags} | memo: ${memo} | comfy: ${comfy}`;
}

if (!CHAT_API_URL) {
  replyEl.textContent = "config.js에서 NPC_API_BASE_URL을 설정하세요.";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
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
    const res = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId || null,
        message,
        history,
        comfy_on: comfyToggle.checked,
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status} ${errText}`.trim());
    }

    const data = await res.json();
    if (data.session_id) {
      sessionId = data.session_id;
      localStorage.setItem("npc_session_id", sessionId);
    }

    replyEl.textContent = data.reply || "(빈 응답)";
    faceChip.textContent = `face: ${data.face || "neutral"}`;
    setMeta(data);
    showImage(data.image_url || "");

    history.push({ role: "user", content: message });
    history.push({ role: "assistant", content: data.reply || "" });
    if (history.length > 20) {
      history.splice(0, history.length - 20);
    }
  } catch (err) {
    replyEl.textContent = "오류가 났어. 서버 로그 확인해봐.";
    metaEl.textContent = String(err);
  } finally {
    input.disabled = false;
    input.value = "";
    input.focus();
  }
});

input.focus();
