let storageError = false;
function readStored(key) {
  try { return localStorage.getItem(key) || ""; }
  catch (_) { storageError = true; return ""; }
}
let sessionId = readStored("npc_session_id");
let profileId = readStored("npc_profile_id");
let pendingTurn = null;
try {
  const saved = readStored("npc_pending_turn");
  if (saved) {
    pendingTurn = JSON.parse(saved);
    if (!pendingTurn || typeof pendingTurn.message !== "string" || typeof pendingTurn.client_turn_id !== "string") {
      pendingTurn = null;
      storageError = true;
    }
  }
} catch (_) { storageError = true; }
let imagePollController = null;
let currentFace = "neutral";
let currentBaseFaceCandidates = [];
let currentBaseFaceIndex = 0;

const form = document.getElementById("chatForm");
const submitButton = form.querySelector('button[type="submit"]');
const input = document.getElementById("messageInput");
const replyEl = document.getElementById("reply");
const chatThread = document.getElementById("chatThread");
const typingIndicator = document.getElementById("typingIndicator");
const renderedMessages = new Set();
const conversationList = document.getElementById("conversationList");
const chatRoom = document.getElementById("chatRoom");
const openYuiRoom = document.getElementById("openYuiRoom");
const roomPreview = document.getElementById("roomPreview");
const roomUnread = document.getElementById("roomUnread");
const videoStage = document.getElementById("videoStage");
const videoInvite = document.getElementById("videoInvite");
const videoStatus = document.getElementById("videoStatus");
const startVideo = document.getElementById("startVideo");
const resizeVideo = document.getElementById("resizeVideo");
const roomPresence = document.getElementById("roomPresence");
let videoOpen = false;
let videoCompact = false;

function stopVideo() {
  videoOpen = false;
  videoCompact = false;
  videoStage.hidden = true;
  videoStage.dataset.compact = "false";
  videoInvite.hidden = false;
  startVideo.hidden = false;
  roomPresence.textContent = "메시지로 함께해요";
  resizeVideo.textContent = "↙";
  resizeVideo.setAttribute("aria-label", "영상 화면 작게 보기");
}

function connectVideo() {
  if (chatRoom.hidden || videoOpen) return;
  videoOpen = true;
  videoStage.hidden = false;
  videoInvite.hidden = true;
  startVideo.hidden = true;
  const imageReady = heroine.complete && heroine.naturalWidth > 0;
  videoStatus.textContent = imageReady ? "함께 보는 중" : "화면 연결 중…";
  roomPresence.textContent = imageReady ? "캐릭터 화면 연결됨" : "캐릭터 화면 준비 중";
  // Retry a missing portrait through the existing fallback chain, without an LLM call.
  if (heroine.style.display === "none") showBaseFace(currentFace);
  document.getElementById("endVideo").focus();
}

function renderRoute() {
  const inRoom = window.location?.hash === "#chat/yui";
  conversationList.hidden = inRoom;
  chatRoom.hidden = !inRoom;
  if (inRoom) {
    roomUnread.hidden = true;
    document.getElementById("backToList").focus();
    chatThread.scrollTop = chatThread.scrollHeight;
  } else {
    stopVideo();
    openYuiRoom.focus();
  }
}

function navigateRoom(hash) {
  if (window.location) window.location.hash = hash;
  renderRoute();
}
openYuiRoom.addEventListener("click", () => navigateRoom("#chat/yui"));
document.getElementById("backToList").addEventListener("click", () => navigateRoom(""));
window.addEventListener("hashchange", renderRoute);
startVideo.addEventListener("click", connectVideo);
document.getElementById("joinVideo").addEventListener("click", connectVideo);
document.getElementById("endVideo").addEventListener("click", () => { stopVideo(); startVideo.focus(); });
resizeVideo.addEventListener("click", () => {
  videoCompact = !videoCompact;
  videoStage.dataset.compact = String(videoCompact);
  resizeVideo.textContent = videoCompact ? "↗" : "↙";
  resizeVideo.setAttribute("aria-label", videoCompact ? "영상 화면 크게 보기" : "영상 화면 작게 보기");
});
function appendMessage(role, text, turnId, anchor = typingIndicator) {
  const key = `${role}:${turnId}`;
  if (renderedMessages.has(key)) return;
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  if (role === "assistant") {
    const speaker = document.createElement("span");
    speaker.className = "speaker";
    speaker.textContent = "유이";
    row.appendChild(speaker);
  }
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  chatThread.insertBefore(row, anchor);
  renderedMessages.add(key);
  roomPreview.textContent = role === "assistant" ? text : `나: ${text}`;
  if (role === "assistant" && chatRoom.hidden) roomUnread.hidden = false;
  chatThread.scrollTop = chatThread.scrollHeight;
}
const metaEl = document.getElementById("meta");
const faceChip = document.getElementById("faceChip");
const heroine = document.getElementById("heroine");
const placeholder = document.getElementById("placeholder");
const comfyToggle = document.getElementById("comfyToggle");

