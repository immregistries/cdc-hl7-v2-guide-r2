/* Navigation tree, filter, reader/author view switch, figure lightbox, and permalink copy. No dependencies. */
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
    var area = key === "guide-filter" ? window.sessionStorage : window.localStorage;
    try { if (value === undefined) return area.getItem(key); area.setItem(key, value); } catch (e) { return null; }
  }

  // ------------------------------------------------------------ tree
  function contains(node, id) {
    if (node.i === id) return true;
    return (node.c || []).some(function (k) { return contains(k, id); });
  }

  function badge(f) {  // quality findings: author view only
    if (f[0]) return '<span class="badge sev-issue author-only" title="' + f[0] + ' issue(s)">' + f[0] + "</span>";
    if (f[1]) return '<span class="badge sev-warning author-only" title="' + f[1] + ' warning(s)">' + f[1] + "</span>";
    return "";
  }
  function authorView() { return document.documentElement.classList.contains("author-view"); }

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
    // the guide (chapters, chapter 7, appendices), then, in the author view only, below a line: how the guide is made
    // and the review tools
    var meta = nav.meta || [];
    treeBody.innerHTML = "<ul>" + nav.nodes.concat(nav.extra).map(function (n) { return item(n, 0); }).join("") + "</ul>" +
      (meta.length ? '<div class="author-only"><div class="sep"></div><ul>' + meta.map(function (n) { return item(n, 0); }).join("") + "</ul></div>" : "");
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

  // filter: by title words and by each section's terms (fields, codes, value sets, curated concepts).
  // Every word typed must match. A field (RXA-2) matches exactly or with a component (RXA-2.1), never RXA-20;
  // a segment (RXA) matches all its fields; codes of 1-2 characters match only exactly; other words match
  // a term or title word that starts with them. The filter is kept while moving between pages.
  var filter = tree && tree.querySelector(".tree-filter input");
  var filterStatus = tree && tree.querySelector(".filter-status");
  var termsById = {};
  (function collect(ns) { ns.forEach(function (n) { termsById[n.i] = n.k || []; if (n.c) collect(n.c); }); })(nav.nodes.concat(nav.extra, nav.meta || []));

  function tokenMatch(tok, term) {
    var t = term.toLowerCase();
    if (/^[a-z][a-z0-9]{2}-\d+(\.\d+)*$/.test(tok)) return t === tok || t.indexOf(tok + ".") === 0;
    if (/^[a-z][a-z0-9]{2}$/.test(tok) && t.indexOf(tok + "-") === 0) return true;
    if (tok.length <= 2) return t === tok;
    if (t === tok) return true;
    return t.split(/[\s\/-]+/).some(function (w) { return w.indexOf(tok) === 0; });
  }

  function nodeMatches(li, tokens) {
    var id = li.getAttribute("data-id");
    var terms = termsById[id] || [];
    var title = li.getAttribute("data-title") || "";
    var words = title.split(/\s+/);
    var hits = [];
    var ok = tokens.every(function (tok) {
      var termHit = terms.filter(function (term) { return tokenMatch(tok, term); });
      if (termHit.length) { termHit.forEach(function (h) { if (hits.indexOf(h) < 0) hits.push(h); }); return true; }
      if (tok.length > 2 && (title.indexOf(tok) >= 0 || words.some(function (w) { return w.indexOf(tok) === 0; }))) return true;
      return words.indexOf(tok) >= 0;
    });
    return ok ? hits : null;
  }

  function applyFilter(q) {
    var all = treeBody.querySelectorAll("li");
    treeBody.querySelectorAll(".row .hit").forEach(function (e) { e.remove(); });
    store("guide-filter", q);
    if (!q) {
      all.forEach(function (li) { li.classList.remove("hidden"); });
      if (filterStatus) filterStatus.textContent = "";
      return;
    }
    var tokens = q.toLowerCase().split(/[\s,]+/).filter(Boolean);
    var count = 0;
    all.forEach(function (li) { li.classList.add("hidden"); });
    var author = authorView();
    all.forEach(function (li) {
      if (!author && li.closest(".author-only")) return;
      var hits = nodeMatches(li, tokens);
      if (!hits) return;
      count++;
      var row = li.querySelector(":scope > .row");
      if (row && hits.length) {
        var chip = document.createElement("span");
        chip.className = "hit";
        chip.textContent = hits.slice(0, 3).join(", ") + (hits.length > 3 ? " …" : "");
        row.querySelector("a").appendChild(chip);
      }
      var p = li;
      while (p && p !== treeBody) {
        if (p.tagName === "LI") { p.classList.remove("hidden"); if (p !== li) p.classList.remove("collapsed"); }
        p = p.parentElement;
      }
    });
    if (filterStatus) filterStatus.textContent = count ? count + " matching" : "Nothing matches";
  }

  if (filter && treeBody) {
    filter.addEventListener("input", function () { applyFilter(filter.value.trim()); });
    var saved = store("guide-filter");
    if (saved) { filter.value = saved; applyFilter(saved); }
    document.addEventListener("click", function (e) {
      var b = e.target.closest(".term");
      if (!b) return;
      filter.value = b.getAttribute("data-term");
      applyFilter(filter.value);
      if (tree.classList && window.matchMedia("(max-width: 900px)").matches) tree.classList.add("open");
      filter.focus();
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

  // ------------------------------------------------------------ reader / author view
  // The switch is shown only to authors (html.is-author: set before drawing by the script in <head>, from InteropHub's
  // answer cached by comments.js). It moves between the author view and the reader view and remembers the choice.
  var vt = document.querySelector(".view-toggle");
  function syncView() {
    var on = authorView();
    if (vt) { vt.textContent = on ? "Reader view" : "Author view"; vt.setAttribute("aria-pressed", String(!on));
      vt.title = on ? "See the guide as readers see it" : "Show the quality findings and the pages for the authors"; }
    if (filter && filter.value.trim()) applyFilter(filter.value.trim());
  }
  if (vt) {
    vt.addEventListener("click", function () {
      var on = document.documentElement.classList.toggle("author-view");
      store("guide-view", on ? "author" : "reader");
      syncView();
    });
    syncView();
  }
  document.addEventListener("guide-author", syncView);  // comments.js learned whether this person is an author

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

  // ------------------------------------------------------------ a link to something inside a folded section opens it
  // (for example a deferred finding, or a finding in a long list on the Quality review)
  function reveal() {
    if (location.hash.length < 2) return;
    var t = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!t) return;
    var folded = false;
    for (var p = t.parentElement; p; p = p.parentElement) if (p.tagName === "DETAILS" && !p.open) { p.open = true; folded = true; }
    if (folded) t.scrollIntoView();
  }
  reveal();
  window.addEventListener("hashchange", reveal);
})();
