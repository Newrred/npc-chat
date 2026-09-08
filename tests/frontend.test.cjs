const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = readFileSync(resolve(__dirname, "../frontend/app.js"), "utf8");

function mount(fetch, configured = true, options = {}) {
  const nodes = new Map();
  const stored = options.stored || new Map();
  const network = { onLine: options.online !== false };
  const events = {};
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
      style: {}, dataset: {}, listeners: {}, value: "", checked: false, disabled: false,
      textContent: "", src: "",
      children: [],
      appendChild(child) { this.children.push(child); },
      insertBefore(child) { this.children.push(child); },
      addEventListener(name, fn) { this.listeners[name] = fn; },
      removeAttribute(name) { delete this[name]; },
      setAttribute(name, value) { this[name] = value; },
      focus() {},
      showModal() { this.open = true; },
      close() { this.open = false; },
      querySelectorAll() { return this.children.filter(child => child.className?.startsWith("message-row")).map(child => ({remove: () => {this.children = this.children.filter(item => item !== child);}})); },
      querySelector() { return node("submit"); },
    });
    return nodes.get(id);
  }
  const context = vm.createContext({
    window: { location: { hash: options.hash || "" }, ...(configured ? { NPC_API_BASE_URL: "http://127.0.0.1:8000" } : {}), ...options.config, addEventListener: (name, fn) => { events[name] = fn; } },
    navigator: network,
    document: { getElementById: node, createElement: () => node(Symbol()) },
    localStorage: { getItem: (key) => stored.get(key), setItem: (key, value) => stored.set(key, value), removeItem: (key) => stored.delete(key) },
    crypto: require("node:crypto").webcrypto,
    fetch: (url, opts) => url.includes("/api/conversation?") && !options.realHistory ? Promise.resolve({ok: true, json: async () => ({items: [], before: null})}) : url.endsWith("/api/session") && !options.realSession ? Promise.resolve({ok: true, json: async () => ({session_id: "session-one", profile_id: "profile-one"})}) : fetch(url, opts), AbortController, setTimeout, clearTimeout,
  });
  vm.runInContext(source, context);
  return { node, stored, network, events, submit: () => node("chatForm").listeners.submit({ preventDefault() {} }) };
}

test("neutral portrait loads and missing faces eventually show a placeholder", () => {
  const ui = mount(() => { throw Error("Unexpected network"); });
  const portrait = ui.node("heroine");
  assert.equal(portrait.src, "./faces/neutral.png");
  portrait.listeners.error();
  assert.equal(portrait.style.display, "none");
  assert.equal(ui.node("placeholder").style.display, "block");
});

test("chat shows Korean, persists session, falls back to existing face, and prevents duplicate submit", async () => {
  let resolveRequest;
  const requests = [];
  const ui = mount((url, options) => {
    requests.push({ url, body: JSON.parse(options.body) });
    return new Promise((resolve) => { resolveRequest = resolve; });
  });
  ui.node("messageInput").value = "안녕";
  const pending = ui.submit();
  assert.equal(ui.node("submit").disabled, true);
  assert.equal(ui.node("typingIndicator").hidden, false);
  assert.equal(ui.node("chatForm").dataset.state, "sending");
  assert.equal(ui.node("reply").textContent, "");
  await ui.submit();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "http://127.0.0.1:8000/api/chat");
  assert.equal(requests[0].body.message, "안녕");
  resolveRequest({ ok: true, json: async () => ({
    session_id: "session-one", reply: "반가워. 오늘은 어땠어?", face: "happy",
    affection_total: 2, tags: ["기쁨"], comfy_status: "disabled",
  }) });
  await pending;
  assert.equal(ui.node("reply").textContent, "반가워. 오늘은 어땠어?");
  assert.equal(ui.stored.get("npc_session_id"), "session-one");
  assert.match(ui.node("meta").textContent, /호감도: 2/);
  assert.equal(ui.node("heroine").src, "./faces/happy.png");
  ui.node("heroine").listeners.error();
  assert.equal(ui.node("heroine").src, "./faces/smiling.png");
  assert.equal(ui.node("submit").disabled, false);
  assert.equal(ui.node("messageInput").disabled, false);
  assert.equal(ui.node("typingIndicator").hidden, true);
  assert.equal(ui.node("chatThread").children.length, 2);
});