const debugToggle = document.getElementById("debugToggle");
const statusEl = document.getElementById("chatStatus");
const retryButton = document.getElementById("retryButton");
const editButton = document.getElementById("editButton");
const debugEnabled = window.NPC_RELATIONSHIP_DISPLAY !== "hidden";
document.getElementById("debugControls").hidden = !debugEnabled;
metaEl.hidden = true;
faceChip.hidden = true;
debugToggle.addEventListener("change", () => {
  metaEl.hidden = faceChip.hidden = !(debugEnabled && debugToggle.checked);
});
let uiState = "idle";
let busy = false;
let missingSession = false;
function setState(state, message = "") {
  uiState = state;
  form.dataset.state = state;
  statusEl.dataset.state = state;
  statusEl.textContent = message;
  busy = state === "sending" || state === "waiting_for_model";
  if (busy) roomPreview.textContent = "유이가 답변을 입력 중이에요…";
  else if (["retryable_error", "non_retryable_error", "offline"].includes(state)) roomPreview.textContent = "메시지 전송 상태를 확인해 주세요.";
  typingIndicator.hidden = !busy;
  if (busy) chatThread.scrollTop = chatThread.scrollHeight;
  input.disabled = submitButton.disabled = comfyToggle.disabled = busy;
  document.getElementById("leaveRoom").disabled = busy;
  input.readOnly = Boolean(pendingTurn);
  retryButton.hidden = !(["retryable_error", "offline"].includes(state) && pendingTurn);
  retryButton.disabled = busy || navigator.onLine === false;
  editButton.hidden = state !== "non_retryable_error" || storageError;
}

async function readResponse(response) {
  if (response.ok) return response.json();
  let data = {};
  try { data = await response.json(); } catch (_) {}
  const error = new Error(data.error?.message || (response.status === 422 ? "입력 내용을 확인해 주세요." : "요청을 처리하지 못했습니다."));
  error.retryable = data.error?.retryable ?? (response.status >= 500 || response.status === 429);
  error.code = data.error?.code || `HTTP_${response.status}`;
  throw error;
}

async function ensureSession(signal) {
  if (pendingTurn?.session_id && pendingTurn?.profile_id) return;
  const data = await readResponse(await fetch(`${API_BASE_URL}/api/session`, {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ session_id: sessionId || null, profile_id: profileId || null }),
  }));
  if (!data.session_id || !data.profile_id) throw new Error("대화 식별자를 확인하지 못했습니다.");
  sessionId = data.session_id;
  profileId = data.profile_id;
  localStorage.setItem("npc_session_id", sessionId);
  localStorage.setItem("npc_profile_id", profileId);
}
const API_BASE_URL = String(window.NPC_API_BASE_URL || "").replace(/\/$/, "");
const CHAT_API_URL = `${API_BASE_URL}/api/chat`;
const IMAGE_STATUS_API_URL = `${API_BASE_URL}/api/image/status`;
const FACE_ASSET_BASE_URL = String(window.NPC_FACE_ASSET_BASE_URL || "./faces").replace(/\/$/, "");
const FACE_ASSET_EXT = String(window.NPC_FACE_EXT || "png").replace(/^\./, "");
const POLL_INTERVAL_MS = Math.max(500, Number(window.NPC_POLL_INTERVAL_MS) || 2000);
const POLL_MAX_ATTEMPTS = Math.max(1, Number(window.NPC_POLL_MAX_ATTEMPTS) || 10);
const FACE_FALLBACK_SLUGS = {
  crying: ["teary", "sad"],
  happy: ["smiling"],
  scared: ["confused"],
  smirk: ["smiling"],
  surprised: ["confused"],
  teary: ["crying", "sad"],
};

