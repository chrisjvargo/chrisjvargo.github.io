/* Trends — live (data/demand_live.json): paper queries continued + brand demand + gated spend lanes */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function fmt(n) { return Number(n || 0).toLocaleString("en-US"); }
  var COLORS = ["#2f5d3a", "#c98a00", "#33566e", "#8a3b2e", "#5b4a7a", "#20706b", "#111111"];
  function lineChart(el, series, label) {
    if (!el || !series.length) return;
    var dates = {}; series.forEach(function (s) { s.points.forEach(function (p) { dates[p.d] = 1; }); });
    var xs = Object.keys(dates).sort(), W = 880, H = 280, L = 46, R = 14, T = 14, B = 32;
    var mx = Math.max.apply(null, series.flatMap(function (s) { return s.points.map(function (p) { return p.v; }); }).concat([1]));
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="' + esc(label) + '">';
    [0, 0.5, 1].forEach(function (f) { var y = T + (1 - f) * (H - T - B); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - R) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="6" y="' + (y + 4) + '" font-size="11" fill="#555">' + fmt(Math.round(mx * f)) + "</text>"; });
    series.forEach(function (s, si) {
      out += '<path fill="none" stroke="' + COLORS[si % COLORS.length] + '" stroke-width="2.2" d="M' + s.points.map(function (p) {
        return (L + xs.indexOf(p.d) * (W - L - R) / Math.max(1, xs.length - 1)).toFixed(1) + " " + (T + (1 - p.v / mx) * (H - T - B)).toFixed(1);
      }).join("L") + '"/>';
    });
    xs.forEach(function (d, i) { if (i % Math.max(1, Math.ceil(xs.length / 7)) === 0 || i === xs.length - 1) out += '<text x="' + (L + i * (W - L - R) / Math.max(1, xs.length - 1)) + '" y="' + (H - 8) + '" font-size="11" fill="#555">' + esc(d.slice(0, 7)) + "</text>"; });
    el.innerHTML = out + "</svg>" + '<p class="fineprint">' + series.map(function (s, si) { return '<span style="color:' + COLORS[si % COLORS.length] + '">■</span> ' + esc(s.name); }).join(" · ") + "</p>";
  }
  function midx(y, m) { return y * 12 + (m - 1); }
  function qMidx(q) { var p = q.split("-Q"); return midx(Number(p[0]), (Number(p[1]) - 1) * 3 + 1); }
  function mLabel(t) { var y = Math.floor(t / 12), m = t % 12 + 1; return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1] + " " + String(y).slice(2); }
  function longLine(el, pts, range, label) {
    if (!el) return;
    var all = pts.slice().sort(function (a, b) { return a.t - b.t; });
    var maxT = all[all.length - 1].t;
    var view = all.filter(function (p) {
      if (range === "paper") return p.t <= midx(2023, 12);
      if (range === "2026") return p.t >= midx(2026, 1);
      if (range === "12m") return p.t > maxT - 12;
      return true;
    });
    if (!view.length) { el.innerHTML = '<p class="fineprint">No data in this range.</p>'; return; }
    var minT = Math.min.apply(null, view.map(function (p) { return p.t; }));
    var span = maxT - minT + 1;
    var W = 880, H = 280, L = 46, Rr = 14, T = 14, B = 32;
    var X = function (t) { return L + (t - minT + 0.5) / span * (W - L - Rr); };
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="' + esc(label) + '">';
    ["paper", "live"].forEach(function (kind, ki) {
      var seg = view.filter(function (p) { return p.kind === kind; });
      if (!seg.length) return;
      var mx = Math.max.apply(null, seg.map(function (p) { return p.v; }).concat([1]));
      var col = kind === "live" ? "#8a3b2e" : "#2f5d3a";
      s += '<path fill="none" stroke="' + col + '" stroke-width="2.4" d="M' + seg.map(function (p) {
        return X(p.t).toFixed(1) + " " + (T + (1 - p.v / mx) * (H - T - B)).toFixed(1);
      }).join("L") + '"/>';
      seg.forEach(function (p) { s += '<circle cx="' + X(p.t) + '" cy="' + (T + (1 - p.v / mx) * (H - T - B)) + '" r="2.6" fill="' + col + '"><title>' + esc(p.label) + " · " + fmt(Math.round(p.v)) + "</title></circle>"; });
    });
    var seen = {};
    view.forEach(function (p) {
      var key, lab;
      if (span > 48) { if (p.t % 12 !== 0) return; key = "y" + Math.floor(p.t / 12); lab = String(Math.floor(p.t / 12)); }
      else if (span > 18) { if (p.t % 3 !== 0) return; key = "q" + p.t; lab = Math.floor(p.t / 12) + "-Q" + (Math.floor((p.t % 12) / 3) + 1); }
      else { key = "m" + p.t; lab = mLabel(p.t); }
      if (seen[key]) return; seen[key] = 1;
      s += '<text x="' + X(p.t) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + lab + "</text>";
    });
    el.innerHTML = s + "</svg>" + '<p class="fineprint"><span style="color:#2f5d3a">■</span> paper quarterly · <span style="color:#8a3b2e">■</span> live monthly — each indexed within its own window</p>';
  }

  Promise.all([
    fetch("data/demand_live.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
    fetch("data/study1.json", { cache: "no-store" }).then(function (r) { return r.json(); })
  ]).then(function (res) {
    var d = res[0], s1 = res[1];
    $("dm-asof").textContent = d.trends_live.as_of || "";
    var longPts = (d.trends_live.us_index || []).map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: p.value, kind: "live" }; });
    var rangeSel = $("dm-range");
    function drawLong() {
      longLine($("dm-long-chart"), longPts, rangeSel ? rangeSel.value : "all", "Help-seeking searches, paper to live");
      var gel = $("dm-general-chart");
      if (gel) {
        var gen = ((d.trends_general || {}).us_index || []).map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: p.value, kind: "live" }; });
        longLine(gel, gen, rangeSel ? rangeSel.value : "all", "General gambling attention");
      }
    }
    if (rangeSel) rangeSel.addEventListener("change", drawLong);
    drawLong();
    lineChart($("dm-brand-chart"), (d.brand_trends || []).map(function (b) { return { name: b.term, points: b.points.map(function (p) { return { d: p.date, v: p.value }; }) }; }), "Brand search demand");

    // State drill-down (compulsory): paper state quarters + live state months
    var sel = $("dm-geo");
    var states = (s1.state_totals || []).map(function (b) { return b.state; });
    sel.innerHTML = states.map(function (g) { return '<option value="' + esc(g) + '">' + esc(g) + "</option>"; }).join("");
    function monthlyMean(series) {
      var by = {};
      (series.points || []).forEach(function (p) { (by[p.month] = by[p.month] || []).push(p.value); });
      return Object.keys(by).sort().map(function (m) { var a = m.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: m, v: by[m].reduce(function (x, y) { return x + y; }, 0) / by[m].length, kind: "live" }; });
    }
    function drawGeo() {
      var st = sel.value;
      var live = (d.state_series || []).filter(function (s) { return s.geo === "US-" + st; })[0];
      var pts = live ? monthlyMean(live) : [];
      longLine($("dm-state-chart"), pts, "all", st + " help-seeking searches");
    }
    if (states.length) { sel.addEventListener("change", drawGeo); drawGeo(); }
    function fmtMoney(n) { return n >= 1e9 ? "$" + (n / 1e9).toFixed(2) + "B" : n >= 1e6 ? "$" + (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? "$" + (n / 1e3).toFixed(0) + "K" : "$" + Math.round(n); }
    $("sp-lanes").innerHTML = (d.spend_lanes || []).map(function (l, li) {
      if (!l.available) return '<div class="meg-callout"><p class="big" style="font-size:19px">' + esc(l.lane) + ' — <span style="color:#8a3b2e">not displayed</span></p><p class="deck" style="margin:0;font-size:15px">' + esc(l.why) + "</p></div>";
      var top = (l.brands || []).slice(0, 10);
      var rows = top.map(function (b) {
        return "<tr><td>" + esc(b.brand) + "</td>" + (l.months || []).map(function (m) {
          var p = (b.points || []).filter(function (x) { return x.month === m; })[0];
          return '<td class="num">' + (p ? fmtMoney(p.value) : "—") + "</td>";
        }).join("") + '<td class="num"><strong>' + fmtMoney(b.total) + "</strong></td></tr>";
      }).join("");
      return '<div class="meg-callout"><p class="big" style="font-size:19px">' + esc(l.lane) + '</p>' +
        '<p class="deck" style="margin:0 0 8px;font-size:15px">Total ' + fmtMoney(l.total_usd) + " across " + (l.brands || []).length + " gambling advertisers · " + esc((l.months || [])[0] + " → " + (l.months || [])[(l.months || []).length - 1]) + ' (monthly, US, all media). ' + esc(l.source) + "</p>" +
        '<div id="sp-chart-' + li + '"></div>' +
        '<div class="meg-tablewrap"><table class="meg-table"><thead><tr><th>Advertiser</th>' + (l.months || []).map(function (m) { return "<th>" + esc(m) + "</th>"; }).join("") + "<th>Total</th></tr></thead><tbody>" + rows + "</tbody></table></div></div>";
    }).join("");
    (d.spend_lanes || []).forEach(function (l, li) {
      if (!l.available) return;
      var el = $("sp-chart-" + li);
      if (el) lineChart(el, (l.brands || []).slice(0, 6).map(function (b) {
        return { name: b.brand, points: (b.points || []).map(function (p) { return { d: p.month, v: p.value / 1e6 }; }) };
      }), "Monthly gambling ad spend by advertiser ($M)");
    });
    $("dm-methods").textContent = d.methods || "";
    $("dm-topterms").innerHTML = (d.trends_live.top_terms || []).slice(0, 8).map(function (t) {
      return "<tr><td>" + esc(t.term) + "</td><td class=num>" + fmt(Math.round(t.total)) + "</td></tr>";
    }).join("");
  }).catch(function () {});
})();
