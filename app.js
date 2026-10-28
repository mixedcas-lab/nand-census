/* NAND Census front end. Reads data/papers.json and data/meta.json (built by collector/build.py on
   the lab server) and data/overrides.csv (hand edits: remove a paper or replace its topic tags).
   Bibliographic list only: no figures are extracted or shown. */
(function () {
  "use strict";
  var REPO = "https://github.com/mixedcas-lab/nand-census";
  var PAGE = 100;
  var TOPICS = ["Chip", "Sensing/page buffer", "HV/WL driver", "I/O interface", "Program/erase scheme",
    "Controller/ECC/SSD", "Reliability", "Device/cell", "Compute/search"];
  var TOPIC_COLORS = {
    "Chip": "#2b316d", "Sensing/page buffer": "#1f7a8c", "HV/WL driver": "#b4533a", "I/O interface": "#6b4fa0",
    "Program/erase scheme": "#3f7d3a", "Controller/ECC/SSD": "#8a5a00", "Reliability": "#a23b72",
    "Device/cell": "#4a5666", "Compute/search": "#0b7a5c"
  };
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var ALL = [], META = {}, VIEW = [], LIMIT = PAGE, F;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function toggle(arr, v) { var i = arr.indexOf(v); if (i >= 0) arr.splice(i, 1); else arr.push(v); }
  function fmtDate(d) {
    var m = /^(\d{4})-(\d{2})/.exec(d || "");
    return m ? MONTHS[+m[2] - 1] + " " + m[1] : (d || "");
  }
  function defaults() {
    return { q: "", venues: [], topics: [], companies: [], y0: "", y1: "", country: "", related: false, fresh: false, sort: "date" };
  }

  /* ------------------------------------------------------------ URL hash (shareable filters) */
  function writeHash() {
    var p = [];
    if (F.q) p.push("q=" + encodeURIComponent(F.q));
    ["venues", "topics", "companies"].forEach(function (k) { if (F[k].length) p.push(k + "=" + F[k].map(encodeURIComponent).join(",")); });
    ["y0", "y1", "country"].forEach(function (k) { if (F[k]) p.push(k + "=" + encodeURIComponent(F[k])); });
    ["related", "fresh"].forEach(function (k) { if (F[k]) p.push(k + "=1"); });
    if (F.sort !== "date") p.push("sort=" + F.sort);
    var h = p.join("&");
    if (("#" + h) !== location.hash && !(h === "" && location.hash === "")) history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
  }
  function readHash() {
    location.hash.replace(/^#/, "").split("&").forEach(function (kv) {
      var i = kv.indexOf("="); if (i < 0) return;
      var k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
      if (k === "venues" || k === "topics" || k === "companies") F[k] = v.split(",").map(decodeURIComponent).filter(Boolean);
      else if (k === "related" || k === "fresh") F[k] = v === "1";
      else if (k in F) F[k] = v;
    });
  }

  /* ------------------------------------------------------------ overrides.csv */
  function parseCSV(text) {
    var rows = [], row = [], cell = "", q = false;
    for (var i = 0; i < text.length; i++) {
      var c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
      else if (c === '"') q = true;
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
      else cell += c;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    return rows.filter(function (r) { return r.some(function (x) { return x.trim(); }); });
  }
  function applyOverrides(papers, text) {
    var rows = parseCSV(text || ""), head = (rows.shift() || []).map(function (h) { return h.trim().toLowerCase(); });
    var ix = { id: head.indexOf("id"), action: head.indexOf("action"), topics: head.indexOf("topics"), note: head.indexOf("note") };
    if (ix.id < 0) return papers;
    var ov = {};
    rows.forEach(function (r) { var id = (r[ix.id] || "").trim(); if (id) ov[id] = r; });
    return papers.filter(function (p) {
      var r = ov[p.id];
      if (!r) return true;
      var act = ix.action >= 0 ? (r[ix.action] || "").trim().toLowerCase() : "";
      if (act === "exclude" || act === "remove") return false;
      if (act === "core") p.lv = "core";
      if (ix.topics >= 0 && (r[ix.topics] || "").trim()) {
        p.tp = r[ix.topics].split(/[;|]/).map(function (s) { return s.trim(); }).filter(function (s) { return TOPICS.indexOf(s) >= 0; });
        p.checked = true;
      }
      if (ix.note >= 0 && (r[ix.note] || "").trim()) p.note = r[ix.note].trim();
      return true;
    });
  }

  /* ------------------------------------------------------------ filtering */
  function base(p) {   // everything except the chip groups, so chip counts reflect the other filters
    if (!F.related && p.lv !== "core") return false;
    if (F.y0 && (p.y || 0) < +F.y0) return false;
    if (F.y1 && (p.y || 9999) > +F.y1) return false;
    if (F.country && (p.cn || []).indexOf(F.country) < 0) return false;
    if (F.fresh && !(p.first === META.updated && META.last_run_new)) return false;
    if (F.q) {
      var hay = p._hay || (p._hay = [p.t, (p.au || []).join(" "), (p.org || []).join(" "), (p.tp || []).join(" "),
        (p.co || []).join(" "), p.v, p.vt, p.y, p.doi].join(" ").toLowerCase());
      var words = F.q.toLowerCase().split(/\s+/).filter(Boolean);
      for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) < 0) return false;
    }
    return true;
  }
  function inChips(p, skip) {
    if (skip !== "venues" && F.venues.length && F.venues.indexOf(p.v) < 0) return false;
    if (skip !== "topics" && F.topics.length && !F.topics.every(function (t) { return (p.tp || []).indexOf(t) >= 0; })) return false;
    if (skip !== "companies" && F.companies.length && !F.companies.some(function (c) { return (p.co || []).indexOf(c) >= 0; })) return false;
    return true;
  }

  function chipHTML(list, selected, counts, colors) {
    return list.map(function (v) {
      var on = selected.indexOf(v) >= 0, n = counts[v] || 0;
      var dot = colors && colors[v] ? '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:' + colors[v] + '"></span>' : "";
      return '<button type="button" class="chip" data-v="' + esc(v) + '" aria-pressed="' + on + '"' + (!n && !on ? ' style="opacity:.45"' : "") + ">" +
        dot + esc(v) + '<span class="n">' + n + "</span></button>";
    }).join("");
  }
  function renderChips(pool) {
    var cv = {}, ct = {}, cc = {};
    pool.forEach(function (p) {
      if (inChips(p, "venues")) cv[p.v] = (cv[p.v] || 0) + 1;
      if (inChips(p, "topics")) (p.tp || []).forEach(function (t) { ct[t] = (ct[t] || 0) + 1; });
      if (inChips(p, "companies")) (p.co || []).forEach(function (c) { cc[c] = (cc[c] || 0) + 1; });
    });
    var venues = uniq(ALL.map(function (p) { return p.v; })).sort(function (a, b) { return (META.by_venue[b] || 0) - (META.by_venue[a] || 0) || a.localeCompare(b); });
    var comps = uniq([].concat.apply([], ALL.map(function (p) { return p.co || []; }))).sort(function (a, b) {
      return (a === "Other industry") - (b === "Other industry") || (META.by_company[b] || 0) - (META.by_company[a] || 0) || a.localeCompare(b);
    });
    $("venues").innerHTML = chipHTML(venues, F.venues, cv);
    $("topics").innerHTML = chipHTML(TOPICS, F.topics, ct, TOPIC_COLORS);
    $("companies").innerHTML = chipHTML(comps, F.companies, cc);
  }
  function uniq(a) { var s = {}; return a.filter(function (x) { if (!x || s[x]) return false; s[x] = 1; return true; }); }

  /* ------------------------------------------------------------ rendering */
  function reportURL(p) {
    var body = ["Paper: " + p.t, "IEEE id: " + p.id + (p.url ? " (" + p.url + ")" : ""), "",
      "What is wrong (pick one):", "- [ ] Not a NAND flash paper (remove)", "- [ ] Topic tags are wrong", "- [ ] Other", "",
      "Correct topics (from: " + TOPICS.join("; ") + "):", "", "Topics shown now: " + ((p.tp || []).join("; ") || "(none)"), "",
      "overrides.csv row to add:", "id,action,topics,note", p.id + ",,,"].join("\n");
    return REPO + "/issues/new?title=" + encodeURIComponent("Report: " + p.t.slice(0, 80)) + "&body=" + encodeURIComponent(body);
  }
  function rowHTML(p) {
    var names = (p.au || []).join(", ");
    var tags = (p.tp || []).map(function (t) {
      return '<span class="tag tp" style="background:' + (TOPIC_COLORS[t] || "#4a5666") + '">' + esc(t) + "</span>";
    }).concat((p.co || []).map(function (c) { return '<span class="tag co">' + esc(c) + "</span>"; }));
    if (p.ct === "EA") tags.push('<span class="tag">Early access</span>');
    if (p.lv !== "core") tags.push('<span class="tag lv">NAND in the abstract only</span>');
    var fresh = p.first === META.updated && META.last_run_new;
    return '<div class="tr" role="row" data-id="' + esc(p.id) + '">' +
      '<div class="pub" role="cell"><span class="venue">' + esc(p.v) + "</span><span>" + esc(fmtDate(p.d)) + "</span>" +
      (fresh ? '<span class="new">New</span>' : "") +
      '<a class="fix" href="' + esc(reportURL(p)) + '" target="_blank" rel="noopener" title="Open a GitHub issue: not a NAND paper, or wrong tags">Report</a></div>' +
      '<div class="paper" role="cell"><a class="title" href="' + esc(p.url || (p.doi ? "https://doi.org/" + p.doi : "#")) +
      '" target="_blank" rel="noopener">' + esc(p.t) + "</a>" +
      (names ? '<p class="by">' + esc(names) + "</p>" : "") +
      ((p.org || []).length ? '<p class="by org">' + esc(p.org.slice(0, 3).join("; ")) + "</p>" : "") +
      (p.note ? '<p class="by note">' + esc(p.note) + "</p>" : "") +
      (tags.length ? '<div class="tags">' + tags.join("") + "</div>" : "") + "</div></div>";
  }
  function renderRows() {
    $("rows").innerHTML = VIEW.slice(0, LIMIT).map(rowHTML).join("");
    $("more").hidden = VIEW.length <= LIMIT;
    $("more").textContent = "Show more (" + Math.min(PAGE, VIEW.length - LIMIT) + " of " + (VIEW.length - LIMIT) + " remaining)";
  }

  function update(opts) {
    var pool = ALL.filter(base);
    VIEW = pool.filter(function (p) { return inChips(p); });
    var key = F.sort;
    VIEW.sort(function (a, b) {
      if (key === "old") return (a.d || "").localeCompare(b.d || "") || a.id.localeCompare(b.id);
      if (key === "venue") return a.v.localeCompare(b.v) || (b.d || "").localeCompare(a.d || "");
      return (b.d || "").localeCompare(a.d || "") || b.id.localeCompare(a.id);
    });
    if (!(opts && opts.keepLimit)) LIMIT = PAGE;
    renderChips(pool);
    $("count").innerHTML = "<strong>" + VIEW.length.toLocaleString() + "</strong> " + (VIEW.length === 1 ? "paper" : "papers");
    $("y0").value = F.y0; $("y1").value = F.y1; $("country").value = F.country; $("sort").value = F.sort;
    $("related").checked = F.related; $("fresh").checked = F.fresh;
    if ($("q").value.trim() !== F.q) $("q").value = F.q;
    $("empty").hidden = VIEW.length > 0 || !ALL.length;
    if (!VIEW.length && ALL.length) $("empty").textContent = "No paper matches these filters.";
    renderRows();
    writeHash();
  }

  function downloadCSV() {
    var head = ["id", "year", "date", "venue", "title", "authors", "affiliations", "countries", "companies", "topics", "level", "doi", "url"];
    var q = function (s) { s = String(s == null ? "" : s); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    var lines = [head.join(",")].concat(VIEW.map(function (p) {
      return [p.id, p.y, p.d, p.v, p.t, (p.au || []).join("; "), (p.org || []).join("; "), (p.cn || []).join("; "),
        (p.co || []).join("; "), (p.tp || []).join("; "), p.lv, p.doi, p.url].map(q).join(",");
    }));
    var blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "nand-census-" + (META.updated || "export") + ".csv";
    document.body.appendChild(a); a.click(); a.remove();
  }

  /* ------------------------------------------------------------ setup */
  function lede() {
    var core = ALL.filter(function (p) { return p.lv === "core"; }).length;
    var nv = Object.keys(META.by_venue || {}).length;
    $("lede").innerHTML = "<strong>" + core.toLocaleString() + " NAND flash papers</strong> from " + nv +
      " IEEE circuits and memory-device venues" + (META.coverage_from ? ", " + fmtDate(META.coverage_from) + " to " + fmtDate(META.coverage_to) : "") +
      ".<br>Updated automatically, last update <span class=\"nowrap\">" + esc(META.updated || "") + "</span>" +
      (META.last_run_new ? ", with " + META.last_run_new + " papers added in the latest update." : ".");
    var years = {}, thisYear = new Date().getFullYear();
    ALL.forEach(function (p) { if (p.lv === "core" && p.y) years[p.y] = (years[p.y] || 0) + 1; });
    var top = Object.keys(META.by_company || {}).filter(function (c) { return c !== "Other industry"; })
      .sort(function (a, b) { return META.by_company[b] - META.by_company[a]; }).slice(0, 3);
    $("summary").innerHTML = '<span><b>' + core.toLocaleString() + "</b>papers</span>" +
      '<span><b>' + ((years[thisYear] || 0) + (years[thisYear - 1] || 0)) + "</b>in " + (thisYear - 1) + "–" + thisYear + "</span>" +
      '<span><b>' + nv + "</b>venues</span>" +
      (top.length ? "<span>Most papers from industry: " + top.map(function (c) { return esc(c) + " (" + META.by_company[c] + ")"; }).join(", ") + "</span>" : "");
    $("summary").hidden = false;
  }
  function fillSelects() {
    var ys = uniq(ALL.map(function (p) { return p.y; })).sort();
    var opts = '<option value="">Any</option>' + ys.map(function (y) { return '<option value="' + y + '">' + y + "</option>"; }).join("");
    $("y0").innerHTML = opts; $("y1").innerHTML = opts;
    var cn = {};
    ALL.forEach(function (p) { (p.cn || []).forEach(function (c) { cn[c] = (cn[c] || 0) + 1; }); });
    $("country").innerHTML = '<option value="">All</option>' + Object.keys(cn).sort(function (a, b) { return cn[b] - cn[a]; })
      .map(function (c) { return '<option value="' + esc(c) + '">' + esc(c) + " (" + cn[c] + ")</option>"; }).join("");
  }
  function bind() {
    var t;
    $("q").addEventListener("input", function (e) { clearTimeout(t); t = setTimeout(function () { F.q = e.target.value.trim(); update(); }, 160); });
    ["venues", "topics", "companies"].forEach(function (k) {
      $(k).addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) { toggle(F[k], b.dataset.v); update(); } });
    });
    ["y0", "y1", "country", "sort"].forEach(function (k) { $(k).addEventListener("change", function (e) { F[k] = e.target.value; update(); }); });
    ["related", "fresh"].forEach(function (k) { $(k).addEventListener("change", function (e) { F[k] = e.target.checked; update(); }); });
    $("reset").addEventListener("click", function () { F = defaults(); update(); });
    $("more").addEventListener("click", function () { LIMIT += PAGE; renderRows(); });
    $("csv").addEventListener("click", downloadCSV);
    window.addEventListener("hashchange", function () { F = defaults(); readHash(); update(); });
  }
  function get(path, json) {
    return fetch(path, { cache: "no-cache" }).then(function (r) { return r.ok ? (json ? r.json() : r.text()) : null; }).catch(function () { return null; });
  }

  F = defaults();
  readHash();
  Promise.all([get("data/papers.json", true), get("data/meta.json", true), get("data/overrides.csv", false)]).then(function (res) {
    META = res[1] || {};
    META.by_venue = META.by_venue || {}; META.by_company = META.by_company || {};
    ALL = applyOverrides(res[0] || [], res[2]);
    bind();
    if (!ALL.length) {
      $("lede").textContent = "The paper index is being built.";
      $("empty").hidden = false;
      $("empty").innerHTML = "The first list appears after the lab server's daily run, once the shared IEEE cache has fetched " +
        "IMW, IEDM and IEEE TED. Until then, see the sister sites above.";
      $("count").textContent = "";
      return;
    }
    fillSelects();
    lede();
    update();
  });
})();
