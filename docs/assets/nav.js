(function () {
  var PAGES = [
    {
      href: "index.html",
      id: "home",
      label: { uk: "Про проєкт", en: "About" }
    },
    {
      href: "matches.html",
      id: "matches",
      label: { uk: "Кандидати", en: "Candidates" }
    },
    {
      href: "funds.html",
      id: "funds",
      label: { uk: "Фонди", en: "Funds" }
    },
    {
      href: "resources.html",
      id: "resources",
      label: { uk: "Ресурси", en: "Resources" }
    },
    {
      href: "mss-pin-matching-graph.html",
      id: "map",
      label: { uk: "Мапа угод МСС", en: "IMC map" }
    }
  ];

  var BRAND = {
    uk: 'W3I <span>Партнери для МСС</span>',
    en: 'W3I <span>IMC partners</span>'
  };
  var MENU = { uk: "Меню", en: "Menu" };
  var NAV_ARIA = { uk: "Розділи сайту", en: "Site sections" };
  var LANG_ARIA = { uk: "Мова", en: "Language" };

  var script = document.currentScript;
  var active = (script && script.getAttribute("data-active")) || "home";

  function fileName(path) {
    var parts = (path || "").split("/");
    return parts[parts.length - 1] || "index.html";
  }

  function lang() {
    return (window.HromadaI18n && window.HromadaI18n.getLang()) || "uk";
  }

  var here = fileName(location.pathname);
  if (here === "" || here === "/") here = "index.html";

  PAGES.forEach(function (p) {
    if (fileName(p.href) === here) active = p.id;
  });

  var nav = document.createElement("nav");
  nav.className = "site-nav";
  nav.setAttribute("aria-label", NAV_ARIA[lang()] || NAV_ARIA.uk);

  var brand = document.createElement("a");
  brand.className = "brand";
  brand.href = "index.html";
  brand.innerHTML = BRAND[lang()] || BRAND.uk;
  nav.appendChild(brand);

  var toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "menu-toggle";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-controls", "site-nav-links");
  toggle.textContent = MENU[lang()] || MENU.uk;
  nav.appendChild(toggle);

  var spacer = document.createElement("div");
  spacer.className = "spacer";
  nav.appendChild(spacer);

  var links = document.createElement("div");
  links.className = "nav-links";
  links.id = "site-nav-links";

  var linkEls = [];
  PAGES.forEach(function (p) {
    var a = document.createElement("a");
    a.href = p.href;
    a.textContent = (p.label[lang()] || p.label.uk);
    a.setAttribute("data-nav-id", p.id);
    if (p.id === active) {
      a.className = "active";
      a.setAttribute("aria-current", "page");
    }
    links.appendChild(a);
    linkEls.push({ el: a, page: p });
  });

  var langSwitch = document.createElement("div");
  langSwitch.className = "lang-switch";
  langSwitch.setAttribute("role", "group");
  langSwitch.setAttribute("aria-label", LANG_ARIA[lang()] || LANG_ARIA.uk);

  function makeLangBtn(code, label) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lang-btn";
    btn.setAttribute("data-lang", code);
    btn.textContent = label;
    btn.addEventListener("click", function () {
      if (window.HromadaI18n) window.HromadaI18n.setLang(code);
      else {
        try { localStorage.setItem("hromada-docs-lang", code); } catch (e) { /* ignore */ }
        location.reload();
      }
    });
    return btn;
  }

  var btnUk = makeLangBtn("uk", "UK");
  var btnEn = makeLangBtn("en", "EN");
  langSwitch.appendChild(btnUk);
  langSwitch.appendChild(btnEn);
  links.appendChild(langSwitch);

  var repo = document.createElement("a");
  repo.href = "https://github.com/MaxSemenchuk/hromada-strategy-collab";
  repo.target = "_blank";
  repo.rel = "noopener";
  repo.textContent = "GitHub";
  links.appendChild(repo);

  nav.appendChild(links);

  function syncLangUi(current) {
    current = current || lang();
    brand.innerHTML = BRAND[current] || BRAND.uk;
    toggle.textContent = MENU[current] || MENU.uk;
    nav.setAttribute("aria-label", NAV_ARIA[current] || NAV_ARIA.uk);
    langSwitch.setAttribute("aria-label", LANG_ARIA[current] || LANG_ARIA.uk);
    linkEls.forEach(function (item) {
      item.el.textContent = item.page.label[current] || item.page.label.uk;
    });
    btnUk.classList.toggle("active", current === "uk");
    btnEn.classList.toggle("active", current === "en");
    btnUk.setAttribute("aria-pressed", current === "uk" ? "true" : "false");
    btnEn.setAttribute("aria-pressed", current === "en" ? "true" : "false");
  }

  syncLangUi();

  if (window.HromadaI18n && window.HromadaI18n.onChange) {
    window.HromadaI18n.onChange(syncLangUi);
  }
  document.addEventListener("hromada-lang", function (ev) {
    syncLangUi(ev.detail && ev.detail.lang);
  });

  toggle.addEventListener("click", function () {
    var open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  document.body.classList.add("has-site-nav");
  document.body.insertBefore(nav, document.body.firstChild);
})();