test("failed generated portrait falls back to static face", async () => {
  const ui = mount(async () => ({ ok: true, json: async () => ({
    session_id: "session-one", reply: "다시 왔네.", face: "shy smile",
    comfy_status: "generated", image_url: "https://images.example/portrait.png",
  }) }));
  ui.node("messageInput").value = "안녕";
  await ui.submit();
  assert.equal(ui.node("heroine").dataset.kind, "generated");
  ui.node("heroine").listeners.error();
  assert.equal(ui.node("heroine").src, "./faces/shy_smile.png");
});

test("HTTP errors restore controls without automatically retrying", async () => {
  let calls = 0;
  const ui = mount(async () => { calls++; return { ok: false, status: 503, text: async () => "Unavailable" }; });
  ui.node("messageInput").value = "안녕";
  await ui.submit();
  assert.equal(calls, 1);
  assert.equal(ui.node("chatForm").dataset.state, "retryable_error");
  assert.equal(ui.node("reply").textContent, "");
  assert.equal(ui.node("messageInput").value, "안녕");
  assert.equal(ui.node("submit").disabled, false);
  assert.equal(ui.node("messageInput").disabled, false);
});

test("empty API configuration uses same-origin without an absolute backend URL", async () => {
  let requested;
  const ui = mount(async (url) => {
    requested = url;
    return { ok: true, json: async () => ({ reply: "반가워.", face: "neutral", comfy_status: "disabled" }) };
  }, false);
  ui.node("messageInput").value = "안녕";
  await ui.submit();
  assert.equal(requested, "/api/chat");
  assert.equal(ui.node("reply").textContent, "반가워.");
});


test("lost response retry preserves ID and payload; debug scores hidden by default", async () => {
  const requests = [];
  const ui = mount(async (_url, options) => {
    requests.push(JSON.parse(options.body));
    if (requests.length === 1) throw Error("lost response");
    return {ok: true, json: async () => ({reply: "반가워", face: "neutral", comfy_status: "disabled"})};
  });
  ui.node("messageInput").value = "안녕";
  await ui.submit();
  assert.ok(ui.stored.get("npc_pending_turn"));
  assert.equal(ui.node("typingIndicator").hidden, true);
  ui.node("comfyToggle").checked = true;
  await ui.submit();
  assert.deepEqual(requests[0], requests[1]);
  assert.ok(requests[0].client_turn_id);
  assert.equal(ui.stored.has("npc_pending_turn"), false);
  assert.equal(ui.node("meta").hidden, true);
  assert.equal(ui.node("chatThread").children.length, 2);
});


test("offline preserves draft and reconnect never sends automatically", async () => {
  let calls = 0;
  const ui = mount(async () => { calls++; }, true, { online: false });
  ui.node("messageInput").value = "초안";
  await ui.submit();
  assert.equal(ui.node("chatForm").dataset.state, "offline");
  assert.equal(ui.node("messageInput").value, "초안");
  ui.network.onLine = true;
  ui.events.online();
  assert.equal(calls, 0);
  assert.equal(ui.node("chatForm").dataset.state, "idle");
});