function stopImagePolling() {
  if (!imagePollController) return;
  imagePollController.abort();
  imagePollController = null;
}

function faceToSlug(face) {
  const slug = String(face || "neutral").trim().toLowerCase().replace(/\s+/g, "_");
  return slug === "suprised" ? "surprised" : slug;
}

function dedupeKeepOrder(items) {
  const seen = new Set();
  const out = [];
  for (const item of items) {
    if (!item || seen.has(item)) continue;
    seen.add(item);
    out.push(item);
  }
  return out;
}

function getBaseFaceUrl(face) {
  return `${FACE_ASSET_BASE_URL}/${faceToSlug(face)}.${FACE_ASSET_EXT}`;
}

function getBaseFaceCandidates(face) {
  const slug = faceToSlug(face);
  return dedupeKeepOrder([slug, ...(FACE_FALLBACK_SLUGS[slug] || []), "neutral"]);
}

function showImage(url, { bustCache = false, kind = "base" } = {}) {
  if (!url) {
    heroine.removeAttribute("src");
    heroine.dataset.kind = "none";
    heroine.style.display = "none";
    placeholder.style.display = "block";
    placeholder.textContent = "표정을 불러오지 못했어요";
    if (videoOpen) {
      videoStatus.textContent = "화면을 불러오지 못했어요";
      roomPresence.textContent = "화면을 확인해 주세요";
    }
    return;
  }

  const finalUrl = bustCache ? `${url}${url.includes("?") ? "&" : "?"}_=${Date.now()}` : url;
  heroine.dataset.kind = kind;
  heroine.src = finalUrl;
  heroine.style.display = "block";
  placeholder.style.display = "none";
}

function showBaseFaceCandidate(index) {
  const slug = currentBaseFaceCandidates[index];
  if (!slug) {
    showImage(null, { kind: "none" });
    return;
  }

  currentBaseFaceIndex = index;
  showImage(getBaseFaceUrl(slug), { kind: "base" });
}

function showBaseFace(face) {
  currentFace = face || "neutral";
  currentBaseFaceCandidates = getBaseFaceCandidates(currentFace);
  currentBaseFaceIndex = 0;
  showBaseFaceCandidate(0);
}

function setMeta(data, elapsedMs) {
  const aff = Number.isFinite(Number(data.affection_total)) ? Number(data.affection_total) : 0;
  const face = data.face || "-";
  const internal = data.internal_emotion || "-";
  const tags = (data.tags || []).join(", ") || "-";
  const flags = (data.flags || []).join(", ") || "-";
  const memo = data.memory_1line || "-";
  const comfy = data.comfy_status || (comfyToggle.checked ? "on" : "off");
  const src = data.image_source || "none";
  const scores = data.relationship ? Object.entries(data.relationship.values).map(([key, value]) =>
    `${key}: ${value} (${data.relationship.delta[key] >= 0 ? "+" : ""}${data.relationship.delta[key]})`).join(" | ") : "";
  metaEl.textContent = `응답 ${(elapsedMs / 1000).toFixed(2)}초 | 규칙: ${data.relationship?.reason_codes?.join(", ") || "-"} | ${scores} | 호감도: ${aff} | face: ${face} | internal: ${internal} | tags: ${tags} | flags: ${flags} | memo: ${memo} | comfy: ${comfy} | img: ${src}`;
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
  if (heroine.dataset.kind === "base") {
    showBaseFaceCandidate(currentBaseFaceIndex + 1);
    return;
  }

  heroine.removeAttribute("src");
  heroine.dataset.kind = "none";
  heroine.style.display = "none";
  placeholder.style.display = "block";
});

