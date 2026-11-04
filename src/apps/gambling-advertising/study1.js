/* Study 1 + Spend tabs (final paper data, data/study1.json) */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function money(n) { if (n >= 1e9) return "$" + (n / 1e9).toFixed(2) + "B"; if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M"; if (n >= 1e3) return "$" + Math.round(n / 1e3) + "k"; return "$" + n; }
  function fmt(n) { return Number(n || 0).toLocaleString("en-US"); }
  function ptxt(p) { return p < 0.001 ? "p < .001" : "p = " + p.toFixed(3).replace(/^0/, ""); }

  function dualChart(el, pts, legalDate, label) {
    if (!el || !pts.length) return;
    var W = 880, H = 300, L = 64, R = 56, T = 14, B = 34;
    var ms = Math.max.apply(null, pts.map(function (p) { return p.spend; }).concat([1]));
    var mt = Math.max.apply(null, pts.map(function (p) { return p.trends; }).concat([1]));
    var bw = (W - L - R) / pts.length;
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="' + esc(label) + '">';
    [0, 0.5, 1].forEach(function (f) {
      var y = T + (1 - f) * (H - T - B);
      s += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - R) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/>' +
        '<text x="6" y="' + (y + 4) + '" font-size="11" fill="#555">' + money(ms * f) + '</text>' +
        '<text x="' + (W - R + 6) + '" y="' + (y + 4) + '" font-size="11" fill="#8a5a00">' + fmt(Math.round(mt * f)) + "</text>";
    });
    pts.forEach(function (p, i) {
      var h = (p.spend / ms) * (H - T - B);
      s += '<rect x="' + (L + i * bw + 1) + '" y="' + (H - B - h) + '" width="' + Math.max(2, bw - 2) + '" height="' + h + '" fill="#2f5d3a"><title>' + esc(p.q) + " · spend " + money(p.spend) + " · searches idx " + fmt(p.trends) + "</title></rect>";
    });
    s += '<path fill="none" stroke="#c98a00" stroke-width="2.5" d="M' + pts.map(function (p, i) {
      return (L + i * bw + bw / 2).toFixed(1) + " " + (T + (1 - p.trends / mt) * (H - T - B)).toFixed(1);
    }).join("L") + '"/>';
    if (legalDate) {
      var li = pts.findIndex(function (p) { return p.q >= legalDate.slice(0, 4) + "-Q" + (Math.floor((Number(legalDate.slice(5, 7)) - 1) / 3) + 1); });
      if (li >= 0) { var x = L + li * bw; s += '<line x1="' + x + '" y1="' + T + '" x2="' + x + '" y2="' + (H - B) + '" stroke="#111" stroke-dasharray="4 3"/><text x="' + (x + 4) + '" y="' + (T + 11) + '" font-size="11" fill="#111">sports betting legal ' + esc(legalDate) + "</text>"; }
    }
    pts.forEach(function (p, i) { if (i % 8 === 0 || i === pts.length - 1) s += '<text x="' + (L + i * bw) + '" y="' + (H - 8) + '" font-size="11" fill="#555">' + esc(p.q) + "</text>"; });
    el.innerHTML = s + "</svg>";
  }

  function midx(y, m) { return y * 12 + (m - 1); }
  function qMidx(q) { var p = q.split("-Q"); return midx(Number(p[0]), (Number(p[1]) - 1) * 3 + 1); }
  function mLabel(t) { var y = Math.floor(t / 12), m = t % 12 + 1; return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1] + " " + String(y).slice(2); }
  function longBars(el, pts, range) {
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
    var W = 880, H = 300, L = 64, Rr = 14, T = 14, B = 34;
    var mx = Math.max.apply(null, view.map(function (p) { return p.v; }).concat([1]));
    var X = function (t) { return L + (t - minT + 0.5) / span * (W - L - Rr); };
    var bw = Math.max(2, (W - L - Rr) / span * 0.72);
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="US gambling ad spend, longitudinal">';
    [0, 0.5, 1].forEach(function (f) { var y = T + (1 - f) * (H - T - B); s += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="6" y="' + (y + 4) + '" font-size="11" fill="#555">' + money(mx * f) + "</text>"; });
    view.forEach(function (p) {
      var h = p.v / mx * (H - T - B);
      s += '<rect x="' + (X(p.t) - bw / 2) + '" y="' + (H - B - h) + '" width="' + bw + '" height="' + h + '" fill="' + (p.kind === "live" ? "#8a3b2e" : "#2f5d3a") + '"><title>' + esc(p.label) + " · " + money(p.v) + (p.kind === "live" ? " · live monthly" : " · paper quarterly") + "</title></rect>";
    });
    // intelligent x unit: years / quarters / months by span
    var seen = {};
    view.forEach(function (p) {
      var key, lab;
      if (span > 48) { if (p.t % 12 !== 0) return; key = "y" + Math.floor(p.t / 12); lab = String(Math.floor(p.t / 12)); }
      else if (span > 18) { if (p.t % 3 !== 0) return; key = "q" + p.t; lab = Math.floor(p.t / 12) + "-Q" + (Math.floor((p.t % 12) / 3) + 1); }
      else { key = "m" + p.t; lab = mLabel(p.t); }
      if (seen[key]) return; seen[key] = 1;
      s += '<text x="' + X(p.t) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + lab + "</text>";
    });
    el.innerHTML = s + "</svg>" + '<p class="fineprint"><span style="color:#2f5d3a">■</span> paper quarterly (Vivvix) · <span style="color:#8a3b2e">■</span> live monthly (MediaRadar, pulled today)</p>';
  }

  Promise.all([
    fetch("data/study1.json").then(function (r) { return r.json(); }),
    fetch("data/demand_live.json").then(function (r) { return r.json(); })
  ]).then(function (res) {
    var d = res[0], dm = res[1];
    var lane = (dm.spend_lanes || [])[0] || {};
    var pts = d.us.map(function (p) { return { t: qMidx(p.q), label: p.q, v: p.spend, kind: "paper" }; })
      .concat((lane.monthly_totals || []).map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: p.value, kind: "live" }; }));
    var rangeSel = $("sp-range");
    function drawLong() { longBars($("sp-long-chart"), pts, rangeSel ? rangeSel.value : "all"); }
    if (rangeSel) rangeSel.addEventListener("change", drawLong);
    drawLong();
    var tot = d.us.reduce(function (a, p) { return a + p.spend; }, 0);
    $("s1-keyline").textContent = "41 states · 1,640 state-quarters · " + money(tot) + " tracked gambling ad spend 2014–2023 (Vivvix).";
    var sel = $("s1-state");
    sel.innerHTML = d.state_totals.map(function (b) {
      var now = (d.states_now || {})[b.state];
      return '<option value="' + esc(b.state) + '">' + esc(b.state) + " — " + (now ? money(now.total_2026) + " in 2026 (DMA)" : money(b.spend_total) + " (paper)") + "</option>";
    }).join("");
    function drawState() {
      var st = sel.value, meta = d.state_totals.filter(function (b) { return b.state === st; })[0] || {};
      var now = (d.states_now || {})[st];
      if (now && now.months && now.months.length) {
        var pts = now.months.map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: p.total, kind: "live" }; });
        longBars($("s1-state-now-chart"), pts, "all");
        var last = now.months[now.months.length - 1];
        $("s1-state-now-meta").textContent = st + ": " + money(now.total_2026) + " DMA-attributed gambling ad spend in 2026 · " + money(now.total_all) + " Jan 2024–Nov 2026 · latest month " + last.month + " " + money(last.total) + " (top: " + (last.top_brand || "—") + "). " + now.source;
      } else {
        $("s1-state-now-chart").innerHTML = '<p class="fineprint">No current DMA-attributed spend pulled for this state.</p>';
        $("s1-state-now-meta").textContent = "";
      }
      dualChart($("s1-state-chart"), d.states[st] || [], meta.legal, st + " ad spend and help-seeking searches");
      $("s1-state-meta").textContent = st + ": " + money(meta.spend_total) + " total spend · " + money(meta.spend_2023) + " in 2023 · searches idx " + fmt(meta.trends_total) + (meta.legal ? " · sports betting legal " + meta.legal : " · not legal in window");
    }
    sel.addEventListener("change", drawState); drawState();
    var names = { spend100k_c: "Ad spend (+$100k/state-quarter)", legal_status: "Sports betting legal (yes/no)", time_spend: "Spend × time (strengthening)" };
    $("s1-models").innerHTML = d.models.map(function (m) {
      var sig = m.p < 0.05;
      return '<div class="meg-find"><p class="n" style="font-size:22px">' + (m.estimate > 0 ? "+" : "") + m.estimate + '</p><p class="l"><strong>' + esc(names[m.term] || m.term) + "</strong> · " + esc(m.model) + " · " + ptxt(m.p) + (sig ? "" : " · not significant") + "</p></div>";
    }).join("");
  }).catch(function () {});
})();