test("non retryable error offers explicit edit and preserves last character reply", async () => {
  const ui = mount(async () => ({ok: false, status: 422, json: async () => ({error: {
    code: "INPUT_TOO_LONG", message: "메시지를 줄여 주세요.", retryable: false }})}));
  ui.node("reply").textContent = "이전 대사";
  ui.node("messageInput").value = "긴 입력";
  await ui.submit();
  assert.equal(ui.node("chatForm").dataset.state, "non_retryable_error");
  assert.equal(ui.node("reply").textContent, "이전 대사");
  assert.equal(ui.node("editButton").hidden, false);
  ui.node("editButton").listeners.click();
  assert.equal(ui.node("messageInput").readOnly, false);
  assert.equal(ui.stored.has("npc_pending_turn"), false);
});

test("reload retains pending identity and skips session recreation", async () => {
  const pending = {message: "안녕", client_turn_id: "same", session_id: "old-session", profile_id: "old-profile", comfy_on: false};
  const stored = new Map([["npc_pending_turn", JSON.stringify(pending)]]);
  let sent;
  const ui = mount(async (url, opts) => {
    assert.match(url, /api\/chat$/);
    sent = JSON.parse(opts.body);
    return {ok: true, json: async () => ({reply: "안녕", face: "neutral"})};
  }, true, {stored, realSession: true});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.node("retryButton").hidden, false);
  await ui.node("retryButton").listeners.click();
  assert.deepEqual(sent, pending);
});

test("waiting state and debug reason codes are separate from dialogue", async () => {
  let done;
  const ui = mount(() => new Promise(resolve => { done = resolve; }));
  ui.node("messageInput").value = "테스트";
  const work = ui.submit();
  await new Promise(resolve => setTimeout(resolve, 550));
  assert.equal(ui.node("chatForm").dataset.state, "waiting_for_model");
  done({ok: true, json: async () => ({reply: "반가워", relationship: {values: {trust: 31}, delta: {trust: 1}, reason_codes: ["base:support"]}})});
  await work;
  assert.match(ui.node("meta").textContent, /base:support/);
  assert.equal(ui.node("meta").hidden, true);
  ui.node("debugToggle").checked = true;
  ui.node("debugToggle").listeners.change();
  assert.equal(ui.node("meta").hidden, false);
});



test("missing profile recovery starts a new identity only on explicit click", async () => {
  const stored = new Map([["npc_session_id", "missing"], ["npc_profile_id", "gone"]]);
  let requests = [];
  const ui = mount(async (url, opts) => {
    requests.push(JSON.parse(opts.body));
    return {ok: false, status: 404, json: async () => ({error: {code: "PROFILE_NOT_FOUND", message: "대화를 찾을 수 없습니다.", retryable: false}})};
  }, true, {stored, realSession: true});
  await new Promise(resolve => setImmediate(resolve));
  ui.node("messageInput").value = "다시 안녕";
  await ui.submit();
  assert.equal(stored.get("npc_profile_id"), "gone");
  assert.equal(ui.node("editButton").textContent, "새 대화 시작");
  ui.node("editButton").listeners.click();
  assert.equal(stored.has("npc_profile_id"), false);
  assert.equal(requests.length, 1);
});


test("account mismatch clears browser identity only after explicit reconnect", async () => {
  const stored = new Map([["npc_session_id", "alice-session"], ["npc_profile_id", "alice-profile"]]);
  const ui = mount(async () => ({ok: false, status: 403, json: async () => ({error: {
    code: "ACCESS_DENIED", message: "이 대화에 접근할 수 없습니다.", retryable: false
  }})}), true, {stored, realSession: true});
  await new Promise(resolve => setImmediate(resolve));
  ui.node("messageInput").value = "안녕";
  await ui.submit();
  assert.equal(stored.get("npc_profile_id"), "alice-profile");
  assert.equal(ui.node("editButton").textContent, "현재 계정으로 연결");
  ui.node("editButton").listeners.click();
  assert.equal(stored.has("npc_profile_id"), false);
  assert.equal(stored.has("npc_session_id"), false);
});

