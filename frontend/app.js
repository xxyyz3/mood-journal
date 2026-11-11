(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const LS = {
    baseUrl: "mj_base_url",
    token: "mj_token",
    chatSession: "mj_chat_session",
    ragSession: "mj_rag_session",
    userId: "mj_user_id",
  };

  const els = {
    baseUrl: $("baseUrl"),
    connPill: $("connPill"),
    connStatus: $("connStatus"),
    healthBtn: $("healthBtn"),
    saveConnBtn: $("saveConnBtn"),
    username: $("username"),
    password: $("password"),
    loginBtn: $("loginBtn"),
    clearTokenBtn: $("clearTokenBtn"),
    loginStatus: $("loginStatus"),
    jwtPayload: $("jwtPayload"),
    chatSession: $("chatSession"),
    chatNewSession: $("chatNewSession"),
    chatClear: $("chatClear"),
    chatMessages: $("chatMessages"),
    chatInput: $("chatInput"),
    chatSend: $("chatSend"),
    chatStop: $("chatStop"),
    ragSession: $("ragSession"),
    ragNewSession: $("ragNewSession"),
    ragUserId: $("ragUserId"),
    ragClear: $("ragClear"),
    ragMessages: $("ragMessages"),
    ragInput: $("ragInput"),
    ragSend: $("ragSend"),
    ragStop: $("ragStop"),
  };

  function newSessionId(prefix) {
    return `${prefix}_${Date.now().toString(36)}`;
  }

  const state = {
    baseUrl: localStorage.getItem(LS.baseUrl) || "http://127.0.0.1:8000",
    token: localStorage.getItem(LS.token) || "",
    chatSession: localStorage.getItem(LS.chatSession) || newSessionId("chat"),
    ragSession: localStorage.getItem(LS.ragSession) || newSessionId("rag"),
    userId: localStorage.getItem(LS.userId) || "user_001",
    busy: { chat: false, rag: false },
    controllers: { chat: null, rag: null },
  };

  const panels = {
    chat: {
      messages: () => els.chatMessages,
      input: () => els.chatInput,
      sendBtn: () => els.chatSend,
      stopBtn: () => els.chatStop,
      url: () => baseUrl() + "/chat/stream",
      build: (text) => ({ message: text, session_id: state.chatSession }),
    },
    rag: {
      messages: () => els.ragMessages,
      input: () => els.ragInput,
      sendBtn: () => els.ragSend,
      stopBtn: () => els.ragStop,
      url: () => baseUrl() + "/ask/stream",
      build: (text) => ({
        question: text,
        session_id: state.ragSession,
        user_id: state.userId,
      }),
    },
  };

  /* ---------------- 基础工具 ---------------- */

  function baseUrl() {
    return state.baseUrl.trim().replace(/\/+$/, "");
  }

  function setStatus(el, message, kind = "") {
    el.textContent = message || "";
    el.className = "status" + (kind ? " " + kind : "");
  }

  function persistToken() {
    if (state.token) {
      localStorage.setItem(LS.token, state.token);
    } else {
      localStorage.removeItem(LS.token);
    }
    updateConnPill();
  }

  function tokenPayload() {
    return state.token ? decodeJwt(state.token) : null;
  }

  function tokenExpired() {
    const payload = tokenPayload();
    return Boolean(
      payload &&
        typeof payload.exp === "number" &&
        payload.exp * 1000 <= Date.now()
    );
  }

  function updateConnPill() {
    if (!state.token) {
      els.connPill.textContent = "未登录";
      els.connPill.classList.remove("ok");
      return;
    }
    if (tokenExpired()) {
      els.connPill.textContent = "登录已过期";
      els.connPill.classList.remove("ok");
      return;
    }
    els.connPill.textContent = "已登录";
    els.connPill.classList.add("ok");
  }

  function scrollToBottom(container) {
    container.scrollTop = container.scrollHeight;
  }

  function addBubble(container, role, text) {
    const empty = container.querySelector(".empty");
    if (empty) empty.remove();

    const wrap = document.createElement("div");
    wrap.className = "msg " + role;

    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = role === "user" ? "你" : "AI";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    wrap.append(label, bubble);
    container.appendChild(wrap);
    scrollToBottom(container);
    return bubble;
  }

  function resetMessages(container, placeholder) {
    container.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = placeholder;
    container.appendChild(empty);
  }

  function decodeJwt(token) {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    try {
      const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
      const binary = atob(padded);
      const bytes = Array.prototype.map.call(
        binary,
        (c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0")
      );
      return JSON.parse(decodeURIComponent(bytes.join("")));
    } catch (_) {
      return null;
    }
  }

  function autoGrow(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }

  function readyError() {
    if (!baseUrl()) return "请先在左侧填写后端地址";
    if (!state.token) return "尚未登录：请先在左侧登录并获取 JWT。";
    if (tokenExpired()) return "登录已过期：请重新点击「登录并获取 JWT」。";
    return null;
  }

  /* ---------------- 流式请求 ---------------- */

  async function streamPost({ url, payload, signal, onChunk }) {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + state.token,
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!resp.ok) {
      const raw = await resp.text();
      let detail = raw;
      try {
        const data = JSON.parse(raw);
        if (data && data.detail) {
          detail =
            typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(data.detail);
        }
      } catch (_) {
        /* 保留原始文本 */
      }
      const err = new Error(`HTTP ${resp.status}：${detail || "无响应内容"}`);
      err.status = resp.status;
      throw err;
    }

    if (!resp.body) {
      throw new Error("当前浏览器不支持读取流式响应");
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let received = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      if (chunk) {
        received += chunk.length;
        onChunk(chunk);
      }
    }

    const tail = decoder.decode();
    if (tail) {
      received += tail.length;
      onChunk(tail);
    }

    return received;
  }

  /* ---------------- 登录 ---------------- */

  async function login() {
    const username = els.username.value.trim();
    const password = els.password.value;

    if (!username || !password) {
      setStatus(els.loginStatus, "请输入用户名和密码", "error");
      return;
    }

    els.loginBtn.disabled = true;
    els.jwtPayload.classList.add("hidden");
    setStatus(els.loginStatus, "正在请求 /auth/token …", "pending");

    try {
      const resp = await fetch(baseUrl() + "/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });

      const raw = await resp.text();
      let data = null;
      try {
        data = JSON.parse(raw);
      } catch (_) {
        /* 非 JSON 响应 */
      }

      if (!resp.ok) {
        const detail =
          data && data.detail
            ? typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(data.detail)
            : raw;
        setStatus(
          els.loginStatus,
          `登录失败 · HTTP ${resp.status}：${detail || "无响应内容"}`,
          "error"
        );
        return;
      }

      if (!data || !data.access_token) {
        setStatus(els.loginStatus, "登录响应中没有 access_token", "error");
        return;
      }

      state.token = data.access_token;
      persistToken();

      setStatus(
        els.loginStatus,
        `登录成功 · HTTP ${resp.status} · token_type=${data.token_type || "bearer"} · JWT 已自动保存`,
        "success"
      );

      const payload = decodeJwt(data.access_token);
      if (payload) {
        const shown = Object.assign({}, payload);
        if (typeof shown.exp === "number") {
          shown.exp_local = new Date(shown.exp * 1000).toLocaleString();
        }
        els.jwtPayload.textContent = JSON.stringify(shown, null, 2);
        els.jwtPayload.classList.remove("hidden");
      }
    } catch (err) {
      setStatus(
        els.loginStatus,
        "请求失败：" + err.message + "（检查后端是否启动、地址与 CORS 配置）",
        "error"
      );
    } finally {
      els.loginBtn.disabled = false;
    }
  }

  /* ---------------- 发送 / 停止 ---------------- */

  async function send(kind) {
    const panel = panels[kind];
    if (state.busy[kind]) return;

    const input = panel.input();
    const text = input.value.trim();
    if (!text) return;

    const container = panel.messages();
    const problem = readyError();
    if (problem) {
      addBubble(container, "ai", problem).classList.add("error");
      return;
    }

    input.value = "";
    autoGrow(input);

    addBubble(container, "user", text);
    const bubble = addBubble(container, "ai", "");
    bubble.classList.add("pending");

    const controller = new AbortController();
    state.controllers[kind] = controller;
    state.busy[kind] = true;
    setBusyUI(kind, true);

    let gotBytes = 0;

    try {
      const received = await streamPost({
        url: panel.url(),
        payload: panel.build(text),
        signal: controller.signal,
        onChunk: (chunk) => {
          if (gotBytes === 0) bubble.classList.remove("pending");
          gotBytes += chunk.length;
          bubble.textContent += chunk;
          scrollToBottom(container);
        },
      });

      bubble.classList.remove("pending");
      if (!received) bubble.textContent = "[空回复：流式响应未返回内容]";
    } catch (err) {
      bubble.classList.remove("pending");
      bubble.classList.add("error");

      if (err.name === "AbortError") {
        bubble.textContent = (bubble.textContent || "") + "\n[已手动停止]";
      } else {
        let message = "请求失败：" + err.message;
        if (err.status === 401) {
          message +=
            "\n提示：Token 缺失、无效或已过期，请重新点击左侧「登录并获取 JWT」后再试。";
        }
        bubble.textContent = message;
      }
    } finally {
      bubble.classList.remove("pending");
      state.busy[kind] = false;
      state.controllers[kind] = null;
      setBusyUI(kind, false);
      scrollToBottom(container);
    }
  }

  function setBusyUI(kind, busy) {
    const panel = panels[kind];
    panel.sendBtn().disabled = busy;
    panel.stopBtn().disabled = !busy;
    panel.input().disabled = false;
  }

  function stop(kind) {
    const controller = state.controllers[kind];
    if (controller) controller.abort();
  }

  /* ---------------- 事件绑定 ---------------- */

  function bindInputSync(el, key, stateKey, transform) {
    el.value = state[stateKey];
    const save = () => {
      const value = transform ? transform(el.value) : el.value;
      state[stateKey] = value;
      if (key) localStorage.setItem(key, value);
      updateConnPill();
    };
    el.addEventListener("input", save);
    el.addEventListener("change", save);
  }

  els.baseUrl.value = state.baseUrl;
  els.baseUrl.addEventListener("change", () => {
    state.baseUrl = els.baseUrl.value.trim().replace(/\/+$/, "");
    localStorage.setItem(LS.baseUrl, state.baseUrl);
    els.baseUrl.value = state.baseUrl;
    updateConnPill();
  });

  els.saveConnBtn.addEventListener("click", () => {
    state.baseUrl = els.baseUrl.value.trim().replace(/\/+$/, "");
    localStorage.setItem(LS.baseUrl, state.baseUrl);
    els.baseUrl.value = state.baseUrl;
    updateConnPill();
    setStatus(els.connStatus, "后端地址已保存到浏览器 localStorage", "success");
  });

  els.healthBtn.addEventListener("click", async () => {
    if (!baseUrl()) {
      setStatus(els.connStatus, "请先填写后端地址", "error");
      return;
    }
    setStatus(els.connStatus, "正在请求 " + baseUrl() + "/health …", "pending");
    try {
      const resp = await fetch(baseUrl() + "/health");
      const text = await resp.text();
      setStatus(
        els.connStatus,
        resp.ok
          ? `连接正常 · HTTP ${resp.status} · ${text}`
          : `健康检查失败 · HTTP ${resp.status} · ${text}`,
        resp.ok ? "success" : "error"
      );
    } catch (err) {
      setStatus(
        els.connStatus,
        "无法连接后端：" + err.message + "（确认服务已启动、端口正确）",
        "error"
      );
    }
  });

  els.loginBtn.addEventListener("click", login);
  els.password.addEventListener("keydown", (e) => {
    if (e.key === "Enter") login();
  });

  els.clearTokenBtn.addEventListener("click", () => {
    state.token = "";
    persistToken();
    els.jwtPayload.classList.add("hidden");
    setStatus(els.loginStatus, "已退出登录，Token 已清除", "");
  });

  bindInputSync(els.chatSession, LS.chatSession, "chatSession");
  bindInputSync(els.ragSession, LS.ragSession, "ragSession");
  bindInputSync(els.ragUserId, LS.userId, "userId");

  els.chatNewSession.addEventListener("click", () => {
    state.chatSession = newSessionId("chat");
    els.chatSession.value = state.chatSession;
    localStorage.setItem(LS.chatSession, state.chatSession);
    resetMessages(els.chatMessages, "已开启新会话，发送一条消息开始测试。");
  });

  els.ragNewSession.addEventListener("click", () => {
    state.ragSession = newSessionId("rag");
    els.ragSession.value = state.ragSession;
    localStorage.setItem(LS.ragSession, state.ragSession);
    resetMessages(els.ragMessages, "已开启新会话，提一个关于“她”的问题开始测试。");
  });

  els.chatClear.addEventListener("click", () =>
    resetMessages(els.chatMessages, "发送一条消息，测试流式聊天。")
  );
  els.ragClear.addEventListener("click", () =>
    resetMessages(els.ragMessages, "提一个关于“她”的问题，测试 RAG 流式回答。")
  );

  els.chatSend.addEventListener("click", () => send("chat"));
  els.ragSend.addEventListener("click", () => send("rag"));
  els.chatStop.addEventListener("click", () => stop("chat"));
  els.ragStop.addEventListener("click", () => stop("rag"));

  function bindComposer(input, kind) {
    input.addEventListener("input", () => autoGrow(input));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        send(kind);
      }
    });
  }

  bindComposer(els.chatInput, "chat");
  bindComposer(els.ragInput, "rag");

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.toggle("active", t === tab));
      const target = tab.dataset.tab;
      $("panel-chat").classList.toggle("active", target === "chat");
      $("panel-rag").classList.toggle("active", target === "rag");
    });
  });

  updateConnPill();
  setInterval(updateConnPill, 30_000);
  els.chatInput.focus();
})();