heroine.addEventListener("load", () => {
  if (videoOpen) {
    videoStatus.textContent = "함께 보는 중";
    roomPresence.textContent = "캐릭터 화면 연결됨";
  }
  if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
    heroine.animate?.([{ opacity: 0.5 }, { opacity: 1 }], { duration: 250, easing: "ease-out" });
  }
});

showBaseFace("neutral");

async function sendTurn() {
  if (busy || historyLoading || resetLoading || historyFailed) return;
  if (storageError) {
    setState("non_retryable_error", "브라우저 저장소를 사용할 수 없습니다. 저장소 설정을 확인한 뒤 새로고침해 주세요.");
    return;
  }
  const message = pendingTurn?.message || input.value.trim();
  if (!message) return;
  if (navigator.onLine === false) {
    setState("offline", "오프라인입니다. 연결이 돌아오면 다시 보내 주세요.");
    return;
  }
  stopImagePolling();
  setState("sending", "메시지를 전송하고 있습니다.");
  const began = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Math.max(1000, Number(window.NPC_REQUEST_TIMEOUT_MS) || 420000));
  let waiting;
  try {
    await ensureSession(controller.signal);
    const recovering = Boolean(pendingTurn);
    if (loadedSession !== sessionId) await loadHistory(false, controller.signal);
    if (recovering && !pendingTurn) { setState("success", "저장된 답변을 복원했습니다."); return; }
    if (!pendingTurn) pendingTurn = { message, client_turn_id: crypto.randomUUID(), comfy_on: comfyToggle.checked };
    pendingTurn.session_id ||= sessionId;
    pendingTurn.profile_id ||= profileId;
    // Persist complete identity and payload before inference, including across reloads.
    localStorage.setItem("npc_pending_turn", JSON.stringify(pendingTurn));
    appendMessage("user", pendingTurn.message, pendingTurn.client_turn_id);
    input.readOnly = true;
    waiting = setTimeout(() => setState("waiting_for_model", "답변을 기다리고 있습니다…"), 500);
    const data = await readResponse(await fetch(CHAT_API_URL, {
      method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
      body: JSON.stringify(pendingTurn),
    }));
    if (typeof data.reply !== "string" || !data.reply.trim()) throw new Error("응답을 확인하지 못했습니다.");
    clearTimeout(waiting);
    const face = faceToSlug(data.face);
    replyEl.textContent = data.reply;
    appendMessage("assistant", data.reply, pendingTurn.client_turn_id);
    faceChip.textContent = `face: ${face}`;
    setMeta(data, Date.now() - began);
    showBaseFace(face);
    if (data.comfy_status === "generated" && data.image_url) {
      showImage(data.image_url, { bustCache: true, kind: "generated" });
    } else if (data.comfy_status === "queued") {
      void pollImageStatus(face);
    }
    localStorage.removeItem("npc_pending_turn");
    pendingTurn = null;
    input.value = "";
    setState("success", "답변을 받았습니다.");
  } catch (error) {
    clearTimeout(waiting);
    missingSession = ["SESSION_NOT_FOUND", "PROFILE_NOT_FOUND", "ACCESS_DENIED"].includes(error.code);
    editButton.textContent = error.code === "ACCESS_DENIED" ? "현재 계정으로 연결" : missingSession ? "새 대화 시작" : "내용 수정";
    const offline = navigator.onLine === false;
    if (["QuotaExceededError", "SecurityError"].includes(error.name)) storageError = true;
    const retryable = !storageError && error.retryable !== false;
    const state = offline ? "offline" : retryable ? "retryable_error" : "non_retryable_error";
    const reason = storageError ? "브라우저 저장소를 확인한 뒤 새로고침해 주세요." : offline ? "오프라인입니다." : error.name === "AbortError" ? "응답 확인 시간이 초과됐습니다." : error.message;
    setState(state, reason + (retryable ? " 같은 메시지를 다시 보내 확인할 수 있습니다." : " 내용을 확인해 주세요."));
    metaEl.textContent = `오류: ${error.code || error.name}`;
    if (pendingTurn) input.value = pendingTurn.message;
  } finally {
    clearTimeout(timeout);
    clearTimeout(waiting);
    historyControls();
    if (!chatRoom.hidden) input.focus();
  }
}

