/**
 * Shared UK/EN i18n for the stakeholder GitHub Pages site.
 * Preference: localStorage key `hromada-docs-lang` (`uk` | `en`).
 *
 * Usage:
 *   window.PAGE_I18N = { uk: {…}, en: {…} };
 *   <script src="assets/i18n.js"></script>
 *   Mark copy with data-i18n / data-i18n-html; optional key `doc.title`.
 */
(function (global) {
  var STORAGE_KEY = "hromada-docs-lang";
  var dict = { uk: {}, en: {} };
  var listeners = [];

  function normalize(lang) {
    return lang === "en" ? "en" : "uk";
  }

  function getLang() {
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "en" || stored === "uk") return stored;
    } catch (e) { /* ignore */ }
    return "uk";
  }

  function persist(lang) {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) { /* ignore */ }
  }

  function mergeDict(next) {
    if (!next) return;
    dict = {
      uk: Object.assign({}, dict.uk, next.uk || {}),
      en: Object.assign({}, dict.en, next.en || {})
    };
  }

  function t(key) {
    var lang = getLang();
    if (dict[lang] && dict[lang][key] != null) return dict[lang][key];
    if (dict.uk && dict.uk[key] != null) return dict.uk[key];
    return key;
  }

  function apply(nextDict) {
    if (nextDict) mergeDict(nextDict);
    var lang = getLang();
    document.documentElement.lang = lang;
    var d = dict[lang] || {};

    if (d["doc.title"] != null) {
      document.title = d["doc.title"];
    }

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (key && d[key] != null) el.textContent = d[key];
    });

    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var key = el.getAttribute("data-i18n-html");
      if (key && d[key] != null) el.innerHTML = d[key];
    });

    document.querySelectorAll("[data-i18n-aria]").forEach(function (el) {
      var key = el.getAttribute("data-i18n-aria");
      if (key && d[key] != null) el.setAttribute("aria-label", d[key]);
    });
  }

  function setLang(lang) {
    lang = normalize(lang);
    if (lang === getLang() && document.documentElement.lang === lang) {
      apply();
      return;
    }
    persist(lang);
    document.documentElement.lang = lang;
    apply();
    var detail = { lang: lang };
    document.dispatchEvent(new CustomEvent("hromada-lang", { detail: detail }));
    listeners.forEach(function (fn) {
      try { fn(lang); } catch (e) { /* ignore */ }
    });
  }

  function onChange(fn) {
    if (typeof fn === "function") listeners.push(fn);
  }

  function boot() {
    try {
      var q = new URLSearchParams(location.search).get("lang");
      if (q === "en" || q === "uk") persist(normalize(q));
    } catch (e) { /* ignore */ }
    if (global.PAGE_I18N) apply(global.PAGE_I18N);
    else document.documentElement.lang = getLang();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.HromadaI18n = {
    getLang: getLang,
    setLang: setLang,
    t: t,
    apply: apply,
    onChange: onChange
  };
})(window);
