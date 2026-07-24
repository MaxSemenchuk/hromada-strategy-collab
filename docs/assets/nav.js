(function () {
  var PAGES = [
    { href: "index.html", id: "home", label: "О проєкті" },
    { href: "matches.html", id: "matches", label: "Кандидати" },
    { href: "funds.html", id: "funds", label: "Фонди" },
    { href: "mss-pin-matching-graph.html", id: "map", label: "Карта МСС" },
    { href: "outreach.html", id: "outreach", label: "Outreach" }
  ];

  var script = document.currentScript;
  var active = (script && script.getAttribute("data-active")) || "home";

  function fileName(path) {
    var parts = (path || "").split("/");
    return parts[parts.length - 1] || "index.html";
  }

  var here = fileName(location.pathname);
  if (here === "" || here === "/") here = "index.html";

  PAGES.forEach(function (p) {
    if (fileName(p.href) === here) active = p.id;
  });

  var nav = document.createElement("nav");
  nav.className = "site-nav";
  nav.setAttribute("aria-label", "Розділи сайту");

  var brand = document.createElement("a");
  brand.className = "brand";
  brand.href = "index.html";
  brand.innerHTML = 'W3I <span>Матчинг громад</span>';
  nav.appendChild(brand);

  var toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "menu-toggle";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-controls", "site-nav-links");
  toggle.textContent = "Меню";
  nav.appendChild(toggle);

  var spacer = document.createElement("div");
  spacer.className = "spacer";
  nav.appendChild(spacer);

  var links = document.createElement("div");
  links.className = "nav-links";
  links.id = "site-nav-links";

  PAGES.forEach(function (p) {
    var a = document.createElement("a");
    a.href = p.href;
    a.textContent = p.label;
    if (p.id === active) {
      a.className = "active";
      a.setAttribute("aria-current", "page");
    }
    links.appendChild(a);
  });

  var repo = document.createElement("a");
  repo.href = "https://github.com/MaxSemenchuk/hromada-strategy-collab";
  repo.target = "_blank";
  repo.rel = "noopener";
  repo.textContent = "GitHub";
  links.appendChild(repo);

  nav.appendChild(links);

  toggle.addEventListener("click", function () {
    var open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  document.body.classList.add("has-site-nav");
  document.body.insertBefore(nav, document.body.firstChild);
})();
