(function () {
  var COPY = {
    uk: {
      title: "Спитати корпус",
      statusOff: "чат локальний · yarn mcp-test-ui",
      statusOn: "підключено",
      statusWait: "з’єднуюсь…",
      empty:
        "Гібридний пошук: SQL по релізу, цитати зі стратегій, сторінки цього сайту. Гіпотези — не факт реєстру.",
      ph: "Питання про дані або сторінку…",
      send: "Надіслати",
      close: "Закрити",
      open: "Відкрити чат",
      settings: "Ключ і модель",
      key: "OpenAI API key",
      model: "Модель",
      hint: "Ключ лише в цьому браузері. Залиште порожнім, якщо сервер має OPENAI_API_KEY у .env.",
      needKey: "Вставте ключ у налаштуваннях або запустіть сервер з .env.",
      down:
        "Чат працює локально. У корені репозиторію: yarn mcp-test-ui — потім відкрийте http://localhost:5175/",
      thinking: "Шукаю в корпусі…",
      s1: "Хто пише про воду / річки?",
      s2: "Що показує ця сторінка сайту?",
      s3: "З ким могла б кооперувати Ніжинська?"
    },
    en: {
      title: "Ask the corpus",
      statusOff: "local chat · yarn mcp-test-ui",
      statusOn: "connected",
      statusWait: "connecting…",
      empty:
        "Hybrid search: SQL over the release, quotes from strategies, and this site’s pages. Hypotheses — not registry fact.",
      ph: "Ask about the data or this page…",
      send: "Send",
      close: "Close",
      open: "Open chat",
      settings: "Key and model",
      key: "OpenAI API key",
      model: "Model",
      hint: "Key stays in this browser. Leave blank if the server has OPENAI_API_KEY in .env.",
      needKey: "Paste a key in settings, or run the server with .env.",
      down:
        "Chat is local. In the repo root run yarn mcp-test-ui, then open http://localhost:5175/",
      thinking: "Searching the corpus…",
      s1: "Who writes about water / rivers?",
      s2: "What does this site page show?",
      s3: "Who could Nizhyn cooperate with?"
    }
  };

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
    return "http://127.0.0.1:5175";
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
    var st = document.getElementById("hcwStatus");
    st.textContent = connected ? t("statusOn") : t("statusWait");
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
    turn.className = "hcw-turn " + role + (role === "assistant" && text.indexOf("⚠") === 0 ? " error" : "");
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
    var status = document.getElementById("hcwStatus");
    status.textContent = t("statusWait");
    try {
      var res = await fetch(apiBase() + "/api/status");
      var data = await res.json();
      connected = Boolean(data.connected);
      hasServerKey = Boolean(data.hasServerKey);
      status.textContent = connected ? t("statusOn") : t("statusOff");
    } catch (e) {
      connected = false;
      status.textContent = t("statusOff");
    }
  }

  async function send() {
    var message = input.value.trim();
    if (!message) return;
    var apiKey = keyInput.value.trim();
    if (!apiKey && !hasServerKey) {
      if (!connected) addBubble("assistant", "⚠ " + t("down"));
      else addBubble("assistant", "⚠ " + t("needKey"));
      settings.classList.add("is-open");
      return;
    }
    addBubble("user", message);
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    var thinking = addBubble("assistant", t("thinking"));
    try {
      var page = (document.querySelector(".site-nav a.active") || {}).getAttribute
        ? document.querySelector(".site-nav a.active").getAttribute("data-nav-id")
        : "";
      var res = await fetch(apiBase() + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          apiKey: apiKey,
          model: modelInput.value || "gpt-4o-mini",
          message: message,
          sessionId: sessionId(),
          page: page || location.pathname,
          lang: lang()
        })
      });
      var data = await res.json();
      thinking.remove();
      if (!res.ok) addBubble("assistant", "⚠ " + (data.error || t("down")));
      else addBubble("assistant", data.reply, data.toolCalls);
    } catch (err) {
      thinking.remove();
      addBubble("assistant", "⚠ " + (connected ? err.message : t("down")));
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
