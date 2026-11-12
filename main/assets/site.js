/* Navigation tree, filter, findings toggle, figure lightbox, and permalink copy. No dependencies. */
(function () {
  "use strict";
  var body = document.body;
  var root = body.getAttribute("data-root") || "";
  var current = body.getAttribute("data-card") || "";
  var nav = window.GUIDE_NAV || { nodes: [], extra: [] };

  // ------------------------------------------------------------ deep links on the home page
  // index.html#<card-id>, #<card-id>--s<n>, or #<page anchor> (links from InteropHub and elsewhere).
  // The query string (e.g. ?interophub=signin) is kept so the target page can continue sign-in.
  if (body.classList.contains("home") && location.hash.length > 1) {
    var target = decodeURIComponent(location.hash.slice(1));
    var ids = {};
    (function walk(ns) { ns.forEach(function (n) { if (!n.p) ids[n.i] = 1; if (n.c) walk(n.c); }); })(nav.nodes);
    var pages = nav.anchors || {};
    var st = target.match(/^(.+)--s\d+$/);
    var q = location.search;
    if (ids[target]) { location.replace(target + "/index.html" + q); return; }
    if (pages[target]) { location.replace(pages[target] + q); return; }
    if (st && ids[st[1]]) { location.replace(st[1] + "/index.html" + q + "#" + target); return; }
  }

  function store(key, value) {
    try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch (e) { return null; }
  }

  // ------------------------------------------------------------ tree
  function contains(node, id) {
    if (node.i === id) return true;
    return (node.c || []).some(function (k) { return contains(k, id); });
  }

  function badge(f) {
    if (f[0]) return '<span class="badge sev-issue" title="' + f[0] + ' issue(s)">' + f[0] + "</span>";
    if (f[1]) return '<span class="badge sev-warning" title="' + f[1] + ' warning(s)">' + f[1] + "</span>";
    return "";
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  function item(n, depth) {
    var kids = n.c || [];
    var open = depth === 0 ? contains(n, current) : contains(n, current);
    var cls = [];
    if (n.i === current) cls.push("current");
    if (kids.length && !open) cls.push("collapsed");
    var href = root + (n.p || n.i + "/index.html");
    var html = '<li data-id="' + esc(n.i) + '" data-title="' + esc((n.n + " " + n.t).toLowerCase()) + '"' +
      (cls.length ? ' class="' + cls.join(" ") + '"' : "") + ">" +
      '<div class="row"><button class="twisty' + (kids.length ? "" : " leaf") + '" type="button" aria-label="Expand or collapse"' +
      (kids.length ? ' aria-expanded="' + open + '"' : ' tabindex="-1"') + ">" + (open ? "▾" : "▸") + "</button>" +
      '<a href="' + href + '"' + (n.i === current ? ' aria-current="page"' : "") + '><span class="n">' + esc(n.n) + "</span>" + esc(n.t) + "</a>" +
      badge(n.f || [0, 0, 0]) + "</div>";
    if (kids.length) html += "<ul>" + kids.map(function (k) { return item(k, depth + 1); }).join("") + "</ul>";
    return html + "</li>";
  }

  var tree = document.getElementById("tree");
  var treeBody = tree && tree.querySelector(".tree-body");
  if (treeBody && nav.nodes.length) {
    treeBody.innerHTML = "<ul>" + nav.nodes.map(function (n) { return item(n, 0); }).join("") + "</ul>" +
      '<div class="sep"></div><ul>' + nav.extra.map(function (n) { return item(n, 0); }).join("") + "</ul>";
    treeBody.addEventListener("click", function (e) {
      var t = e.target.closest(".twisty");
      if (!t || t.classList.contains("leaf")) return;
      var li = t.closest("li");
      var collapsed = li.classList.toggle("collapsed");
      t.textContent = collapsed ? "▸" : "▾";
      t.setAttribute("aria-expanded", String(!collapsed));
    });
    var cur = treeBody.querySelector("li.current > .row");
    if (cur) cur.scrollIntoView({ block: "center" });
  }

  // filter
  var filter = tree && tree.querySelector(".tree-filter input");
  if (filter && treeBody) {
    filter.addEventListener("input", function () {
      var q = filter.value.trim().toLowerCase();
      var all = treeBody.querySelectorAll("li");
      if (!q) {
        all.forEach(function (li) { li.classList.remove("hidden"); });
        return;
      }
      all.forEach(function (li) { li.classList.add("hidden"); });
      all.forEach(function (li) {
        if (li.getAttribute("data-title").indexOf(q) >= 0) {
          var p = li;
          while (p && p !== treeBody) {
            if (p.tagName === "LI") { p.classList.remove("hidden"); if (p !== li) p.classList.remove("collapsed"); }
            p = p.parentElement;
          }
        }
      });
    });
  }

  // mobile toggle
  var toggle = document.querySelector(".tree-toggle");
  if (toggle && tree) {
    toggle.addEventListener("click", function () {
      var open = tree.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // ------------------------------------------------------------ findings toggle
  var ft = document.querySelector(".findings-toggle");
  function syncFindings() {
    var hidden = document.documentElement.classList.contains("hide-findings");
    if (ft) { ft.textContent = hidden ? "Show findings" : "Hide findings"; ft.setAttribute("aria-pressed", String(hidden)); }
  }
  if (ft) {
    ft.addEventListener("click", function () {
      var hidden = document.documentElement.classList.toggle("hide-findings");
      store("guide-hide-findings", hidden ? "1" : "0");
      syncFindings();
    });
    syncFindings();
  }

  // ------------------------------------------------------------ lightbox
  var box = document.querySelector("dialog.lightbox");
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".fig-open");
    if (!b || !box || !box.showModal) return;
    box.querySelector("img").src = b.getAttribute("data-src");
    box.querySelector("img").alt = (b.querySelector("img") || {}).alt || "";
    box.querySelector(".lb-caption").textContent = b.getAttribute("data-caption") || "";
    box.showModal();
  });
  if (box) box.addEventListener("click", function (e) { if (e.target === box) box.close(); });

  // ------------------------------------------------------------ copy an example message
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".hl7-copy");
    if (!b || !navigator.clipboard) return;
    navigator.clipboard.writeText(b.getAttribute("data-text").replace(/\n/g, "\r")).then(function () {
      b.textContent = "Copied";
      setTimeout(function () { b.textContent = "Copy"; }, 1500);
    });
  });

  // ------------------------------------------------------------ permalink
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".permalink, .s-id");
    if (!b) return;
    var url = location.href.split("#")[0];
    if (b.classList.contains("s-id")) url += b.getAttribute("href");
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(function () {
        if (b.classList.contains("permalink")) {
          b.classList.add("copied");
          b.textContent = "Link copied";
          setTimeout(function () { b.classList.remove("copied"); b.textContent = "Copy link"; }, 1800);
        }
      });
    }
  });
})();
