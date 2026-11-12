/* Card-level review comments stored in InteropHub (one document key for the whole site).
 *
 * Each page declares window.GUIDE_COMMENTS = {hub, document, anchor, title, targets, root}:
 *   anchor   the page's review anchor (a card ID, or structure-…/quality-… for generated pages)
 *   targets  what a comment can be "about" on this page: [{i: 0, label: "Whole section"}, {i: 3, label: "Statement s3", snippet}]
 * A comment is stored as {anchor, blockIndex: target i, snippet}. Sign-in is the InteropHub
 * PKCE flow used by the AIRA guide template (app_code topic-reference), so one sign-in covers
 * every page of the site. Reading comments also requires sign-in.
 * No dependencies. All user text is inserted with textContent.
 */
(function () {
  "use strict";
  var cfg = window.GUIDE_COMMENTS;
  if (!cfg || !cfg.hub || !cfg.document) return;
  var hub = cfg.hub.replace(/\/$/, "");
  var key = cfg.document;
  var tokenKey = "content-guide-token:" + hub + ":" + key;
  var authKey = "content-guide-signin:" + hub + ":" + key;
  var auth = readJson(localStorage, tokenKey);
  var info = null;
  var threads = [];
  var showClosed = false;
  var notRegistered = false;
  var panel = document.getElementById("comments");
  var body = document.body;

  // ------------------------------------------------------------------ storage and requests
  function readJson(store, k) {
    try { return JSON.parse(store.getItem(k) || "null"); } catch (e) { return null; }
  }
  function writeJson(store, k, v) {
    try { if (v === null) store.removeItem(k); else store.setItem(k, JSON.stringify(v)); } catch (e) { /* storage off */ }
  }
  function signedIn() {
    if (auth && auth.accessToken && Date.parse(auth.expiresAt) > Date.now()) return true;
    if (auth) { auth = null; writeJson(localStorage, tokenKey, null); }
    return false;
  }
  function request(path, opts) {
    opts = opts || {};
    var headers = { "Content-Type": "application/json" };
    if (opts.token !== false && signedIn()) headers.Authorization = "Bearer " + auth.accessToken;
    return fetch(hub + path, {
      method: opts.method || "GET", headers: headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body)
    }).then(function (r) {
      if (r.status === 401 && opts.token !== false) {
        auth = null; writeJson(localStorage, tokenKey, null);
        throw { signin: true, message: "Sign in to see and add comments." };
      }
      if (r.status === 204) return null;
      return r.json().catch(function () { return {}; }).then(function (b) {
        if (!r.ok) throw { status: r.status, message: b.message || "The comment service could not complete the request." };
        return b;
      });
    });
  }
  var api = "/api/guide/" + encodeURIComponent(key);

  // ------------------------------------------------------------------ sign-in (PKCE, response in the fragment)
  function b64url(bytes) {
    var s = ""; bytes.forEach(function (v) { s += String.fromCharCode(v); });
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function pageUrl() { return location.origin + location.pathname; }
  function beginSignIn(prompt) {
    var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    var bytes = new Uint8Array(64); crypto.getRandomValues(bytes);
    var verifier = Array.prototype.map.call(bytes, function (v) { return chars[v % chars.length]; }).join("");
    var sb = new Uint8Array(24); crypto.getRandomValues(sb);
    var state = b64url(sb);
    var back = new URL(location.href); back.searchParams.delete("interophub");
    writeJson(sessionStorage, authKey, { codeVerifier: verifier, state: state, returnLocation: back.href });
    crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)).then(function (d) {
      var q = new URLSearchParams({
        app_code: "topic-reference", return_to: pageUrl(), state: state,
        code_challenge: b64url(new Uint8Array(d)), code_challenge_method: "S256",
        response_mode: "fragment", requested_url: pageUrl()
      });
      if (prompt) q.set("prompt", "login");
      location.href = hub + "/home?" + q.toString();
    });
  }
  function finishSignIn() {
    var params = new URLSearchParams(location.hash.slice(1));
    if (!params.has("code")) return Promise.resolve(false);
    var pending = readJson(sessionStorage, authKey);
    writeJson(sessionStorage, authKey, null);
    if (!pending || params.get("state") !== pending.state) {
      history.replaceState(null, "", location.pathname + location.search);
      return Promise.resolve(false);
    }
    return request("/api/guide/token", {
      token: false, method: "POST",
      body: { code: params.get("code"), codeVerifier: pending.codeVerifier, returnTo: pageUrl() }
    }).then(function (r) {
      auth = { accessToken: r.accessToken, expiresAt: r.expiresAt, user: r.user };
      writeJson(localStorage, tokenKey, auth);
      history.replaceState(null, "", pending.returnLocation);
      return true;
    }).catch(function (e) {
      history.replaceState(null, "", location.pathname + location.search);
      status(e.message || "Sign-in did not complete. Try again.");
      return false;
    });
  }
  function signOut(switchAccount) {
    request("/api/guide/token", { method: "DELETE" }).catch(function () {}).then(function () {
      auth = null; writeJson(localStorage, tokenKey, null);
      threads = []; info = null;
      if (switchAccount) beginSignIn(true); else render();
    });
  }

  // ------------------------------------------------------------------ DOM helpers
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  function button(label, cls, fn) {
    var b = el("button", cls || "c-btn", label); b.type = "button";
    b.addEventListener("click", fn); return b;
  }
  function when(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }
  function status(msg) {
    if (!panel) return;
    var s = panel.querySelector(".c-status");
    if (s) s.textContent = msg || "";
  }
  function targetLabel(i) {
    var t = (cfg.targets || []).filter(function (x) { return x.i === Number(i); })[0];
    return t ? t.label : (Number(i) ? "Part " + i : "Whole section");
  }

  // ------------------------------------------------------------------ data
  function load() {
    if (!signedIn()) { info = null; threads = []; return Promise.resolve(); }
    return request(api).catch(function (e) {
      if (e && e.status === 404) { notRegistered = true; return null; }
      throw e;
    }).then(function (d) {
      if (!d) return;
      info = d;
      if (!d.permissions || !d.permissions.canView) { threads = []; return; }
      return request(api + "/comments" + (showClosed ? "?state=all" : "")).then(function (r) {
        threads = r.comments || [];
        try { sessionStorage.setItem("guide-comment-index:" + key, JSON.stringify(index(threads))); } catch (e) { /* ignore */ }
      });
    });
  }
  function index(list) {
    var out = {};
    list.forEach(function (t) {
      if (t.deleted) return;
      var o = out[t.anchor] || (out[t.anchor] = { open: 0, all: 0 });
      o.all++;
      if (t.state === "OPEN") o.open++;
    });
    return out;
  }

  // ------------------------------------------------------------------ tree badges
  function badges(idx) {
    if (!idx) return;
    document.querySelectorAll(".tree li[data-id]").forEach(function (li) {
      var row = li.querySelector(":scope > .row");
      if (!row) return;
      var old = row.querySelector(".c-badge"); if (old) old.remove();
      var n = idx[li.getAttribute("data-id")];
      if (n && n.all) {
        var b = el("span", "c-badge" + (n.open ? " open" : ""), String(n.all));
        b.title = n.all + " comment thread(s)" + (n.open ? ", " + n.open + " open" : "");
        row.appendChild(b);
      }
    });
  }

  // ------------------------------------------------------------------ rendering
  function render() {
    if (!panel) return;
    panel.textContent = "";
    var head = el("div", "c-head");
    head.appendChild(el("h2", "", "Comments"));
    var who = el("div", "c-who");
    if (signedIn()) {
      who.appendChild(el("span", "", "Signed in as " + ((auth.user && auth.user.displayName) || "InteropHub user")));
      who.appendChild(button("Switch account", "c-link", function () { signOut(true); }));
      who.appendChild(button("Sign out", "c-link", function () { signOut(false); }));
    }
    head.appendChild(who);
    panel.appendChild(head);
    panel.appendChild(el("p", "c-status", ""));

    if (!signedIn()) {
      var p = el("p", "c-intro", "Reviewers comment on each section of this draft through InteropHub. Sign in to see the comments on this page and add your own.");
      panel.appendChild(p);
      panel.appendChild(button("Sign in with InteropHub", "c-btn primary", function () { beginSignIn(false); }));
      return;
    }
    if (notRegistered) {
      panel.appendChild(el("p", "c-intro", "Commenting on this draft has not opened yet. Check back soon."));
      return;
    }
    if (!info) { status("Loading comments…"); return; }
    if (!info.permissions.canView) {
      panel.appendChild(el("p", "c-intro", "Your InteropHub account cannot view comments on this guide. The review is open to members of the topic “"
        + ((info.topic && info.topic.topicName) || "") + "” in InteropHub."));
      if (info.topic && info.topic.url) {
        var a = el("a", "c-link", "Open the topic in InteropHub"); a.href = info.topic.url; panel.appendChild(a);
      }
      return;
    }
    var mine = threads.filter(function (t) { return t.anchor === cfg.anchor && !t.deleted; });
    mine.sort(function (a, b) { return (a.blockIndex || 0) - (b.blockIndex || 0) || (a.createdAt < b.createdAt ? -1 : 1); });
    var list = el("div", "c-list");
    if (!mine.length) list.appendChild(el("p", "c-empty", showClosed ? "No comments on this page." : "No open comments on this page."));
    mine.forEach(function (t) { list.appendChild(threadEl(t)); });
    panel.appendChild(list);

    var tools = el("div", "c-tools");
    var lbl = el("label", "c-toggle");
    var cb = el("input"); cb.type = "checkbox"; cb.checked = showClosed;
    cb.addEventListener("change", function () { showClosed = cb.checked; refresh(); });
    lbl.appendChild(cb); lbl.appendChild(document.createTextNode(" Show closed and withdrawn"));
    tools.appendChild(lbl);
    if (info.topic && info.topic.topicId) {
      var all = el("a", "c-link", "All comments in InteropHub");
      all.href = hub + "/es/topic-guide-comments/" + info.topic.topicId; all.target = "_blank"; all.rel = "noopener";
      tools.appendChild(all);
    }
    panel.appendChild(tools);
    if (info.permissions.canComment) panel.appendChild(newForm());
    else panel.appendChild(el("p", "c-empty", "Comments on this guide are closed (read-only)."));
    if (location.hash.indexOf("#comment-") === 0) {
      var target = document.getElementById(location.hash.slice(1));
      if (target) { target.classList.add("c-target"); target.scrollIntoView({ block: "center" }); }
    }
  }

  function threadEl(t) {
    var box = el("article", "c-thread state-" + String(t.state || "").toLowerCase());
    box.id = "comment-" + t.id;
    var meta = el("div", "c-meta");
    meta.appendChild(el("strong", "", (t.author && t.author.displayName) || "Reviewer"));
    if (t.author && t.author.organization) meta.appendChild(el("span", "c-org", t.author.organization));
    meta.appendChild(el("span", "c-date", when(t.createdAt) + (t.editedAt ? " (edited)" : "")));
    if (t.state && t.state !== "OPEN") meta.appendChild(el("span", "c-state", t.state.toLowerCase()));
    box.appendChild(meta);
    if (Number(t.blockIndex)) box.appendChild(el("div", "c-about", "About: " + targetLabel(t.blockIndex)));
    box.appendChild(el("div", "c-text", t.text));
    if (t.disposition) {
      var d = el("div", "c-disp");
      d.appendChild(el("strong", "", t.disposition.label + ". "));
      if (t.changeNote) d.appendChild(document.createTextNode(t.changeNote));
      box.appendChild(d);
    }
    (t.replies || []).forEach(function (r) {
      if (r.deleted) return;
      var rb = el("div", "c-reply"); rb.id = "comment-" + r.id;
      var rm = el("div", "c-meta");
      rm.appendChild(el("strong", "", (r.author && r.author.displayName) || "Reviewer"));
      rm.appendChild(el("span", "c-date", when(r.createdAt) + (r.editedAt ? " (edited)" : "")));
      rb.appendChild(rm);
      rb.appendChild(el("div", "c-text", r.text));
      var ra = el("div", "c-actions");
      if (r.permissions && r.permissions.canEdit) ra.appendChild(button("Edit", "c-link", function () { editForm(rb, r); }));
      if (r.permissions && r.permissions.canWithdraw && !r.withdrawn) ra.appendChild(button("Withdraw", "c-link", function () { act(withdraw(r)); }));
      rb.appendChild(ra);
      box.appendChild(rb);
    });
    var p = t.permissions || {};
    var actions = el("div", "c-actions");
    if (p.canReply) actions.appendChild(button("Reply", "c-link", function () { replyForm(box, t); }));
    if (p.canEdit) actions.appendChild(button("Edit", "c-link", function () { editForm(box, t); }));
    if (p.canWithdraw && t.state !== "WITHDRAWN") actions.appendChild(button("Withdraw", "c-link", function () { act(withdraw(t)); }));
    if (p.canDispose) actions.appendChild(button(t.disposition ? "Change disposition" : "Disposition", "c-link", function () { dispositionForm(box, t); }));
    if (p.canClose && (t.state === "OPEN" || t.state === "DISPOSED")) actions.appendChild(button("Close", "c-link", function () { act(patch(t, { state: "CLOSED" })); }));
    if (p.canClose && t.state === "CLOSED") actions.appendChild(button("Reopen", "c-link", function () { act(patch(t, { state: "OPEN" })); }));
    box.appendChild(actions);
    return box;
  }

  // ------------------------------------------------------------------ forms and actions
  function textarea(value) {
    var t = el("textarea"); t.rows = 4; t.value = value || ""; t.maxLength = 10000; return t;
  }
  function newForm() {
    var f = el("form", "c-form");
    f.appendChild(el("h3", "", "Add a comment"));
    var sel = null;
    if ((cfg.targets || []).length > 1) {
      var l = el("label", "c-field", "About ");
      sel = el("select");
      cfg.targets.forEach(function (x) { var o = el("option", "", x.label); o.value = x.i; sel.appendChild(o); });
      l.appendChild(sel); f.appendChild(l);
    }
    var ta = textarea(); ta.setAttribute("aria-label", "Comment"); ta.placeholder = "Your comment on " + (cfg.title || "this section");
    f.appendChild(ta);
    var row = el("div", "c-actions");
    var submit = el("button", "c-btn primary", "Post comment"); submit.type = "submit";
    row.appendChild(submit);
    row.appendChild(el("span", "c-hint", "Visible to signed-in reviewers of this guide."));
    f.appendChild(row);
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = ta.value.trim(); if (!text) return;
      var i = sel ? Number(sel.value) : 0;
      var t = (cfg.targets || []).filter(function (x) { return x.i === i; })[0];
      submit.disabled = true;
      act(request(api + "/comments", { method: "POST", body: {
        anchor: cfg.anchor, blockIndex: i, snippet: (t && t.snippet) || cfg.title || "", text: text } }));
    });
    return f;
  }
  function inlineForm(host, label, value, onSave) {
    var old = host.querySelector(":scope > .c-form"); if (old) { old.remove(); return; }
    var f = el("form", "c-form inline");
    var ta = textarea(value); f.appendChild(ta);
    var row = el("div", "c-actions");
    var s = el("button", "c-btn primary", label); s.type = "submit"; row.appendChild(s);
    row.appendChild(button("Cancel", "c-link", function () { f.remove(); }));
    f.appendChild(row);
    f.addEventListener("submit", function (e) { e.preventDefault(); var v = ta.value.trim(); if (v) { s.disabled = true; act(onSave(v)); } });
    host.appendChild(f); ta.focus();
  }
  function replyForm(box, t) {
    inlineForm(box, "Reply", "", function (text) {
      return request(api + "/comments", { method: "POST", body: { parentCommentId: t.id, text: text } });
    });
  }
  function editForm(box, item) {
    inlineForm(box, "Save", item.text, function (text) { return patch(item, { text: text }); });
  }
  function dispositionForm(box, t) {
    var old = box.querySelector(":scope > .c-form"); if (old) { old.remove(); return; }
    var f = el("form", "c-form inline");
    var sel = el("select");
    var none = el("option", "", "No disposition"); none.value = ""; sel.appendChild(none);
    (info.dispositions || []).forEach(function (d) {
      var o = el("option", "", d.label); o.value = d.code;
      if (t.disposition && t.disposition.code === d.code) o.selected = true;
      sel.appendChild(o);
    });
    var l = el("label", "c-field", "Disposition "); l.appendChild(sel); f.appendChild(l);
    var ta = textarea(t.changeNote || ""); ta.placeholder = "Change note: what will change, or why not"; f.appendChild(ta);
    var row = el("div", "c-actions");
    var s = el("button", "c-btn primary", "Save disposition"); s.type = "submit"; row.appendChild(s);
    row.appendChild(button("Cancel", "c-link", function () { f.remove(); }));
    f.appendChild(row);
    f.addEventListener("submit", function (e) {
      e.preventDefault(); s.disabled = true;
      act(patch(t, { dispositionCode: sel.value || null, changeNote: ta.value.trim() || null }));
    });
    box.appendChild(f);
  }
  function patch(item, values) {
    values.expectedUpdatedAt = item.updatedAt;
    return request("/api/guide/comments/" + item.id, { method: "PATCH", body: values });
  }
  function withdraw(item) {
    return request("/api/guide/comments/" + item.id + "/withdraw", { method: "POST", body: {} });
  }
  function act(promise) {
    return promise.then(refresh).catch(function (e) {
      if (e && e.signin) render();
      status((e && e.message) || "The comment service could not complete the request.");
      if (panel) panel.querySelectorAll("button[disabled]").forEach(function (b) { b.disabled = false; });
    });
  }
  function refresh() {
    return load().then(function () { render(); badges(index(threads)); }).catch(function (e) {
      render(); status((e && e.message) || "Comments could not be loaded.");
    });
  }

  // ------------------------------------------------------------------ home-page routing for InteropHub comment links
  // InteropHub links to <site>/?interophub=signin#comment-<id>; site.js routes #<anchor> links.
  function route() {
    var hash = location.hash.slice(1);
    if (!body.classList.contains("home") || !/^comment-\d+$/.test(hash)) return Promise.resolve(false);
    if (!signedIn()) { beginSignIn(false); return Promise.resolve(true); }
    var id = Number(hash.slice(8));
    var anchors = (window.GUIDE_NAV && window.GUIDE_NAV.anchors) || {};
    return request(api + "/comments?state=all").then(function (r) {
      var t = (r.comments || []).filter(function (x) {
        return x.id === id || (x.replies || []).some(function (y) { return y.id === id; });
      })[0];
      if (!t) return false;
      location.replace((anchors[t.anchor] || t.anchor + "/index.html") + "#" + hash);
      return true;
    }).catch(function () { return false; });
  }

  // ------------------------------------------------------------------ start
  finishSignIn().then(function () {
    var params = new URL(location.href).searchParams;
    if (params.get("interophub") === "signin" && !signedIn() && !body.classList.contains("home")) { beginSignIn(false); return; }
    return route().then(function (routed) {
      if (routed) return;
      try { badges(JSON.parse(sessionStorage.getItem("guide-comment-index:" + key) || "null")); } catch (e) { /* ignore */ }
      if (panel) render();
      if (signedIn()) refresh();
    });
  });
})();
