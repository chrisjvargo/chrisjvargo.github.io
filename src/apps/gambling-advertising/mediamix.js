/* Ad spend by media (tab 1): every major advertiser's media mix.
   Level 1: 100% stacked share bars (top advertisers). Level 2 (click):
   monthly stacked spend $ by media type for that advertiser.
   Data: data/meg_cpm.json strata brand dollars (MediaRadar, finalized months). */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  var MEDIA = [
    { name: "TV", color: "#8a3b2e" },
    { name: "Digital Video", color: "#c08a3e" },
    { name: "Digital Display & Apps", color: "#2e5f8a" },
    { name: "Radio", color: "#4a7a4f" },
    { name: "Print", color: "#6b4a8a" }
  ];
  var D = null, selected = null;

  function brandIn(stratum, brand) {
    return ((D.strata[stratum] || {}).brands || []).filter(function (x) { return x.brand === brand; })[0];
  }
  function val(brand, mname, mo) {
    var b = brandIn(mname, brand); if (!b) return 0;
    var p = b.points.filter(function (x) { return x.month === mo; })[0];
    return p && !p.provisional ? (p.dollars || 0) : 0;
  }
  function months() {
    var s = {};
    MEDIA.forEach(function (m) {
      ((D.strata[m.name] || {}).brands || []).forEach(function (b) {
        b.points.forEach(function (p) { if (!p.provisional) s[p.month] = 1; });
      });
    });
    return Object.keys(s).sort();
  }

  var YEARS = ["2022", "2023", "2024", "2025", "2026"];
  var mixYear = "2026", mixTimer = null, TOP12 = [];
  function brandYearTotal(brand, mname, yr) {
    var b = brandIn(mname, brand); if (!b) return 0;
    return b.points.reduce(function (s, p) { return s + (!p.provisional && p.month.slice(0, 4) === yr ? (p.dollars || 0) : 0); }, 0);
  }
  function renderBars() {
    var el = $("mix-bars"); if (!el || !D) return;
    if (!TOP12.length) {
      var tot = {};
      MEDIA.forEach(function (m) {
        ((D.strata[m.name] || {}).brands || []).forEach(function (b) {
          tot[b.brand] = (tot[b.brand] || 0) + b.points.reduce(function (s, p) { return s + (p.provisional ? 0 : (p.dollars || 0)); }, 0);
        });
      });
      TOP12 = Object.keys(tot).sort(function (a, b) { return tot[b] - tot[a]; }).slice(0, 12);
      if (!selected) selected = TOP12[0];
    }
    $("mix-year-label").textContent = mixYear;
    var existing = el.querySelectorAll(".mix-row");
    if (existing.length === TOP12.length) {
      // paint in place so widths animate via CSS transition
      Array.prototype.forEach.call(existing, function (row) {
        var brand = row.getAttribute("data-brand");
        var per = MEDIA.map(function (m) { return brandYearTotal(brand, m.name, mixYear); });
        var grand = per.reduce(function (s, v) { return s + v; }, 0);
        row.querySelectorAll(".mix-seg").forEach(function (seg, i) {
          var pct = grand ? per[i] / grand * 100 : 0;
          seg.style.width = pct.toFixed(2) + "%";
          seg.textContent = pct >= 9 ? pct.toFixed(0) + "%" : "";
          seg.title = brand + " · " + MEDIA[i].name + " " + pct.toFixed(0) + "% ($" + (per[i] / 1e6).toFixed(0) + "M)";
        });
        row.querySelector(".mix-total").textContent = grand ? "$" + (grand / 1e6).toFixed(0) + "M" : "—";
        row.classList.toggle("selected", brand === selected);
      });
      return;
    }
    var legend = MEDIA.map(function (m) {
      return '<span class="flight-chip"><span class="flight-dot" style="background:' + m.color + '"></span>' + esc(m.name) + "</span>";
    }).join(" ");
    var h = '<p class="flight-legend">' + legend + "</p>";
    TOP12.forEach(function (brand) {
      var per = MEDIA.map(function (m) { return brandYearTotal(brand, m.name, mixYear); });
      var grand = per.reduce(function (s, v) { return s + v; }, 0);
      var segs = MEDIA.map(function (m, i) {
        var pct = grand ? per[i] / grand * 100 : 0;
        return '<span class="mix-seg" data-m="' + i + '" style="width:' + pct.toFixed(2) + "%;background:" + m.color + '" title="' + esc(brand) + " · " + esc(m.name) + " " + pct.toFixed(0) + "% ($" + (per[i] / 1e6).toFixed(0) + 'M)">' + (pct >= 9 ? pct.toFixed(0) + "%" : "") + "</span>";
      }).join("");
      h += '<div class="mix-row' + (brand === selected ? " selected" : "") + '" data-brand="' + esc(brand) + '" role="button" tabindex="0" aria-label="Drill into ' + esc(brand) + '">' +
        '<span class="mix-name">' + esc(brand) + '</span><span class="mix-track">' + segs + '</span>' +
        '<span class="mix-total">' + (grand ? "$" + (grand / 1e6).toFixed(0) + "M" : "—") + "</span></div>";
    });
    el.innerHTML = h;
    Array.prototype.forEach.call(el.querySelectorAll(".mix-row"), function (row) {
      function go() { selected = row.getAttribute("data-brand"); renderBars(); renderDetail(); }
      row.addEventListener("click", go);
      row.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
    });
  }
  function wireYearControls() {
    var slider = $("mix-year"), btn = $("mix-play");
    if (!slider || !btn) return;
    slider.addEventListener("input", function () { mixYear = slider.value; renderBars(); });
    btn.addEventListener("click", function () {
      if (mixTimer) { clearInterval(mixTimer); mixTimer = null; btn.textContent = "▶ Play"; return; }
      btn.textContent = "⏸ Pause";
      var i = YEARS.indexOf(mixYear);
      if (i >= YEARS.length - 1) i = -1;
      mixTimer = setInterval(function () {
        i++;
        if (i >= YEARS.length) { clearInterval(mixTimer); mixTimer = null; btn.textContent = "▶ Play"; return; }
        mixYear = YEARS[i]; slider.value = mixYear; renderBars();
      }, 1100);
    });
  }

  function renderDetail() {
    var el = $("mix-chart"); if (!el || !D || !selected) return;
    var mos = months();
    var totals = mos.map(function (mo) { return MEDIA.reduce(function (s, m) { return s + val(selected, m.name, mo); }, 0); });
    var mx = Math.max.apply(null, totals) * 1.08;
    var W = 880, H = 280, L = 52, Rr = 14, T = 14, B = 30;
    var X = function (j) { return L + (j + 0.5) / mos.length * (W - L - Rr); };
    var Y = function (v) { return T + (1 - v / mx) * (H - T - B); };
    var out = '<h4 class="mix-detail-title">' + esc(selected) + ' — monthly spend by media</h4><svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="Monthly spend by media for ' + esc(selected) + '">';
    [0, 0.5, 1].forEach(function (f) { var y = Y(mx * f); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="4" y="' + (y + 4) + '" font-size="11" fill="#555">$' + (mx * f / 1e6).toFixed(0) + "M</text>"; });
    var base = mos.map(function () { return 0; });
    MEDIA.forEach(function (m) {
      var top = base.map(function (b, j) { return b + val(selected, m.name, mos[j]); });
      var dTop = top.map(function (v, j) { return X(j).toFixed(1) + " " + Y(v).toFixed(1); }).join("L");
      var dBase = base.slice().reverse().map(function (v, k) { var j = mos.length - 1 - k; return X(j).toFixed(1) + " " + Y(v).toFixed(1); }).join("L");
      out += '<path fill="' + m.color + '" fill-opacity="0.85" d="M' + dTop + "L" + dBase + 'Z"><title>' + esc(m.name) + "</title></path>";
      base = top;
    });
    mos.forEach(function (mo, j) { if (j % 12 === 0) out += '<text x="' + X(j) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + mo.slice(0, 4) + "</text>"; });
    out += "</svg>";
    var grand = totals.reduce(function (s, v) { return s + v; }, 0);
    var shares = MEDIA.map(function (m) {
      var t = mos.reduce(function (s, mo) { return s + val(selected, m.name, mo); }, 0);
      return { name: m.name, color: m.color, tot: t };
    }).filter(function (x) { return x.tot > 0; });
    out += '<p class="flight-legend">' + shares.map(function (x) {
      return '<span class="flight-chip"><span class="flight-dot" style="background:' + x.color + '"></span>' + esc(x.name) + " $" + (x.tot / 1e6).toFixed(0) + "M (" + Math.round(x.tot / (grand || 1) * 100) + "%)</span>";
    }).join(" ") + "</p>";
    el.innerHTML = out;
    var note = $("mix-note");
    if (note) note.textContent = "MediaRadar/Vivvix (CU Boulder license), modelled gross spend, finalized months Jan 2022–Sep 2026. Categories are mutually exclusive. The pattern to see: the TV-first books (FanDuel) versus the digital-first challengers — same market, opposite media bets.";
  }

  fetch("data/meg_cpm.json").then(function (r) { return r.json(); }).then(function (d) {
    D = d; wireYearControls(); renderBars(); renderDetail();
  }).catch(function () {});
})();