test("video connects, minimizes, ends, and never starts an inference request", () => {
  const ui = mount(() => { throw Error("Video controls must not call the API"); });
  assert.equal(ui.node("chatRoom").hidden, true);
  ui.node("openYuiRoom").listeners.click();
  assert.equal(ui.node("conversationList").hidden, true);
  assert.equal(ui.node("videoStage").hidden, true);
  ui.node("joinVideo").listeners.click();
  assert.equal(ui.node("videoStage").hidden, false);
  assert.equal(ui.node("videoStatus").textContent, "화면 연결 중…");
  ui.node("heroine").listeners.load();
  assert.equal(ui.node("videoStatus").textContent, "함께 보는 중");
  ui.node("resizeVideo").listeners.click();
  assert.equal(ui.node("videoStage").dataset.compact, "true");
  ui.node("endVideo").listeners.click();
  assert.equal(ui.node("videoStage").hidden, true);
  assert.equal(ui.node("startVideo").hidden, false);
  assert.equal(ui.node("messageInput").disabled, false);
});

test("leaving while generating retains draft and response, and marks the room unread", async () => {
  let resolveRequest;
  const ui = mount(() => new Promise(resolve => { resolveRequest = resolve; }));
  ui.node("openYuiRoom").listeners.click();
  ui.node("messageInput").value = "안녕";
  const pending = ui.submit();
  await new Promise(resolve => setImmediate(resolve));
  ui.node("backToList").listeners.click();
  assert.equal(ui.node("chatRoom").hidden, true);
  assert.equal(ui.node("videoStage").hidden, true);
  resolveRequest({ok: true, json: async () => ({reply: "어서 와!", face: "neutral"})});
  await pending;
  assert.equal(ui.node("roomPreview").textContent, "어서 와!");
  assert.equal(ui.node("roomUnread").hidden, false);
  ui.node("messageInput").value = "작성 중인 말";
  ui.node("openYuiRoom").listeners.click();
  assert.equal(ui.node("chatThread").children.length, 2);
  assert.equal(ui.node("messageInput").value, "작성 중인 말");
  assert.equal(ui.node("roomUnread").hidden, true);
});

test("room deep link opens chat and portrait failure is not shown as connected", () => {
  const ui = mount(() => { throw Error("Unexpected network"); }, true, {hash: "#chat/yui"});
  assert.equal(ui.node("chatRoom").hidden, false);
  ui.node("joinVideo").listeners.click();
  ui.node("heroine").listeners.error();
  assert.equal(ui.node("videoStatus").textContent, "화면을 불러오지 못했어요");
  assert.equal(ui.node("chatRoom").hidden, false);
});

test("messenger retains multiple turns as text and stops typing after each reply", async () => {
  const ui = mount(async () => ({ ok: true, json: async () => ({reply: "<b>반가워</b>", face: "neutral"}) }));
  for (const message of ["안녕", "<img src=x onerror=alert(1)>"]) {
    ui.node("messageInput").value = message;
    await ui.submit();
    assert.equal(ui.node("typingIndicator").hidden, true);
  }
  const rows = ui.node("chatThread").children;
  assert.equal(rows.length, 4);
  assert.equal(rows[2].children[0].textContent, "<img src=x onerror=alert(1)>");
  assert.equal(rows[3].children[1].textContent, "<b>반가워</b>");
});

test("request timeout preserves the ID and keeps the prior character reply", async () => {
  const ui = mount((_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener("abort", () => { const e = new Error("timeout"); e.name = "AbortError"; reject(e); });
  }), true, {config: {NPC_REQUEST_TIMEOUT_MS: 1000}});
  ui.node("reply").textContent = "이전 대사";
  ui.node("messageInput").value = "안녕";
  await ui.submit();
  assert.equal(ui.node("chatForm").dataset.state, "retryable_error");
  assert.equal(ui.node("reply").textContent, "이전 대사");
  assert.ok(JSON.parse(ui.stored.get("npc_pending_turn")).client_turn_id);
  assert.equal(ui.node("retryButton").hidden, false);
});


