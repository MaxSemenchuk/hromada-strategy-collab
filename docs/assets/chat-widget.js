(function () {
  var COPY = {
    uk: {
      title: "Спитати корпус",
      statusOff: "корпус у браузері",
      statusOn: "підключено",
      statusWait: "з’єднуюсь…",
      empty:
        "Пошук по стратегіях і сторінках цього сайту. Гіпотези — не факт реєстру. Для чату потрібен ключ OpenAI (шестерня).",
      ph: "Питання про дані або сторінку…",
      send: "Надіслати",
      close: "Закрити",
      open: "Відкрити чат",
      settings: "Ключ і модель",
      key: "OpenAI API key",
      model: "Модель",
      hint: "Ключ лише в цьому браузері. На GitHub Pages вставте ключ сюди — сервер не потрібен.",
      needKey: "Вставте OpenAI API key у шестерні (лишається в цьому браузері).",
      down: "Не вдалося звернутися до OpenAI. Перевірте ключ у шестерні.",
      thinking: "Шукаю в корпусі…",
      loading: "Завантажую корпус…",
      s1: "Хто пише про воду / річки?",
      s2: "Що показує ця сторінка сайту?",
      s3: "З ким могла б кооперувати Ніжинська?"
    },
    en: {
      title: "Ask the corpus",
      statusOff: "in-browser corpus",
      statusOn: "connected",
      statusWait: "connecting…",
      empty:
        "Search over strategies and this site’s pages. Hypotheses — not registry fact. Paste an OpenAI key in the gear to chat.",
      ph: "Ask about the data or this page…",
      send: "Send",
      close: "Close",
      open: "Open chat",
      settings: "Key and model",
      key: "OpenAI API key",
      model: "Model",
      hint: "Key stays in this browser. On GitHub Pages paste it here — no local server needed.",
      needKey: "Paste an OpenAI API key in the gear (stored in this browser only).",
      down: "Could not reach OpenAI. Check the key in settings.",
      thinking: "Searching the corpus…",
      loading: "Loading corpus…",
      s1: "Who writes about water / rivers?",
      s2: "What does this site page show?",
      s3: "Who could Nizhyn cooperate with?"
    }
  };

  var STOP = {
    хто: 1, що: 1, як: 1, які: 1, який: 1, яка: 1, яке: 1, для: 1, про: 1,
    при: 1, або: 1, та: 1, і: 1, й: 1, в: 1, у: 1, на: 1, з: 1, зі: 1, із: 1,
    по: 1, це: 1, чи: 1, the: 1, a: 1, an: 1, of: 1, for: 1, and: 1, or: 1,
    to: 1, in: 1, on: 1, with: 1, who: 1, what: 1, which: 1, where: 1, how: 1,
    about: 1, from: 1, this: 1, page: 1, site: 1, shows: 1, показує: 1,
    сторінка: 1, сайту: 1, ця: 1
  };

  var STATIC_SYSTEM =
    "You are the in-site assistant for «Партнери для МСС». Product unit = candidate IMC/МСС " +
    "agreement (pair · theme · one of 5 Law 1508-VII forms). Discovery signals are not legal forms. " +
    "Use search_chunks for quotes, themes, named rivers/landfills, and what the website says. " +
    "Cite hromada name + field, or a docs/*.html path. Never invent quotes. " +
    "Matching score is a hypothesis unless known=true. Twinning / Interreg / Law 3668 are not МСС forms. " +
    "Goals coverage is a sample (~394/1463) — do not generalise to all Ukraine. " +
    "No SQL in this mode. Answer in the user's language. Keep answers short. 3–7 citations max.";

  var STATIC_TOOLS = [
    {
      type: "function",
      function: {
        name: "search_chunks",
        description:
          "Full-text search over strategy fields and stakeholder site pages. " +
          "Fields: goals_strategic, goals_operational, strengths, challenges, projects, " +
          "mss_intent, mss_candidate, site_page, site_doc, twinning, intl_agreement, interreg, donors.",
        parameters: {
          type: "object",
          properties: {
            query: { type: "string" },
            field: { type: "string", description: "Optional field or comma-separated fields" },
            oblast: { type: "string" },
            limit: { type: "integer" }
          },
          required: ["query"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "get_context",
        description: "Methodology caveats to read before interpreting matches.",
        parameters: { type: "object", properties: {} }
      }
    }
  ];

  function lang() {
    return (window.HromadaI18n && window.HromadaI18n.getLang()) || "uk";
  }
  function t(key) {
    var L = COPY[lang()] || COPY.uk;
    return L[key] || COPY.uk[key] || key;
  }

  function apiBase() {
    try {
      var stored = localStorage.getItem("hromada_chat_api");
      if (stored) return stored.replace(/\/$/, "");
    } catch (e) { /* ignore */ }
    if (location.port === "5175") return "";
    if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      return "http://127.0.0.1:5175";
    }
    return "";
  }

  function sessionId() {
    try {
      var id = sessionStorage.getItem("hromada_chat_session");
      if (id) return id;
      id = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
      sessionStorage.setItem("hromada_chat_session", id);
      return id;
    } catch (e) {
      return "anon";
    }
  }

  var css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = "assets/chat-widget.css";
  document.head.appendChild(css);

  var root = document.createElement("div");
  root.className = "hcw-root";
  root.innerHTML =
    '<button type="button" class="hcw-fab" id="hcwFab" aria-expanded="false">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
      "</svg>" +
    "</button>" +
    '<section class="hcw-panel" id="hcwPanel" role="dialog" aria-labelledby="hcwTitle" hidden>' +
      '<div class="hcw-head">' +
        "<div><h2 id=\"hcwTitle\"></h2><span class=\"hcw-status\" id=\"hcwStatus\"></span></div>" +
        '<button type="button" class="hcw-icon-btn" id="hcwGear" aria-label=""></button>' +
        '<button type="button" class="hcw-icon-btn" id="hcwClose" aria-label=""></button>' +
      "</div>" +
      '<div class="hcw-settings" id="hcwSettings">' +
        '<label for="hcwKey" id="hcwKeyLabel"></label>' +
        '<input type="password" id="hcwKey" autocomplete="off" />' +
        '<label for="hcwModel" id="hcwModelLabel"></label>' +
        '<input id="hcwModel" list="hcwModels" />' +
        '<datalist id="hcwModels">' +
          '<option value="gpt-4o-mini"></option>' +
          '<option value="gpt-4o"></option>' +
          '<option value="gpt-5"></option>' +
        "</datalist>" +
        '<p class="hcw-hint" id="hcwHint"></p>' +
      "</div>" +
      '<div class="hcw-log" id="hcwLog"></div>' +
      '<div class="hcw-composer">' +
        '<textarea id="hcwInput" rows="1"></textarea>' +
        '<button type="button" class="hcw-send" id="hcwSend"></button>' +
      "</div>" +
    "</section>";
  document.body.appendChild(root);

  var fab = document.getElementById("hcwFab");
  var panel = document.getElementById("hcwPanel");
  var log = document.getElementById("hcwLog");
  var input = document.getElementById("hcwInput");
  var sendBtn = document.getElementById("hcwSend");
  var gear = document.getElementById("hcwGear");
  var settings = document.getElementById("hcwSettings");
  var keyInput = document.getElementById("hcwKey");
  var modelInput = document.getElementById("hcwModel");
  var hasServerKey = false;
  var connected = false;
  var pingDone = false;
  var staticIndex = null;
  var indexPromise = null;
  var staticMessages = null;

  gear.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  document.getElementById("hcwClose").innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  try {
    keyInput.value = localStorage.getItem("hromada_mcp_openai_key") || "";
    modelInput.value = localStorage.getItem("hromada_chat_model") || "gpt-4o-mini";
  } catch (e) {
    modelInput.value = "gpt-4o-mini";
  }

  keyInput.addEventListener("input", function () {
    try { localStorage.setItem("hromada_mcp_openai_key", keyInput.value); } catch (e) { /* ignore */ }
  });
  modelInput.addEventListener("change", function () {
    try { localStorage.setItem("hromada_chat_model", modelInput.value); } catch (e) { /* ignore */ }
  });

  function setStatus() {
    var st = document.getElementById("hcwStatus");
    if (connected) st.textContent = t("statusOn");
    else if (staticIndex) st.textContent = t("statusOff");
    else st.textContent = t("statusWait");
  }

  function applyCopy() {
    document.getElementById("hcwTitle").textContent = t("title");
    document.getElementById("hcwKeyLabel").textContent = t("key");
    document.getElementById("hcwModelLabel").textContent = t("model");
    document.getElementById("hcwHint").textContent = t("hint");
    input.placeholder = t("ph");
    sendBtn.textContent = t("send");
    fab.setAttribute("aria-label", t("open"));
    document.getElementById("hcwClose").setAttribute("aria-label", t("close"));
    gear.setAttribute("aria-label", t("settings"));
    setStatus();
    var empty = log.querySelector(".hcw-empty");
    if (empty) renderEmpty();
  }

  function renderEmpty() {
    log.innerHTML = "";
    var wrap = document.createElement("div");
    wrap.className = "hcw-empty";
    wrap.textContent = t("empty");
    var chips = document.createElement("div");
    chips.className = "hcw-chips";
    ["s1", "s2", "s3"].forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "hcw-chip";
      b.textContent = t(k);
      b.addEventListener("click", function () {
        input.value = t(k);
        send();
      });
      chips.appendChild(b);
    });
    wrap.appendChild(chips);
    log.appendChild(wrap);
  }

  function openPanel() {
    panel.hidden = false;
    panel.classList.add("is-open");
    fab.setAttribute("aria-expanded", "true");
    loadIndex();
    input.focus();
  }
  function closePanel() {
    panel.hidden = true;
    panel.classList.remove("is-open");
    fab.setAttribute("aria-expanded", "false");
  }

  fab.addEventListener("click", openPanel);
  document.getElementById("hcwClose").addEventListener("click", closePanel);
  gear.addEventListener("click", function () {
    settings.classList.toggle("is-open");
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel.classList.contains("is-open")) closePanel();
  });

  function addBubble(role, text, toolCalls) {
    var empty = log.querySelector(".hcw-empty");
    if (empty) empty.remove();
    var turn = document.createElement("div");
    turn.className = "hcw-turn " + role + (role === "assistant" && String(text).indexOf("⚠") === 0 ? " error" : "");
    var bubble = document.createElement("div");
    bubble.className = "hcw-bubble";
    if (role === "assistant") {
      var esc = String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      esc = esc.replace(/`([^`]+)`/g, "<code>$1</code>");
      esc = esc.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      esc = esc.replace(/\n/g, "<br>");
      bubble.innerHTML = esc;
    } else {
      bubble.textContent = text;
    }
    turn.appendChild(bubble);
    if (toolCalls && toolCalls.length) {
      var tools = document.createElement("div");
      tools.className = "hcw-tools";
      tools.textContent = toolCalls.map(function (c) { return c.name; }).join(" · ");
      turn.appendChild(tools);
    }
    log.appendChild(turn);
    log.scrollTop = log.scrollHeight;
    return turn;
  }

  async function ping() {
    var base = apiBase();
    if (location.protocol === "https:" && base.indexOf("http://") === 0) {
      pingDone = true;
      connected = false;
      setStatus();
      return;
    }
    try {
      var res = await fetch(base + "/api/status");
      var data = await res.json();
      connected = Boolean(data.connected);
      hasServerKey = Boolean(data.hasServerKey);
    } catch (e) {
      connected = false;
      hasServerKey = false;
    }
    pingDone = true;
    setStatus();
  }

  function loadIndex() {
    if (indexPromise) return indexPromise;
    indexPromise = fetch("assets/chat-index.json")
      .then(function (r) {
        if (!r.ok) throw new Error("index " + r.status);
        return r.json();
      })
      .then(function (data) {
        staticIndex = data;
        setStatus();
        return data;
      })
      .catch(function (err) {
        indexPromise = null;
        throw err;
      });
    return indexPromise;
  }

  function tokenize(q) {
    return String(q || "")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, " ")
      .split(/\s+/)
      .filter(function (tok) { return tok.length >= 2 && !STOP[tok]; });
  }

  function searchLocal(opts) {
    var chunks = (staticIndex && staticIndex.chunks) || [];
    var tokens = tokenize(opts.query);
    if (opts.query && /вод[ауиіо]|річк|басейн|каналіз|водо/i.test(opts.query)) {
      tokens = tokens.concat(["вода", "річка", "басейн", "водопостачання"]);
    }
    if (opts.query && /тпв|смітт|полігон|відход/i.test(opts.query)) {
      tokens = tokens.concat(["тпв", "відходи", "сміття", "полігон"]);
    }
    var fields = (opts.field || "")
      .split(",")
      .map(function (f) { return f.trim(); })
      .filter(Boolean);
    var oblast = (opts.oblast || "").toLowerCase();
    var limit = Math.min(Math.max(opts.limit || 12, 1), 30);
    var hits = [];
    for (var i = 0; i < chunks.length; i++) {
      var c = chunks[i];
      if (fields.length && fields.indexOf(c.f) < 0) continue;
      if (oblast && String(c.o || "").toLowerCase().indexOf(oblast) < 0) continue;
      var hay = ((c.t || "") + " " + (c.n || "")).toLowerCase();
      var score = 0;
      for (var j = 0; j < tokens.length; j++) {
        if (hay.indexOf(tokens[j]) >= 0) score += 1;
      }
      if (!tokens.length && opts.query) {
        if (hay.indexOf(String(opts.query).toLowerCase()) >= 0) score = 1;
      }
      if (score > 0) hits.push({ score: score, c: c });
    }
    hits.sort(function (a, b) { return b.score - a.score; });
    return {
      hit_count: Math.min(hits.length, limit),
      hits: hits.slice(0, limit).map(function (h) {
        return {
          name: h.c.n,
          katottg: h.c.k || "",
          oblast: h.c.o || "",
          field: h.c.f,
          source: h.c.s || "",
          text: h.c.t
        };
      })
    };
  }

  function runLocalTool(name, args) {
    if (name === "get_context") {
      return JSON.stringify({
        context: (staticIndex && staticIndex.context) || STATIC_SYSTEM,
        chunks: staticIndex && staticIndex.n
      });
    }
    if (name === "search_chunks") {
      return JSON.stringify(searchLocal(args || {}));
    }
    return JSON.stringify({ error: "unknown tool " + name });
  }

  async function runStaticLoop(apiKey, model, userMessage) {
    if (!staticMessages) {
      staticMessages = [{ role: "system", content: STATIC_SYSTEM }];
    }
    staticMessages.push({ role: "user", content: userMessage });
    var toolCalls = [];
    for (var round = 0; round < 8; round++) {
      var res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + apiKey
        },
        body: JSON.stringify({
          model: model,
          messages: staticMessages,
          tools: STATIC_TOOLS,
          tool_choice: "auto"
        })
      });
      var data = await res.json();
      if (!res.ok) {
        var msg = (data.error && data.error.message) || ("HTTP " + res.status);
        if (res.status === 401) msg = t("needKey");
        if (res.status === 429) msg = "Rate limited — wait a moment and retry.";
        throw new Error(msg);
      }
      var choice = data.choices && data.choices[0];
      var message = choice && choice.message;
      if (!message) throw new Error("Empty OpenAI response");
      staticMessages.push(message);
      var calls = message.tool_calls || [];
      if (!calls.length) {
        return { reply: message.content || "(no text)", toolCalls: toolCalls };
      }
      for (var i = 0; i < calls.length; i++) {
        var tc = calls[i];
        var fn = tc.function || {};
        var parsed = {};
        try { parsed = fn.arguments ? JSON.parse(fn.arguments) : {}; } catch (e) { parsed = {}; }
        var out = runLocalTool(fn.name, parsed);
        toolCalls.push({ name: fn.name, input: parsed, output: out, isError: false });
        staticMessages.push({
          role: "tool",
          tool_call_id: tc.id,
          content: out
        });
      }
    }
    return { reply: "(stopped after tool round-trips)", toolCalls: toolCalls };
  }

  async function send() {
    var message = input.value.trim();
    if (!message) return;

    if (!pingDone) await ping();
    if (!connected) {
      try { await loadIndex(); } catch (e) { /* keep going */ }
    }

    var apiKey = keyInput.value.trim();
    if (!connected && !apiKey) {
      addBubble("assistant", "⚠ " + t("needKey"));
      settings.classList.add("is-open");
      return;
    }
    if (connected && !apiKey && !hasServerKey) {
      addBubble("assistant", "⚠ " + t("needKey"));
      settings.classList.add("is-open");
      return;
    }

    addBubble("user", message);
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    var thinking = addBubble("assistant", connected ? t("thinking") : t("loading"));

    var pageEl = document.querySelector(".site-nav a.active");
    var page = pageEl ? pageEl.getAttribute("data-nav-id") : location.pathname;

    try {
      if (connected) {
        thinking.firstChild.textContent = t("thinking");
        var res = await fetch(apiBase() + "/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            apiKey: apiKey,
            model: modelInput.value || "gpt-4o-mini",
            message: message,
            sessionId: sessionId(),
            page: page,
            lang: lang()
          })
        });
        var data = await res.json();
        thinking.remove();
        if (!res.ok) addBubble("assistant", "⚠ " + (data.error || t("down")));
        else addBubble("assistant", data.reply, data.toolCalls);
      } else {
        if (!staticIndex) await loadIndex();
        thinking.firstChild.textContent = t("thinking");
        var framed = "[page: " + page + "; lang: " + lang() + "]\n" + message;
        var out = await runStaticLoop(apiKey, modelInput.value || "gpt-4o-mini", framed);
        thinking.remove();
        addBubble("assistant", out.reply, out.toolCalls);
      }
    } catch (err) {
      thinking.remove();
      addBubble("assistant", "⚠ " + (err && err.message ? err.message : t("down")));
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
  input.addEventListener("input", function () {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 110) + "px";
  });

  document.addEventListener("hromada-lang", applyCopy);
  if (window.HromadaI18n && window.HromadaI18n.onChange) window.HromadaI18n.onChange(applyCopy);

  applyCopy();
  renderEmpty();
  ping();
})();
