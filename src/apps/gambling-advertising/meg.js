/* Creatives: lane filter (Panel observation / TikTok current) + brand filter + metadata.
   Panel cards carry diary aggregates; TikTok cards carry library fields.
   Fields the library does not export are labelled, never invented. */
(function () {
  "use strict";
  var panel = document.getElementById("panel-evidence");
  if (!panel) return;
  var wall = document.getElementById("meg-gallery");
  var metaBox = document.getElementById("meg-panel-meta");
  var brandSel = document.getElementById("meg-brand");
  var sortSel = document.getElementById("meg-sort");
  var countEl = document.getElementById("meg-count");
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  var PANEL_MEDIA = [
    { file: "dk_lebron.mp4", poster: "dk_poster.jpg", brand: "DraftKings", kind: "video" },
    { file: "dk_poster.jpg", brand: "DraftKings", kind: "still" },
    { file: "metawin_btc.jpg", brand: "MetaWin", kind: "still" },
    { file: "paripesa_a.jpg", brand: "Paripesa", kind: "still" },
    { file: "paripesa_b.jpg", brand: "Paripesa", kind: "still" },
    { file: "bybit_spot.jpg", brand: "Bybit", kind: "still" }
  ];
  var state = { lane: "tiktok", brand: "", sort: "reach", tt: null, pn: null, page: 1, query: "" };

  function brandAgg(brand) {
    var g = (state.pn && state.pn.gambling) || {};
    return (g.brands || []).filter(function (b) { return b.brand.toLowerCase() === brand.toLowerCase(); })[0] || null;
  }
  function libCard(r) {
    var media = !r.media_file
      ? '<div class="meg-textcard"><p>' + esc(r.body || r.title || "Library-matched creative — copy only, media not banked") + "</p></div>"
      : r.media_kind === "video"
      ? '<video muted loop playsinline preload="none" src="creative/' + esc(r.media_file) + '" aria-label="' + esc(r.brand) + ' library-matched creative"></video>'
      : '<img src="creative/' + esc(r.media_file) + '" alt="" loading="lazy">';
    return '<figure class="meg-card" data-lane="panel">' + media +
      '<figcaption><strong>' + esc(r.brand) + '</strong> · Panel observation · 2024 · library-matched<br>' +
      "Observed " + r.impressions + "× · " + r.people + " people · " + r.clicks + " clicks" +
      (r.library_score ? " · match score " + r.library_score : "") +
      (r.engagement_views ? " · " + Number(r.engagement_views).toLocaleString("en-US") + " platform views" : "") +
      "<br>" + esc(r.title || r.body || "") + "</figcaption></figure>";
  }
  function panelCard(m) {
    var a = brandAgg(m.brand);
    var meta = a
      ? "Observed " + a.impressions + "× · " + (a.users_hint || "—") + " people · " + a.clicks + " clicks (brand diary total)"
      : "Panel-observed still · brand diary total not matched";
    var burden = "Burden: gambling exposures concentrate in the heaviest feeds (top 10% of panelists = 76.7%) — aggregate flag, not per-person";
    var media = m.kind === "video"
      ? '<video muted loop playsinline preload="none" poster="creative/' + m.poster + '" src="creative/' + m.file + '" aria-label="' + esc(m.brand) + ' panel creative"></video>'
      : '<img src="creative/' + m.file + '" alt="" loading="lazy">';
    return '<figure class="meg-card" data-lane="panel">' + media +
      '<figcaption><strong>' + esc(m.brand) + '</strong> · Panel observation · 2024<br>' + esc(meta) + "<br>" + esc(burden) + "</figcaption></figure>";
  }
  function ttCard(c) {
    var e = (state.eng || {})[c.id] || {};
    var engParts = [];
    var likes = c.likes != null ? c.likes : e.likes;
    if (likes != null) engParts.push("♥ " + Number(likes).toLocaleString("en-US") + " likes");
    if (e.shares != null) engParts.push(Number(e.shares).toLocaleString("en-US") + " shares");
    if (e.favorites) engParts.push(Number(e.favorites).toLocaleString("en-US") + " favorites");
    if (e.ctr_score != null) engParts.push("CTR score " + e.ctr_score + " (position-derived, not a rate)");
    if (e.reach_band) engParts.push("library audience " + e.reach_band);
    if (e.first_shown) engParts.push("shown " + e.first_shown + (e.last_shown ? " → " + e.last_shown : ""));
    var eng = engParts.length ? engParts.join(" · ") + (likes != null || e.shares != null ? " — platform-reported at pull" : " — ad-library record (no engagement published)") : (c.stat_line || "no engagement row at pull");
    var obj = c.objective_label ? esc(c.objective_label) : (e.objective_label ? esc(e.objective_label) : "objective not in export");
    var spend = c.spend_est_usd != null ? "est. spend $" + Number(c.spend_est_usd).toLocaleString("en-US") + " (tier-band estimate, not measured billing)" : "no public spend figure";
    return '<figure class="meg-card" data-lane="tiktok"><video muted loop playsinline preload="none" poster="creative/' +
      esc(c.poster) + '" src="creative/' + esc(c.media_file) + '" aria-label="' + esc(c.brand) + " ad " + esc(c.id || "") + '"></video>' +
      '<figcaption><strong>' + esc(c.brand) + "</strong> · TikTok · " + esc(c.src || "") +
      (c.dur ? " · " + Math.round(c.dur) + "s" : "") + "<br>" + esc(eng) + "<br>" + obj + " · " + spend +
      (c.captured ? "<br>captured " + esc(c.captured) : "") + "</figcaption></figure>";
  }
  function feedCard(r) {
    var media = r.media_kind === "video"
      ? '<video muted loop playsinline preload="none" src="creative/' + esc(r.media_file) + '" aria-label="' + esc(r.advertiser) + ' panel creative"></video>'
      : '<img src="creative/' + esc(r.media_file) + '" alt="" loading="lazy">';
    return '<figure class="meg-card" data-lane="panel">' + media +
      '<figcaption><strong>' + esc(r.advertiser) + "</strong> · " + esc(r.platform) + " · Panel feed 2024<br>" +
      "Observed " + r.impressions + "× · " + r.people + " people · " + r.clicks + " clicks" +
      (r.views ? " · " + Number(r.views).toLocaleString("en-US") + " platform views" : "") +
      (r.vertical ? "<br>" + esc(r.vertical) : "") +
      (r.library_matched ? " · library-matched" : "") + "</figcaption></figure>";
  }
  function panelMeta() {
    if (state.lane === "tiktok") { metaBox.innerHTML = ""; return; }
    var g = (state.pn && state.pn.gambling) || {};
    var brands = (g.brands || []).filter(function (b) { return !state.brand || b.brand === state.brand; }).slice(0, 6);
    if (!brands.length) { metaBox.innerHTML = ""; return; }
    metaBox.innerHTML = '<table class="meg-table meg-panel-table"><tr><th>Panel brand (2024 diary)</th><th class="num">Times observed</th><th class="num">People</th><th class="num">Clicks</th><th>Most-observed creative</th><th>Overburden flag</th></tr>' +
      brands.map(function (b) {
        var top = (b.top_creatives || [])[0] || {};
        return "<tr><td>" + esc(b.brand) + '</td><td class="num">' + b.impressions + '</td><td class="num">' + (b.users_hint || "—") + '</td><td class="num">' + b.clicks +
          "</td><td>" + esc(top.platform || "") + (top.text ? " — " + esc(String(top.text).slice(0, 90)) : "") +
          "</td><td>Heaviest-decile feeds carry 76.7% of gambling exposures (aggregate)</td></tr>";
      }).join("") + "</table>";
  }
  function render() {
    var cards = [];
    if (state.lane !== "tiktok") {
      var feed = (state.feed && state.feed.records) || [];
      var libs = (state.lib && state.lib.records) || [];
      if (feed.length) feed.forEach(function (r) {
        if (state.brand && r.advertiser !== state.brand) return;
        if (state.query && (r.advertiser + " " + (r.text || "")).toLowerCase().indexOf(state.query) < 0) return;
        cards.push({ html: feedCard(r), reach: r.impressions || 0, lane: "panel" });
      });
      else if (libs.length) libs.forEach(function (r) { if (!state.brand || r.brand === state.brand) cards.push({ html: libCard(r), reach: r.impressions || 0, lane: "panel", id: r.library_ad_id }); });
      else PANEL_MEDIA.forEach(function (m) { if (!state.brand || m.brand === state.brand) cards.push({ html: panelCard(m), reach: (brandAgg(m.brand) || {}).impressions || 0, lane: "panel" }); });
    }
    if (state.lane !== "panel") {
      var seenIds = {};
      (state.tt || []).forEach(function (c) {
        if (!c.media_file) return;
        seenIds[c.id] = 1;
        if (!state.brand || c.brand === state.brand) cards.push({ html: ttCard(c), reach: c.likes || 0, lane: "tiktok", id: c.id });
      });
      ((state.dsa && state.dsa.records) || []).forEach(function (c) {
        if (seenIds[c.id]) return;
        if (state.brand && c.brand !== state.brand) return;
        if (state.query && (c.brand + " " + (c.title || "")).toLowerCase().indexOf(state.query) < 0) return;
        var eng = (state.eng || {})[c.id] || {};
        var cap = "<strong>" + esc(c.brand) + "</strong> · TikTok UK library · 2026<br>" +
          (c.audience ? "library audience " + esc(c.audience) + " · " : "") +
          (c.first ? "shown " + esc(c.first) + (c.last ? " → " + esc(c.last) : "") : "") +
          (eng.likes != null ? "<br>♥ " + Number(eng.likes).toLocaleString("en-US") + " likes — platform-reported" : "<br>ad-library record (no engagement published)");
        cards.push({ html: '<figure class="meg-card" data-lane="tiktok"><video muted loop playsinline preload="none" src="creative/' + esc(c.media_file) + '" aria-label="' + esc(c.brand) + " library ad " + esc(c.id) + '"></video><figcaption>' + cap + "</figcaption></figure>", reach: c.band || 0, lane: "tiktok", id: c.id });
      });
    }
    if (state.sort === "reach") cards.sort(function (a, b) { return b.reach - a.reach; });
    else cards.sort(function (a, b) { return String(b.id || "").localeCompare(String(a.id || "")); });
    var totalCards = cards.length;
    cards = cards.slice(0, state.page * 120);
    wall.innerHTML = cards.map(function (c) { return c.html; }).join("");
    var moreBtn = document.getElementById("meg-more");
    if (moreBtn) moreBtn.hidden = !(totalCards > cards.length);
    countEl.textContent = cards.length + " of " + totalCards + " creatives" +
      (state.lane === "panel" && state.feed ? " · feed universe " + Number(state.feed.universe_impressions || 0).toLocaleString("en-US") + " observed impressions" : "");
    panelMeta();
    bindVideos();
  }
  function bindVideos() {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var v = en.target;
        if (en.isIntersecting && !panel.hidden) v.play().catch(function () {});
        else if (v.muted) v.pause();
      });
    }, { threshold: 0.25 });
    wall.querySelectorAll("video").forEach(function (v) {
      io.observe(v);
      v.addEventListener("click", function () {
        wall.querySelectorAll("video").forEach(function (o) { if (o !== v) o.muted = true; });
        v.muted = !v.muted; v.controls = !v.muted;
        if (v.paused) v.play().catch(function () {});
      });
    });
  }
  function fillBrands() {
    var names = {};
    PANEL_MEDIA.forEach(function (m) { names[m.brand] = 1; });
    if (state.tt) (state.tt || []).forEach(function (c) { if (c.brand) names[c.brand] = 1; });
    if (state.lib) (state.lib.records || []).forEach(function (r) { names[r.brand] = 1; });
    brandSel.innerHTML = '<option value="">All brands</option>' + Object.keys(names).sort().map(function (b) {
      return '<option value="' + esc(b) + '">' + esc(b) + "</option>";
    }).join("");
  }
  panel.querySelectorAll("[data-lane]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.lane = btn.getAttribute("data-lane"); state.page = 1;
      panel.querySelectorAll("[data-lane]").forEach(function (b) { b.setAttribute("aria-pressed", b === btn ? "true" : "false"); });
      render();
    });
  });
  brandSel.addEventListener("change", function () { state.brand = brandSel.value; state.page = 1; render(); });
  var searchEl = document.getElementById("meg-search");
  if (searchEl) searchEl.addEventListener("input", function () { state.query = searchEl.value.trim().toLowerCase(); state.page = 1; render(); });
  var moreEl = document.getElementById("meg-more");
  if (moreEl) moreEl.addEventListener("click", function () { state.page += 1; render(); });
  sortSel.addEventListener("change", function () { state.sort = sortSel.value; state.page = 1; render(); });

  Promise.all([
    fetch("data/tt_creatives.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
    fetch("data/meg_panel.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
    fetch("data/tt_market.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
    fetch("data/tt_ledgers.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
    fetch("data/meg_engagement.json", { cache: "no-store" }).then(function (r) { return r.json(); }).catch(function () { return {}; }),
    fetch("data/meg_library.json", { cache: "no-store" }).then(function (r) { return r.json(); }).catch(function () { return {}; }),
    fetch("data/meg_feed.json", { cache: "no-store" }).then(function (r) { return r.json(); }).catch(function () { return {}; }),
    fetch("data/meg_dsa_ads.json", { cache: "no-store" }).then(function (r) { return r.json(); }).catch(function () { return {}; })
  ]).then(function (res) {
    state.tt = res[0]; state.pn = res[1]; state.eng = res[4] || {}; state.lib = res[5] || {}; state.feed = res[6] || {}; state.dsa = res[7] || {};
    var mk = res[2] || {}, lg = res[3] || {}, t = mk.totals || {}, o = lg.outcomes || {};
    var note = document.getElementById("meg-corpus-note");
    if (note) note.textContent = "TikTok corpus · refreshed " + (mk.generated || "—") + " · " +
      (t.tiktok_playables || 0) + " playable creatives of " + (t.tiktok_ads || 0) + " collected ads · ledger: " +
      (o.kept_total || 0) + " kept, " + (o.routed_gated || 0) + " routed-gated, " + (o.unrouted || 0) + " unrouted of " + (lg.n_rows_scanned || 0) + " scanned. Counts are platform-reported as captured; spend is estimated only where a basis is named.";
    fillBrands(); render();
  }).catch(function () {});
})();