test("configured hidden relationship display never reveals exact developer values", () => {
  const ui = mount(() => {}, true, {config: {NPC_RELATIONSHIP_DISPLAY: "hidden"}});
  assert.equal(ui.node("debugControls").hidden, true);
  ui.node("debugToggle").checked = true;
  ui.node("debugToggle").listeners.change();
  assert.equal(ui.node("meta").hidden, true);
});

test("refresh restores server messages and reconciles a committed pending response without sending", async () => {
  const turn = {turn_id: "committed", user_message: "저장된 질문", reply: "저장된 답변", face: "happy"};
  const stored = new Map([["npc_session_id", "s"], ["npc_profile_id", "p"], ["npc_pending_turn", JSON.stringify({message: turn.user_message, client_turn_id: turn.turn_id, session_id: "s", profile_id: "p"})]]);
  let calls = 0;
  const ui = mount(async url => { assert.match(url, /api\/conversation\?/); calls++; return {ok: true, json: async () => ({items:[turn], before:null})}; }, true, {stored, realHistory: true});
  assert.equal(ui.node("submit").disabled, true);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.node("chatThread").children.length, 2);
  assert.equal(ui.node("roomPreview").textContent, turn.reply);
  assert.equal(ui.node("heroine").src, "./faces/happy.png");
  assert.equal(stored.has("npc_pending_turn"), false);
  assert.equal(ui.node("submit").disabled, false);
  await ui.node("reloadHistory").listeners.click();
  assert.equal(ui.node("chatThread").children.length, 2);
  assert.equal(calls, 2);
});

test("history outage blocks a blind new turn and offers retry without erasing identity", async () => {
  const stored = new Map([["npc_session_id", "s"], ["npc_profile_id", "p"]]);
  const ui = mount(async () => ({ok:false, status:503, json:async()=>({error:{message:"저장소 오프라인"}})}), true, {stored, realHistory:true});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.node("submit").disabled, true);
  assert.equal(ui.node("reloadHistory").hidden, false);
  assert.equal(stored.get("npc_session_id"), "s");
});

test("leave cancel preserves conversation; confirmed leave clears server identity and bubbles", async () => {
  let resets = 0;
  const ui = mount(async url => {
    if(url.endsWith("/reset")){resets++;return {ok:true,json:async()=>({closed:true})};}
    return {ok:true,json:async()=>({reply:"반가워",face:"neutral"})};
  });
  ui.node("openYuiRoom").listeners.click();
  ui.node("messageInput").value="안녕"; await ui.submit();
  ui.node("leaveRoom").listeners.click();
  assert.equal(ui.node("leaveDialog").open,true);
  ui.node("cancelLeave").listeners.click();
  assert.equal(resets,0); assert.equal(ui.node("chatThread").children.length,2);
  ui.node("leaveRoom").listeners.click();
  await ui.node("confirmLeave").listeners.click();
  assert.equal(resets,1); assert.equal(ui.node("chatThread").children.length,0);
  assert.equal(ui.stored.has("npc_session_id"),false);
  assert.equal(ui.node("conversationList").hidden,false);
  assert.equal(ui.node("leaveDialog").open,false);
});

test("failed leave preserves bubbles and identity and keeps confirmation open", async () => {
  const stored=new Map([["npc_session_id","s"],["npc_profile_id","p"]]);
  const ui=mount(async()=>({ok:false,status:503,json:async()=>({error:{message:"저장 실패"}})}),true,{stored});
  await new Promise(resolve=>setImmediate(resolve));
  ui.node("leaveRoom").listeners.click();
  await ui.node("confirmLeave").listeners.click();
  assert.equal(stored.get("npc_session_id"),"s");
  assert.equal(ui.node("leaveDialog").open,true);
  assert.match(ui.node("leaveStatus").textContent,/완료를 확인하지 못/);
});
