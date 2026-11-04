/* Creative pressure: stacked ads-in-flight per month by brand (Google Transparency).
   Approximation, labelled: 1 creative = 1 unit for each month firstShown..lastShown.
   NOT impressions, clicks, or spend — Google publishes none of those. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  var COLORS = ["#8a3b2e", "#2e5f8a", "#c08a3e", "#4a7a4f", "#6b4a8a", "#8a8a3b", "#3b8a7a", "#999999"];
  fetch("data/meg_flighting.json").then(function (r) { return r.json(); }).then(function (d) {
    var el = $("flight-chart"); if (!el) return;
    var months = d.months, advs = d.advertisers;
    var W = 880, H = 300, L = 44, Rr = 14, T = 14, B = 30;
    var totals = months.map(function (_, j) { return advs.reduce(function (s, a) { return s + a.live[j]; }, 0); });
    var mx = Math.max.apply(null, totals) * 1.08;
    var X = function (j) { return L + (j + 0.5) / months.length * (W - L - Rr); };
    var Y = function (v) { return T + (1 - v / mx) * (H - T - B); };
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="Gambling ads in flight per month by brand">';
    [0, 0.5, 1].forEach(function (f) { var y = Y(mx * f); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="4" y="' + (y + 4) + '" font-size="11" fill="#555">' + Math.round(mx * f) + "</text>"; });
    var base = months.map(function () { return 0; });
    advs.forEach(function (a, ai) {
      var top = base.map(function (b, j) { return b + a.live[j]; });
      var dTop = top.map(function (v, j) { return X(j).toFixed(1) + " " + Y(v).toFixed(1); }).join("L");
      var dBase = base.slice().reverse().map(function (v, k) { var j = months.length - 1 - k; return X(j).toFixed(1) + " " + Y(v).toFixed(1); }).join("L");
      out += '<path fill="' + COLORS[ai % COLORS.length] + '" fill-opacity="0.82" stroke="none" d="M' + dTop + "L" + dBase + 'Z"><title>' + esc(a.name) + "</title></path>";
      base = top;
    });
    months.forEach(function (m, j) { if (j % 12 === 0) out += '<text x="' + X(j) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + m.slice(0, 4) + "</text>"; });
    out += "</svg>";
    var legend = advs.map(function (a, ai) {
      var now = a.live[a.live.length - 1];
      return '<span class="flight-chip"><span class="flight-dot" style="background:' + COLORS[ai % COLORS.length] + '"></span>' + esc(a.name) + " · " + now + " live now</span>";
    }).join(" ");
    el.innerHTML = out + '<p class="flight-legend">' + legend + "</p>";
    var note = $("flight-note");
    if (note) note.textContent = d.method + " Census of " + d.ads_n + " ads across 16 gambling domains (Google Ads Transparency, pulled Nov 2026). Early years are understated: only ads still listed today appear, so short-lived old ads are missing. Fanatics totals include its retail storefront — Google does not separate them. An ad kept live for years is budget that kept being renewed; that persistence, not invented view counts, is the signal.";
  }).catch(function () {});

  /* MediaRadar counterpart: stacked modelled impressions by advertiser. */
  function stacked(el, months, advs, yFmt, aria) {
    if (!el || !months.length) return;
    var W = 880, H = 300, L = 44, Rr = 14, T = 14, B = 30;
    var totals = months.map(function (_, j) { return advs.reduce(function (s, a) { return s + a.live[j]; }, 0); });
    var mx = Math.max.apply(null, totals) * 1.08;
    var X = function (j) { return L + (j + 0.5) / months.length * (W - L - Rr); };
    var Y = function (v) { return T + (1 - v / mx) * (H - T - B); };
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="' + aria + '">';
    [0, 0.5, 1].forEach(function (f) { var y = Y(mx * f); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="4" y="' + (y + 4) + '" font-size="11" fill="#555">' + yFmt(mx * f) + "</text>"; });
    var base = months.map(function () { return 0; });
    advs.forEach(function (a, ai) {
      var top = base.map(function (b, j) { return b + a.live[j]; });
      var dTop = top.map(function (v, j) { return X(j).toFixed(1) + " " + Y(v).toFixed(1); }).join("L");
      var dBase = base.slice().reverse().map(function (v, k) { var j = months.length - 1 - k; return X(j).toFixed(1) + " " + Y(v).toFixed(1); }).join("L");
      out += '<path fill="' + COLORS[ai % COLORS.length] + '" fill-opacity="0.82" stroke="none" d="M' + dTop + "L" + dBase + 'Z"><title>' + esc(a.name) + "</title></path>";
      base = top;
    });
    months.forEach(function (m, j) { if (j % 12 === 0) out += '<text x="' + X(j) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + m.slice(0, 4) + "</text>"; });
    out += "</svg>";
    var legend = advs.map(function (a, ai) {
      var li = a.live.length - 1;
      while (li > 0 && !a.live[li]) li--;
      return '<span class="flight-chip"><span class="flight-dot" style="background:' + COLORS[ai % COLORS.length] + '"></span>' + esc(a.name) + " · " + yFmt(a.live[li]) + "/mo (" + months[li] + ")</span>";
    }).join(" ");
    el.innerHTML = out + '<p class="flight-legend">' + legend + "</p>";
  }

  fetch("data/meg_cpm.json").then(function (r) { return r.json(); }).then(function (d) {
    var el = $("mr-pressure-chart"); if (!el) return;
    var brands = ((d.strata["All media"] || {}).brands || []).slice();
    brands.forEach(function (b) {
      b._tot = b.points.reduce(function (s, p) { return s + (p.provisional ? 0 : (p.impressions || 0)); }, 0);
    });
    brands.sort(function (a, b) { return b._tot - a._tot; });
    var top = brands.slice(0, 7), rest = brands.slice(7);
    var monthSet = {};
    brands.forEach(function (b) { b.points.forEach(function (p) { if (!p.provisional) monthSet[p.month] = 1; }); });
    var months = Object.keys(monthSet).sort();
    function seriesFor(list) {
      return months.map(function (mo) {
        return list.reduce(function (s, b) {
          var p = b.points.filter(function (x) { return x.month === mo; })[0];
          return s + (p && !p.provisional ? (p.impressions || 0) : 0);
        }, 0) / 1e9;
      });
    }
    var advs = top.map(function (b) { return { name: b.brand, live: seriesFor([b]) }; });
    advs.push({ name: "All other advertisers", live: seriesFor(rest) });
    stacked(el, months, advs, function (v) { return (v >= 0.1 ? v.toFixed(1) : v.toFixed(2)) + "B"; }, "MediaRadar modelled impressions per month by advertiser");
    var note = $("mr-pressure-note");
    if (note) note.textContent = "MediaRadar/Vivvix (CU Boulder license), all-media modelled impressions, finalized months only (Oct–Nov 2026 excluded until finalized). The two charts measure different things on purpose: Google counts creatives kept in flight, MediaRadar estimates showings. DraftKings and FanDuel dominate delivered volume even where their Google creative count is thin — they buy reach, not variety.";
  }).catch(function () {});
})();