form.addEventListener("submit", (event) => { event.preventDefault(); return sendTurn(); });
retryButton.addEventListener("click", () => sendTurn());
editButton.addEventListener("click", () => {
  if (busy) return;
  try {
    localStorage.removeItem("npc_pending_turn");
    pendingTurn = null;
    if (missingSession) {
      localStorage.removeItem("npc_session_id");
      localStorage.removeItem("npc_profile_id");
      sessionId = profileId = "";
      missingSession = false;
      clearDisplayedHistory();
    }
    setState("idle", "내용을 수정한 뒤 새 메시지로 보내 주세요.");
    input.focus();
  } catch (_) { setState("non_retryable_error", "저장소를 확인한 뒤 새로고침해 주세요."); }
});
window.addEventListener("offline", () => {
  if (!busy) setState("offline", "오프라인입니다. 입력은 유지됩니다.");
});
window.addEventListener("online", () => {
  if (!busy && uiState === "offline") setState(pendingTurn ? "retryable_error" : "idle", "연결이 돌아왔습니다. 직접 다시 보내 주세요.");
});
if (pendingTurn) input.value = pendingTurn.message;
setState(storageError ? "non_retryable_error" : navigator.onLine === false ? "offline" : pendingTurn ? "retryable_error" : "idle",
  storageError ? "브라우저 저장소를 확인한 뒤 새로고침해 주세요." : pendingTurn ? "완료를 확인하지 못한 메시지가 있습니다. 다시 보내 주세요." : "");
renderRoute();

// Server history is authoritative; browser storage contains identities and pending requests only.
const historyStatus = document.getElementById("historyStatus");
const reloadHistory = document.getElementById("reloadHistory");
const reconnectHistory = document.getElementById("reconnectHistory");
const olderHistory = document.getElementById("olderHistory");
const leaveDialog = document.getElementById("leaveDialog");
const confirmLeave = document.getElementById("confirmLeave");
let historyLoading = false;
let historyFailed = false;
let resetLoading = false;
let historyBefore = null;
let loadedSession = "";

