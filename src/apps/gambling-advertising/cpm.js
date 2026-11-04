/* Tab 6: CPM & competitiveness from meg_cpm.json */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function midx(y, m) { return y * 12 + (m - 1); }
  function mLabel(t) { var y = Math.floor(t / 12), m = t % 12 + 1; return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1] + " " + String(y).slice(2); }
  var state = { stratum: "Digital (total)", brand: "", range: "all", data: null };

  function seriesFor() {
    var st = state.data.strata[state.stratum];
    if (!st) return { pts: [], defined: false };
    // Provisional months (impressions not yet finalized) are dropped, never
    // plotted: their collapsed denominators inflate CPM ~20x. The builder
    // already omits them; this filter also guards stale cached data files.
    var src = (state.brand ? ((st.brands || []).filter(function (b) { return b.brand === state.brand; })[0] || {}).points || [] : st.industry).filter(function (p) { return !p.provisional; });
    return { pts: src.map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: st.cpm_defined ? p.cpm : (p.dollars / 1e6), prov: p.provisional }; }), defined: st.cpm_defined };
  }
  function draw() {
    var el = $("cpm-chart"); if (!el || !state.data) return;
    var s = seriesFor();
    var maxT = Math.max.apply(null, s.pts.map(function (p) { return p.t; }));
    var view = s.pts.filter(function (p) {
      if (state.range === "2026") return p.t >= midx(2026, 1);
      if (state.range === "12m") return p.t > maxT - 12;
      return true;
    }).filter(function (p) { return p.v != null; });
    if (!view.length) { el.innerHTML = '<p class="fineprint">No data in this range.</p>'; return; }
    var minT = Math.min.apply(null, view.map(function (p) { return p.t; }));
    var span = maxT - minT + 1;
    var W = 880, H = 290, L = 52, Rr = 14, T = 14, B = 32;
    // Scale to finalized months only: provisional impressions are unfinalized
    // and would inflate CPM (and squash the real line) if they set the axis.
    var fin = view.filter(function (p) { return !p.prov; });
    var mx = Math.max.apply(null, (fin.length ? fin : view).map(function (p) { return p.v; }).concat([1])) * 1.08;
    var X = function (t) { return L + (t - minT + 0.5) / span * (W - L - Rr); };
    var Y = function (v) { return T + (1 - v / mx) * (H - T - B); };
    var unit = s.defined ? "$" : "$M";
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="CPM by month">';
    [0, 0.5, 1].forEach(function (f) { var y = Y(mx * f); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="4" y="' + (y + 4) + '" font-size="11" fill="#555">' + unit + Math.round(mx * f * 10) / 10 + "</text>"; });
    var solid = view.filter(function (p) { return !p.prov; }), prov = view.filter(function (p) { return p.prov; });
    function path(pts, dash) {
      return pts.length ? '<path fill="none" stroke="#8a3b2e" stroke-width="2.4"' + (dash ? ' stroke-dasharray="5 4" opacity="0.65"' : "") + ' d="M' + pts.map(function (p) { return X(p.t).toFixed(1) + " " + Y(p.v).toFixed(1); }).join("L") + '"/>' : "";
    }
    out += path(solid, false) + path(prov, true);
    view.forEach(function (p) { out += '<circle cx="' + X(p.t) + '" cy="' + Y(p.v) + '" r="2.6" fill="#8a3b2e"><title>' + esc(p.label) + " · " + unit + p.v + (p.prov ? " (provisional — impressions not finalized)" : "") + "</title></circle>"; });
    // Two-tier time axis: labels thin out as the span grows (year-only at
    // multi-year spans), with unlabeled quarter ticks keeping the monthly
    // grain readable. Labeling every quarter at 57 months put 19 labels in
    // ~814px and they collided.
    var step = span > 36 ? 12 : span > 24 ? 6 : span > 12 ? 3 : 1;
    var seen = {};
    view.forEach(function (p) {
      var labeled = (p.t % step === 0);
      if (step >= 12 && p.t % 3 === 0) {
        out += '<line x1="' + X(p.t) + '" y1="' + (H - B) + '" x2="' + X(p.t) + '" y2="' + (H - B + (labeled ? 7 : 4)) + '" stroke="#999" stroke-width="1"/>';
      } else if (labeled) {
        out += '<line x1="' + X(p.t) + '" y1="' + (H - B) + '" x2="' + X(p.t) + '" y2="' + (H - B + 5) + '" stroke="#999" stroke-width="1"/>';
      }
      if (!labeled || seen[p.t]) return; seen[p.t] = 1;
      var lab = step >= 12 ? String(Math.floor(p.t / 12)) : mLabel(p.t);
      out += '<text x="' + X(p.t) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + lab + "</text>";
    });
    // Platform benchmark overlay: all-industry CPM, same $ axis (dashed grey).
    var bench = (state.stratum === "Digital (total)" ? ((state.data.benchmark || {}).platform || []) : []).filter(function (p) { return p.cpm != null; })
      .map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: p.cpm }; })
      .filter(function (p) { return p.t >= minT && p.t <= maxT; });
    if (bench.length) {
      out += '<path fill="none" stroke="#666" stroke-width="2" stroke-dasharray="6 4" d="M' + bench.map(function (p) { return X(p.t).toFixed(1) + " " + Y(p.v).toFixed(1); }).join("L") + '"/>';
      bench.forEach(function (p) { out += '<circle cx="' + X(p.t) + '" cy="' + Y(p.v) + '" r="2.2" fill="#666"><title>' + esc(p.label) + " · platform CPM $" + p.v + "</title></circle>"; });
    }
    el.innerHTML = out + "</svg>" + (bench.length ? '<p class="fineprint">Solid: gambling CPM. Dashed grey: all-industry (platform) CPM.</p>' : "");
    $("cpm-chart-title").firstChild.textContent = (state.brand || "Industry") + " CPM by month ";
    drawIndex(view, minT, maxT);
  }
  function drawIndex(view, minT, maxT) {
    var el = $("cpm-index-chart"); if (!el) return;
    var ix = state.data.indexes || {};
    var sets = [
      { key: "gambling-demand", label: "Gambling demand (spend)", pts: (ix.gambling || {}).demand || [], color: "#8a3b2e", dash: "" },
      { key: "gambling-supply", label: "Gambling supply (impressions)", pts: (ix.gambling || {}).supply || [], color: "#8a3b2e", dash: ' stroke-dasharray="2 3"' },
      { key: "platform-demand", label: "Platform demand (all-industry spend)", pts: (ix.platform || {}).demand || [], color: "#666", dash: "" },
      { key: "politics-demand", label: "Politics demand (spend)", pts: (ix.politics || {}).demand || [], color: "#2e5f8a", dash: "" }
    ].map(function (s) {
      s.pts = s.pts.map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), label: p.month, v: p.v }; })
        .filter(function (p) { return p.t >= minT && p.t <= maxT; });
      return s;
    }).filter(function (s) { return s.pts.length > 2; });
    if (!sets.length) { var f = el.closest("figure"); if (f) f.style.display = "none"; el.innerHTML = ""; return; }
    var fig = el.closest("figure"); if (fig) fig.style.display = "";
    var W = 880, H = 240, L = 52, Rr = 14, T = 14, B = 32;
    var span = maxT - minT + 1;
    var mx = Math.max.apply(null, sets.reduce(function (a, s) { return a.concat(s.pts.map(function (p) { return p.v; })); }, [120])) * 1.08;
    var X = function (t) { return L + (t - minT + 0.5) / span * (W - L - Rr); };
    var Y = function (v) { return T + (1 - v / mx) * (H - T - B); };
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="Demand supply index">';
    [0, 100, Math.round(mx / 2)].forEach(function (v) { var y = Y(v); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="' + (v === 100 ? "#333" : "#999") + '" stroke-opacity="' + (v === 100 ? ".45" : ".25") + '"/><text x="4" y="' + (y + 4) + '" font-size="11" fill="#555">' + v + "</text>"; });
    sets.forEach(function (s) {
      out += '<path fill="none" stroke="' + s.color + '" stroke-width="2.2"' + s.dash + ' d="M' + s.pts.map(function (p) { return X(p.t).toFixed(1) + " " + Y(p.v).toFixed(1); }).join("L") + '"/>';
      s.pts.forEach(function (p) { out += '<circle cx="' + X(p.t) + '" cy="' + Y(p.v) + '" r="2.2" fill="' + s.color + '"><title>' + esc(p.label) + " · " + s.label + ": " + p.v + "</title></circle>"; });
    });
    var step = span > 36 ? 12 : span > 24 ? 6 : span > 12 ? 3 : 1;
    var seen = {};
    (view || []).forEach(function (p) {
      if (p.t % step !== 0 || seen[p.t]) return; seen[p.t] = 1;
      var lab = step >= 12 ? String(Math.floor(p.t / 12)) : mLabel(p.t);
      out += '<text x="' + X(p.t) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + lab + "</text>";
    });
    el.innerHTML = out + "</svg>";
    $("cpm-index-legend").innerHTML = sets.map(function (s) {
      return '<span style="color:' + s.color + '">\u25aa</span> ' + esc(s.label);
    }).join(" &nbsp;·&nbsp; ") + " &nbsp;·&nbsp; demand \u00f7 supply = CPM index (" + esc(ix.base || "2022 monthly average = 100") + ")";
  }
  function renderTable() {
    var st = state.data.strata[state.stratum];
    var brandRows = st.brands || [];
    function wavg(pts) {
      var d = 0, i = 0;
      pts.forEach(function (p) { d += p.dollars || 0; i += p.impressions || 0; });
      return i ? Math.round(d / i * 1000 * 100) / 100 : null;
    }
    var data = brandRows.map(function (b) {
      var pts = b.points.filter(function (p) { return p.cpm != null && !p.provisional; });
      if (pts.length < 6) return null;
      var first = wavg(pts.slice(0, 3)), last = wavg(pts.slice(-3));
      if (!first || !last) return null;
      var spend = pts.reduce(function (s, p) { return s + (p.dollars || 0); }, 0);
      return { brand: b.brand, first: first, last: last, pct: (last / first - 1) * 100, spend: spend };
    }).filter(Boolean).sort(function (a, b) { return b.spend - a.spend; }).slice(0, 10)
      .sort(function (a, b) { return b.pct - a.pct; });
    if (!st.cpm_defined) {
      $("cpm-table").innerHTML = '<p class="fineprint">This medium has no published audience count in MediaRadar, so no price per 1,000 can be computed — the chart shows spend instead.</p>';
      return;
    }
    var mx = Math.max.apply(null, data.map(function (d) { return Math.abs(d.pct); }).concat([10]));
    var bars = data.map(function (d) {
      var w = Math.min(48, Math.abs(d.pct) / mx * 48);
      var pos = d.pct >= 0;
      return '<div class="brand-bar"><span class="bb-name">' + esc(d.brand) + '</span>' +
        '<span class="bb-track"><span class="bb-zero"></span>' +
        '<span class="bb-fill ' + (pos ? "up" : "down") + '" style="width:' + w.toFixed(1) + "%;" + (pos ? "left:50%" : "right:50%") + '"></span></span>' +
        '<span class="bb-val">' + (pos ? "+" : "") + d.pct.toFixed(0) + "% · $" + d.first + " → $" + d.last + "</span></div>";
    }).join("");
    $("cpm-table").innerHTML = '<h3 class="lib-h">Who pays more now, who pays less</h3>' +
      '<p class="deck">The ten biggest spenders, ranked by how their price of 1,000 showings moved from 2022 to today (first vs last 3 finalized months). Same market, opposite directions — the deflation was not shared equally.</p>' + bars;
  }
  function renderAll() {
    var d = state.data;
    var v = d.verdict["Digital (total)"] || {};
    $("cpm-verdict").textContent = "No. Showing a gambling ad 1,000 times costs $" + v.last3_avg + " today. At the 2024 peak it cost $" + v.peak3_avg + ". Prices surged as sportsbooks fought over newly legal states, then deflated " + Math.abs(v.pct_from_peak) + "% from the peak — advertisers now buy more attention per dollar, and they are spending it on volume instead (findings below).";
    $("cpm-strata").innerHTML = ["Digital (total)", "Digital Video", "Digital Display & Apps"].filter(function (s) { return d.strata[s]; }).map(function (s) {
      return '<button type="button" class="chip-btn" data-stratum="' + esc(s) + '" aria-pressed="' + (s === state.stratum) + '">' + esc(s) + "</button>";
    }).join(" ");
    $("cpm-strata").querySelectorAll("[data-stratum]").forEach(function (btn) {
      btn.addEventListener("click", function () { state.stratum = btn.getAttribute("data-stratum"); state.brand = ""; fillBrands(); renderAll(); });
    });
    draw(); renderTable(); renderFindings();
  }
  function fillBrands() {
    var st = state.data.strata[state.stratum];
    var sel = $("cpm-brand");
    sel.innerHTML = '<option value="">Industry (spend-weighted)</option>' + (st.brands || []).map(function (b) {
      return '<option value="' + esc(b.brand) + '"' + (b.brand === state.brand ? " selected" : "") + ">" + esc(b.brand) + "</option>";
    }).join("");
  }
  function fmt(n) { return n == null ? "—" : Number(n).toLocaleString("en-US"); }
fetch("data/meg_cpm.json", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) {
    state.data = d;
    fillBrands(); renderAll();
    $("cpm-brand").addEventListener("change", function () { state.brand = $("cpm-brand").value; draw(); });
    $("cpm-range").addEventListener("change", function () { state.range = $("cpm-range").value; draw(); });
  }).catch(function () {});

  /* ---- Findings for a reader, not an analyst: chart first, provenance second. ---- */
  function divergenceSvg() {
    var d = state.data; if (!d) return "";
    function pts(name) {
      var st = d.strata[name]; if (!st) return [];
      return st.industry.filter(function (p) { return p.cpm != null && !p.provisional; })
        .map(function (p) { var a = p.month.split("-"); return { t: midx(Number(a[0]), Number(a[1])), v: p.cpm, label: p.month }; });
    }
    var vid = pts("Digital Video"), dsp = pts("Digital Display & Apps");
    if (vid.length < 6 || dsp.length < 6) return "";
    var all = vid.concat(dsp);
    var minT = Math.min.apply(null, all.map(function (p) { return p.t; }));
    var maxT = Math.max.apply(null, all.map(function (p) { return p.t; }));
    var mx = Math.max.apply(null, all.map(function (p) { return p.v; })) * 1.1;
    var W = 880, H = 250, L = 46, Rr = 14, T = 16, B = 30, span = maxT - minT + 1;
    var X = function (t) { return L + (t - minT + 0.5) / span * (W - L - Rr); };
    var Y = function (v) { return T + (1 - v / mx) * (H - T - B); };
    function line(list, color, name, dy) {
      var last = list[list.length - 1];
      return '<path fill="none" stroke="' + color + '" stroke-width="2.4" d="M' + list.map(function (p) { return X(p.t).toFixed(1) + " " + Y(p.v).toFixed(1); }).join("L") + '"/>' +
        '<text x="' + (X(last.t) - 4) + '" y="' + (Y(last.v) + dy) + '" font-size="13" font-weight="700" fill="' + color + '" text-anchor="end">' + name + " $" + last.v + "</text>";
    }
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="Video versus display CPM">';
    [0, 0.5, 1].forEach(function (f) { var y = Y(mx * f); out += '<line x1="' + L + '" y1="' + y + '" x2="' + (W - Rr) + '" y2="' + y + '" stroke="#999" stroke-opacity=".25"/><text x="4" y="' + (y + 4) + '" font-size="11" fill="#555">$' + Math.round(mx * f) + "</text>"; });
    out += line(vid, "#8a3b2e", "Video", -10) + line(dsp, "#2e5f8a", "Display & apps", 18);
    for (var t = minT; t <= maxT; t += 12) out += '<text x="' + X(t) + '" y="' + (H - 8) + '" font-size="11" fill="#555" text-anchor="middle">' + Math.floor(t / 12) + "</text>";
    return out + "</svg>";
  }

  function volumeSvg(cohorts) {
    var W = 880, H = 240, L = 46, Rr = 14, T = 16, B = 30;
    var mx = Math.max.apply(null, cohorts.map(function (c) { return c.started; })) * 1.15;
    var bw = (W - L - Rr) / cohorts.length;
    var out = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%" role="img" aria-label="New gambling ads launched per year">';
    cohorts.forEach(function (c, i) {
      var h = c.started / mx * (H - T - B), x = L + i * bw + bw * 0.18, w = bw * 0.64;
      out += '<rect x="' + x.toFixed(1) + '" y="' + (H - B - h).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" fill="#8a3b2e"><title>' + c.year + ": " + c.started + " new ads</title></rect>" +
        '<text x="' + (x + w / 2).toFixed(1) + '" y="' + (H - B - h - 6).toFixed(1) + '" font-size="13" font-weight="700" fill="#333" text-anchor="middle">' + c.started + "</text>" +
        '<text x="' + (x + w / 2).toFixed(1) + '" y="' + (H - 8) + '" font-size="12" fill="#555" text-anchor="middle">' + c.year + "</text>";
    });
    return out + "</svg>";
  }

  var FOUND = { xp: null, claims: null };
  function renderFindings() {
    var xp = FOUND.xp, claims = FOUND.claims;
    var root = $("findings-root"); if (!root || !state.data) return;
    var p = (xp && xp.platforms) || {};
    var coh = (p.google_big || {}).cohorts || [];
    var meta = p.meta || {}, mus = p.meta_us || {}, tt = p.tiktok || {};
    var cells = claims && claims.auction_cpm && claims.auction_cpm.coverage ? claims.auction_cpm.coverage.cells_n : null;
    var h = '<h3 class="lib-h">Three things the data actually say</h3>';

    h += '<article class="finding"><h4>1 · Prices fell. Volume exploded.</h4>' +
      '<p class="deck">As attention got cheaper, advertisers answered with more ads, not smaller budgets. New gambling creatives launched on Google:</p>' +
      (coh.length ? volumeSvg(coh) : "") +
      '<p class="fineprint">What data got us here: Google Ads Transparency census — ' + fmt((p.google_big || {}).ads) + ' gambling ads across 16 US sportsbook and casino domains, first-shown dates 2021–2026, pulled November 2026. Meta\u2019s US library tells the same story: ' + fmt((mus.starts_by_year || {})["2026"]) + ' gambling ads started in 2026 alone. Read: the overspending risk in 2026 is sheer volume, not unit price.</p></article>';

    h += '<article class="finding"><h4>2 · Video held its price. Display collapsed.</h4>' +
      '<p class="deck">Display banners lost 31% from their 2024 peak and now go for about $13 per 1,000 showings. Video — the format you cannot scroll past — kept most of its value at about $44, roughly 3.4× the display price. Advertisers are paying up for the format that forces attention:</p>' +
      divergenceSvg() +
      '<p class="fineprint">What data got us here: MediaRadar/Vivvix monthly dollars ÷ impressions by format (CU Boulder license), finalized months, Jan 2022–today. Same source as the chart above.</p></article>';

    h += '<article class="finding"><h4>3 · Nobody publishes the real price.</h4>' +
      '<p class="deck">Every number above comes from a licensed vendor model, because the platforms themselves will not say what gambling ads cost:</p>' +
      '<div class="opacity-rows">' +
      '<p><strong>Google</strong> shows the ads and how long each ran — never spend, never audience.</p>' +
      '<p><strong>Meta</strong> must publish audience size in Europe: ' + fmt(meta.ads_with_reach) + ' German gambling ads reached ' + fmt(meta.reach_total) + ' people. In the US it publishes nothing.</p>' +
      '<p><strong>TikTok</strong> shows likes and a popularity score across ' + fmt(tt.ads) + ' current gambling ads — never spend.</p></div>' +
      (cells != null ? '<p class="fineprint">What data got us here: across every public ad library, we could assemble only ' + cells + ' ad-months where money and audience appear in the same row. A true market price for gambling attention cannot be computed from public data — which is why the licensed estimate above is labelled a model, not a measurement.</p>' : "") +
      '</article>';
    root.innerHTML = h;
  }

  Promise.all([
    fetch("data/meg_xplatform.json").then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
    fetch("data/cpm_claims.json").then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
  ]).then(function (all) { FOUND.xp = all[0]; FOUND.claims = all[1]; renderFindings(); }).catch(function () {});

  // Live lane (own-data, free Apify team): TikTok ad library Oct/Nov 2026 lower
  // bounds. Separate file, separate label — never merged into the licensed plot.
  fetch("data/tt_cpm_live.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (lv) {
    var el = $("cpm-live"); if (!el || !lv || !lv.months || !lv.months.length) return;
    function money(v) { return v == null ? "\u2014" : "$" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }); }
    var chips = lv.months.map(function (m) {
      var c = m.cpm_usd_lower_bound == null ? "no library spend published" : "CPM \u2265 $" + m.cpm_usd_lower_bound.toFixed(2);
      return '<span class="live-chip"><b>' + esc(m.month) + "</b> \u00b7 " + c +
             " \u00b7 " + m.n_books + " books \u00b7 " + m.n_ads + " ads</span>";
    }).join("");
    var rows = [];
    lv.months.forEach(function (m) {
      var pb = m.per_book || {};
      Object.keys(pb).sort(function (a, b) { return pb[b].impressions - pb[a].impressions; }).slice(0, 12).forEach(function (bk) {
        rows.push("<tr><td>" + esc(bk) + "</td><td>" + esc(m.month) + "</td><td>" +
                  Number(pb[bk].impressions).toLocaleString() + "</td><td>" + money(pb[bk].spend_usd) + "</td></tr>");
      });
    });
    var table = rows.length ? '<details class="live-details"><summary>Per-advertiser library detail (attributed to month of first public date)</summary><table class="live-table"><thead><tr><th>Advertiser</th><th>Attributed month</th><th>Library impressions</th><th>Spend (mid, USD eq.)</th></tr></thead><tbody>' + rows.join("") + "</tbody></table></details>" : "";
    el.innerHTML = '<p class="fineprint"><b>Live lane \u2014 TikTok ad library (months the licensed series above has not finalized yet).</b> ' +
      esc(lv.semantics || "") + '</p><p class="live-chips">' + chips + "</p>" + table;
  }).catch(function () {});
})();