function historyControls() {
  input.disabled = submitButton.disabled = busy || historyLoading || resetLoading || historyFailed;
  document.getElementById("leaveRoom").disabled = busy || historyLoading || resetLoading;
  olderHistory.disabled = reloadHistory.disabled = reconnectHistory.disabled = historyLoading || busy || resetLoading;
}
async function loadHistory(older = false, signal) {
  if (!sessionId || !profileId) return;
  historyLoading = true;
  historyControls();
  historyStatus.textContent = "대화 기록을 불러오는 중…";
  try {
    let query = `session_id=${encodeURIComponent(sessionId)}&profile_id=${encodeURIComponent(profileId)}`;
    if (older && historyBefore) query += `&before=${encodeURIComponent(historyBefore)}`;
    const controller = signal ? null : new AbortController();
    const timer = controller ? setTimeout(() => controller.abort(), 15000) : null;
    let data;
    try { data = await readResponse(await fetch(`${API_BASE_URL}/api/conversation?${query}`, { signal: signal || controller.signal, cache: "no-store" })); }
    finally { if (timer) clearTimeout(timer); }
    if (!Array.isArray(data.items)) throw Error("대화 기록을 확인하지 못했습니다.");
    const anchor = older ? chatThread.querySelector(".message-row") || typingIndicator : typingIndicator;
    const preview = roomPreview.textContent;
    const oldHeight = chatThread.scrollHeight;
    const oldTop = chatThread.scrollTop;
    for (const turn of data.items) {
      appendMessage("user", turn.user_message, turn.turn_id, anchor);
      appendMessage("assistant", turn.reply, turn.turn_id, anchor);
      if (pendingTurn?.client_turn_id === turn.turn_id) {
        localStorage.removeItem("npc_pending_turn"); pendingTurn = null; input.value = "";
      }
    }
    if (older) {
      roomPreview.textContent = preview;
      chatThread.scrollTop = oldTop + chatThread.scrollHeight - oldHeight;
    } else if (data.items.length) {
      showBaseFace(data.items[data.items.length - 1].face);
    }
    roomUnread.hidden = true;
    historyBefore = data.before;
    olderHistory.hidden = !historyBefore;
    reloadHistory.hidden = reconnectHistory.hidden = true;
    historyFailed = false;
    loadedSession = sessionId;
    historyStatus.textContent = "";
    input.readOnly = Boolean(pendingTurn);
    if (!busy) setState(pendingTurn ? "retryable_error" : "idle", pendingTurn ? "완료를 확인하지 못한 메시지가 있습니다. 다시 보내 주세요." : "");
  } catch (error) {
    historyFailed = true;
    historyStatus.textContent = error.name === "AbortError" ? "대화 기록 확인 시간이 초과됐어요." : error.message;
    reloadHistory.hidden = false;
    reconnectHistory.hidden = !["ACCESS_DENIED", "SESSION_NOT_FOUND", "PROFILE_NOT_FOUND"].includes(error.code);
    throw error;
  } finally { historyLoading = false; historyControls(); }
}
function clearDisplayedHistory() {
  chatThread.querySelectorAll(".message-row:not(.typing-row)").forEach(row => row.remove());
  renderedMessages.clear();
  loadedSession = ""; historyBefore = null; historyFailed = false;
  olderHistory.hidden = reloadHistory.hidden = reconnectHistory.hidden = true;
  historyStatus.textContent = "";
  roomPreview.textContent = "유이에게 첫 메시지를 보내보세요.";
  roomUnread.hidden = true;
  replyEl.textContent = metaEl.textContent = "";
  stopImagePolling(); showBaseFace("neutral");
}
reloadHistory.addEventListener("click", () => { if (!busy && !historyLoading) return loadHistory().catch(() => {}); });
olderHistory.addEventListener("click", () => { if (!busy && !historyLoading) return loadHistory(true).catch(() => {}); });
reconnectHistory.addEventListener("click", async () => {
  if (busy || historyLoading) return;
  try {
    for (const key of ["npc_session_id", "npc_profile_id", "npc_pending_turn"]) localStorage.removeItem(key);
    sessionId = profileId = ""; pendingTurn = null;
    clearDisplayedHistory();
    historyLoading = true; historyControls();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try { await ensureSession(controller.signal); } finally { clearTimeout(timer); }
    await loadHistory();
  } catch (error) { historyFailed = true; historyStatus.textContent = error.message; reconnectHistory.hidden = false; }
  finally { historyLoading = false; historyControls(); }
});
document.getElementById("leaveRoom").addEventListener("click", () => {
  if (busy || historyLoading || resetLoading) return;
  document.getElementById("leaveStatus").textContent = "";
  leaveDialog.showModal();
  document.getElementById("cancelLeave").focus();
});
document.getElementById("cancelLeave").addEventListener("click", () => { if (!resetLoading) leaveDialog.close(); });
leaveDialog.addEventListener("cancel", event => { if (resetLoading) event.preventDefault(); });
confirmLeave.addEventListener("click", async () => {
  if (busy || historyLoading || resetLoading) return;
  resetLoading = true; confirmLeave.disabled = true; historyControls();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    if (sessionId && profileId) await readResponse(await fetch(`${API_BASE_URL}/api/conversation/reset`, {
      method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
      body: JSON.stringify({ session_id: sessionId, profile_id: profileId }),
    }));
    for (const key of ["npc_session_id", "npc_profile_id", "npc_pending_turn"]) localStorage.removeItem(key);
    sessionId = profileId = ""; pendingTurn = null; input.value = "";
    clearDisplayedHistory(); setState("idle"); leaveDialog.close(); navigateRoom("");
  } catch (error) {
    document.getElementById("leaveStatus").textContent = "나가기 완료를 확인하지 못했어요. " + error.message + " 취소 후 새로고침해 상태를 확인해 주세요.";
  } finally { clearTimeout(timer); resetLoading = false; confirmLeave.disabled = false; historyControls(); }
});
if (sessionId && profileId && !storageError) void loadHistory().catch(() => {});
