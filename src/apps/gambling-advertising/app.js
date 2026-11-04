/* After the Visit — tabs, timeline render, burden chart. No dependencies. */
(function () {
  "use strict";

  var VERIFIED_SVG = '<svg class="verified" viewBox="0 0 24 24" aria-label="Verified account"><circle cx="12" cy="12" r="10" fill="#1d9bf0"/><path d="M10.5 15.5l-3-3 1.4-1.4 1.6 1.6 4.6-4.6 1.4 1.4z" fill="#fff"/></svg>';

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fetchJSON(p) { return fetch(p, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(p); return r.json(); }); }
  function fetchCSV(p) {
    return fetch(p, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(p); return r.text(); }).then(function (t) {
      var lines = t.trim().split("\n"), head = lines[0].split(",");
      return lines.slice(1).map(function (ln) {
        // simple CSV: no embedded commas in our frozen files except quoted shares
        var cells = [], cur = "", q = false;
        for (var i = 0; i < ln.length; i++) {
          var c = ln[i];
          if (c === '"') { q = !q; continue; }
          if (c === "," && !q) { cells.push(cur); cur = ""; continue; }
          cur += c;
        }
        cells.push(cur);
        var o = {};
        head.forEach(function (h, j) { o[h.trim()] = (cells[j] || "").trim(); });
        return o;
      });
    });
  }

  /* ---------- tabs ---------- */
  var tabCycle = document.getElementById("tab-cycle");
  var tabBurden = document.getElementById("tab-burden");
  var tabMarket = document.getElementById("tab-market");
  var panelCycle = document.getElementById("panel-cycle");
  var panelBurden = document.getElementById("panel-burden");
  var panelMarket = document.getElementById("panel-market");
  function showTab(which) {
    var spec = [[panelCycle, tabCycle, "cycle"], [panelBurden, tabBurden, "burden"], [panelMarket, tabMarket, "market"]];
    spec.forEach(function (p) {
      var on = p[2] === which;
      if (p[0]) p[0].hidden = !on;
      if (p[1]) p[1].setAttribute("aria-selected", on ? "true" : "false");
    });
    if (("onhashchange" in window) && location.hash !== "#" + which) {
      history.replaceState(null, "", "#" + which);
    }
    window.scrollTo(0, 0);
  }
  tabCycle.addEventListener("click", function (e) { e.preventDefault(); showTab("cycle"); });
  tabBurden.addEventListener("click", function (e) { e.preventDefault(); showTab("burden"); });
  if (tabMarket) tabMarket.addEventListener("click", function (e) { e.preventDefault(); showTab("market"); });
  if (location.hash === "#burden") showTab("burden");
  if (location.hash === "#cycle") showTab("cycle");
  if (location.hash === "#market" && panelMarket) showTab("market");
  window.addEventListener("hashchange", function () {
    if (location.hash === "#cycle") showTab("cycle");
    else if (location.hash === "#burden") showTab("burden");
  });

  /* ---------- reveal + progress ---------- */
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var revealObs = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); revealObs.unobserve(e.target); } });
  }, { threshold: 0.08 });
  function reveal(el) { if (reduceMotion) { el.classList.add("in"); } else { el.classList.add("reveal"); revealObs.observe(el); } }

  var progressFill = document.getElementById("progress-fill");
  var beatsEl = document.getElementById("beats");
  function updateProgress() {
    if (panelCycle.hidden) return;
    var r = beatsEl.getBoundingClientRect();
    var total = r.height - window.innerHeight * 0.6;
    var done = Math.min(Math.max(-r.top + window.innerHeight * 0.3, 0), Math.max(total, 1));
    progressFill.style.width = (total > 0 ? (done / total) * 100 : 0).toFixed(1) + "%";
  }
  document.addEventListener("scroll", updateProgress, { passive: true });

  /* ---------- video autoplay (muted, pausable) ---------- */
  var videoObs = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      var v = e.target;
      if (e.isIntersecting && !reduceMotion) { v.play().catch(function () {}); }
      else { v.pause(); }
    });
  }, { threshold: 0.5 });

  function initial(name) { return (name || "?").trim().charAt(0).toUpperCase(); }

  /* Display cleaner for native trace text. Faithful except: "hashtag X" renders
     as "#X"; standalone "?" mojibake tokens (lost emoji in capture) are dropped;
     a trailing "Promoted." is dropped because the card meta row already shows it. */
  function cleanDisplay(t) {
    var s = String(t == null ? "" : t);
    s = s.replace(/hashtag\s+/gi, "#");
    s = s.replace(/(^|\s)\?(\s|$)/g, "$1$2");
    s = s.replace(/\bImage\.\s*\.\s*/g, "");
    s = s.replace(/\s+Promoted\.\s*$/, "");
    return s.replace(/\s{2,}/g, " ").trim();
  }

  function adCardHTML(b, i, total) {
    var media = "";
    if (b.media_file && /\.mp4$/.test(b.media_file)) {
      var poster = b.poster || (b.media_file === "dk_lebron.mp4" ? "dk_poster.jpg" : "");
      if (poster) {
        // Deliver the creative inline as muted video (autoplays on scroll via
        // videoObs), with the poster as the video's own poster frame. If the
        // video cannot load, renderCycle swaps in the poster <img> — the
        // creative is never a blank box.
        media = '<figure class="ad-media"><video muted loop playsinline preload="metadata" poster="creative/' + esc(poster) +
          '" data-poster="creative/' + esc(poster) + '" title="Ad creative from ' + esc(b.advertiser) + '">' +
          '<source src="creative/' + esc(b.media_file) + '" type="video/mp4"></video></figure>';
      } else {
        media = '<figure class="ad-media"><video muted loop playsinline preload="metadata" title="Ad creative from ' + esc(b.advertiser) + '">' +
          '<source src="creative/' + esc(b.media_file) + '" type="video/mp4"></video></figure>';
      }
    } else if (b.media_file) {
      media = '<figure class="ad-media"><img loading="lazy" src="creative/' + esc(b.media_file) +
        '" alt="Ad creative from ' + esc(b.advertiser) + ' (representative)"></figure>';
    }
    return '<div class="ad-card' + (b.media_file ? "" : " text-only") + '">' +
      '<div class="ad-head"><div class="ad-avatar" aria-hidden="true">' + esc(initial(b.advertiser)) + "</div>" +
      '<div class="ad-who"><div class="ad-name">' + esc(b.advertiser) + " " + VERIFIED_SVG + "</div>" +
      '<div class="ad-handle">' + esc(b.service) + " · Promoted</div></div></div>" +
      '<p class="ad-text">' + esc(cleanDisplay(b.native_text)) + "</p>" + media +
      '<div class="ad-meta"><span class="promoted">Promoted</span><span>Day ' + b.day + ", " + esc(b.clock) +
      " · +" + esc(b.elapsed_label) + "</span>" +
      '<span class="tier">' + esc(b.media_file ? b.creative_label : "text record only — no verified creative") + "</span></div></div>";
  }

  function visitCardHTML(v, isReturn) {
    var name = v.app || v.domain || "gambling site";
    var sub = (isReturn ? "Opened again · " : "") + v.kind + " · Day " + v.day + ", " + v.clock +
      (v.elapsed_min ? " · +" + Math.floor(v.elapsed_min / 60) + "h " + String(v.elapsed_min % 60).padStart(2, "0") + "m" : " · start of the window");
    return '<div class="visit-card' + (isReturn ? " return" : "") + '">' +
      '<p class="app-name">' + esc(name) + "</p>" +
      '<p class="app-sub">' + esc(sub) + "</p></div>";
  }

  function renderCycle(cyc, listEl, opts) {
    opts = opts || {};
    var html = "";
    html += '<li class="beat visit"><p class="beat-label"><span class="daytag">Day 1</span>The visit</p>' +
      visitCardHTML(cyc.anchor, false) + "</li>";
    var beats = cyc.beats, total = beats.length;
    for (var i = 0; i < beats.length; i++) {
      var b = beats[i];
      html += '<li class="beat ad"><p class="beat-label"><span class="daytag">Day ' + b.day + "</span>" +
        "Ad " + b.n + " of " + total + ' · <span class="elapsed">+' + esc(b.elapsed_label) + "</span></p>" +
        adCardHTML(b, i, total) + "</li>";
      var nx = beats[i + 1];
      if (nx && nx.advertiser === b.advertiser && Math.abs(nx.elapsed_min - b.elapsed_min) <= 2) {
        html += '<p class="pair-note">Same post, seen twice — two separate impressions.</p>';
      }
    }
    html += '<li class="beat visit"><p class="beat-label"><span class="daytag">Day ' + cyc["return"].day + "</span>" +
      'The return · <span class="elapsed">+' + Math.floor(cyc["return"].elapsed_min / 60) + "h " +
      String(cyc["return"].elapsed_min % 60).padStart(2, "0") + "m</span></p>" +
      visitCardHTML(cyc["return"], true) + "</li>";
    listEl.innerHTML = html;
    Array.prototype.forEach.call(listEl.querySelectorAll("li, .pair-note"), reveal);
    Array.prototype.forEach.call(listEl.querySelectorAll("video"), function (v) {
      videoObs.observe(v);
      v.addEventListener("click", function () { if (v.paused) v.play(); else v.pause(); });
      // Fail visible: a video that cannot load is replaced by its poster
      // image, so the creative still shows instead of a blank black box.
      var fail = function () {
        var p = v.getAttribute("data-poster");
        if (!p || v.dataset.fbk) return; v.dataset.fbk = "1";
        var im = document.createElement("img");
        im.src = p; im.alt = v.title || "Ad creative";
        v.replaceWith(im);
      };
      v.addEventListener("error", fail, true);
      var so = v.querySelector("source");
      if (so) so.addEventListener("error", fail);
    });
    Array.prototype.forEach.call(listEl.querySelectorAll("img[data-video]"), function (img) {
      img.addEventListener("click", function () {
        var v = document.createElement("video");
        v.muted = true; v.loop = true; v.playsInline = true; v.autoplay = true; v.controls = true;
        v.src = img.getAttribute("data-video");
        img.replaceWith(v);
        v.play().catch(function () {});
      });
    });
    updateProgress();
  }

  /* ---------- journeys: picker + full stage ---------- */
  var JOURNEYS = [];
  var POSTERS = { "dk_lebron.mp4": "dk_poster.jpg" };
  var numWord = { 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve" };

  function fact(v, k) { return '<div class="person-fact"><span class="v">' + esc(v) + '</span><span class="k">' + esc(k) + "</span></div>"; }
  function cap(s) { return String(s).charAt(0).toUpperCase() + String(s).slice(1); }
  function pro(pron, g) {
    if (g === "woman") return pron === "s" ? "she" : "her";
    if (g === "man") return pron === "s" ? "he" : "his";
    return pron === "s" ? "they" : "their";
  }

  function deckFor(h) {
    var anchorName = h.anchor.app || h.anchor.domain;
    var returnName = h["return"].app || h["return"].domain;
    var byAdv = {};
    h.beats.forEach(function (b) { byAdv[b.advertiser] = (byAdv[b.advertiser] || 0) + 1; });
    var top = Object.keys(byAdv).sort(function (x, y) { return byAdv[y] - byAdv[x]; })[0];
    var shortTop = top.split("|")[0].split(" - ")[0].trim();
    var topBeats = h.beats.filter(function (b) { return b.advertiser === top; });
    var files = {};
    topBeats.forEach(function (b) { if (b.media_file) files[b.media_file] = true; });
    var fileKeys = Object.keys(files);
    var clause;
    if (topBeats.length === h.beats.length && fileKeys.length === 1) {
      var kind = /\.mp4$/.test(fileKeys[0]) ? "video" : "ad";
      clause = " — the same " + shortTop + " " + kind + " " + (numWord[topBeats.length] || topBeats.length) + " times.";
    } else if (byAdv[top] >= 2 && byAdv[top] >= h.beats.length - 1) {
      clause = " — " + (numWord[byAdv[top]] || byAdv[top]) + " of them from " + shortTop + ".";
    } else {
      clause = ".";
    }
    var again = anchorName === returnName ? " again." : ".";
    var gapMin = h["return"].elapsed_min;
    var gapStr = gapMin < 60 ? gapMin + " minutes" : h.pressure.gap_hours + " hours";
    return "A " + h.person.age + "-year-old " + h.person.gender + " in " + h.person.state +
      " opened " + anchorName + ". Over the next " + gapStr +
      ", " + pro("o", h.person.gender) + " " + h.pressure.services.join("-and-") +
      " feed served " + h.pressure.n_ads + " gambling ads" + clause + " Then " +
      pro("s", h.person.gender) + " opened " + returnName + again;
  }

  function thumbFor(h) {
    for (var i = 0; i < h.beats.length; i++) {
      var mf = h.beats[i].media_file;
      if (mf) {
        var img = /\.mp4$/.test(mf) ? (POSTERS[mf] || "") : mf;
        if (img) return '<span class="journey-thumb"><img loading="lazy" src="creative/' + esc(img) + '" alt=""></span>';
      }
    }
    return '<span class="journey-thumb textile" aria-hidden="true">Aa</span>';
  }

  function creativeBadge(h) {
    var kinds = {};
    h.beats.forEach(function (b) {
      if (!b.media_file) return;
      kinds[/\.mp4$/.test(b.media_file) ? "video" : "photos"] = true;
    });
    var k = Object.keys(kinds);
    return k.length ? k.join(" + ") : "text records";
  }

  function renderPicker() {
    var el = document.getElementById("journey-picker");
    el.innerHTML = JOURNEYS.map(function (h, i) {
      var a = h.anchor.app || h.anchor.domain, r = h["return"].app || h["return"].domain;
      return '<button class="journey-card" data-i="' + i + '" aria-current="' + (i === 0 ? "true" : "false") + '">' +
        thumbFor(h) +
        '<span class="journey-body"><span class="journey-title">' + esc(h.title) + "</span>" +
        '<span class="journey-sub" style="display:block">' + h.person.age + ", " + h.person.gender + ", " + esc(h.person.state) +
        " · " + esc(a) + " → " + esc(r) + "</span>" +
        '<span class="journey-meta"><span class="badge">' + h.pressure.n_ads + " ads</span>" +
        "<span>" + h.pressure.gap_hours + "h</span>" +
        "<span>" + esc(creativeBadge(h)) + "</span>" +
        "<span>class of " + h.support.class_users + "</span></span></span></button>";
    }).join("");
    Array.prototype.forEach.call(el.querySelectorAll(".journey-card"), function (btn) {
      btn.addEventListener("click", function () { selectJourney(+btn.getAttribute("data-i"), true); });
    });
  }

  function selectJourney(i, scroll) {
    var h = JOURNEYS[i];
    if (!h) return;
    document.getElementById("journey-title").textContent = h.title + ".";
    document.getElementById("hero-deck").textContent = deckFor(h);
    document.getElementById("person-facts").innerHTML =
      fact(h.person.age, "Age") + fact(cap(h.person.gender), "Gender") + fact(h.person.state, "State");
    document.getElementById("person-profile").textContent = (h.profile || []).join(" ");
    renderCycle(h, beatsEl);
    document.getElementById("loop-summary").innerHTML =
      '<p class="loop-line">1 visit → ' + h.pressure.n_ads + " ads → 1 return</p>" +
      '<p class="loop-sub">' + h.pressure.ads_per_day + " gambling ads per day across " +
      h.pressure.gap_hours + " hours · " + h.pressure.n_advertisers + " advertisers · " +
      h.pressure.services.join(", ") + "</p>";
    document.getElementById("support-note").textContent =
      "One case from a pattern seen across " + h.support.class_users + " panelists.";
    document.getElementById("methods-cycle").innerHTML = methodsCycle(h);
    Array.prototype.forEach.call(document.querySelectorAll(".journey-card"), function (btn) {
      btn.setAttribute("aria-current", +btn.getAttribute("data-i") === i ? "true" : "false");
    });
    if (scroll) document.getElementById("journey-title").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  }

  /* ---------- load cycle tab ---------- */
  fetchJSON("data/journeys.json").then(function (js) {
    JOURNEYS = js;
    renderPicker();
    selectJourney(0, false);
  }).catch(function () {
    document.getElementById("journey-title").textContent = "Could not load the journey data.";
  });

  fetchJSON("data/dk_panel.json").then(function (d) {
    var adv = Object.keys(d.ads_seen.by_advertiser).slice(0, 4).map(function (k) {
      return "<li>" + esc(k) + " — " + d.ads_seen.by_advertiser[k] + "</li>";
    }).join("");
    document.getElementById("dk-panel").innerHTML =
      stat(d.ads_seen.n, "DraftKings ads seen across the panel") +
      stat(d.ads_seen.users, "panelists who saw at least one") +
      stat(d.loops.n + " / " + d.loops.users, "DK-anchored loops / users (below display rule)") +
      '<div class="stat wide"><div class="l" style="margin:0 0 2px">Top DraftKings advertisers seen</div><ul>' + adv + "</ul></div>";
  });

  function stat(n, l) { return '<div class="stat"><div class="n">' + esc(n) + '</div><div class="l">' + esc(l) + "</div></div>"; }

  function methodsCycle(h) {
    return "<p><strong>Source.</strong> YouGov Pulse panel with RealityMine passive traces, Oct 4 – Nov 5, 2024. " +
      "Gambling ads were labeled by a fine-tuned classifier with full manual review of positives; gambling visits from 333 reviewed domains plus reviewed apps. " +
      "Loop definition: a gambling visit, followed only by gambling-ad exposures, followed by the next gambling visit within 72 hours. " +
      "Profiles are three-sentence summaries of each person's survey response (household, work, gambling frequency, symptom bands) — no names, handles, or identifiers.</p>" +
      "<p><strong>Display rule.</strong> A journey is shown only if its pattern class (anchor family × pressure bin × window) covers at least 5 panelists " +
      "and every beat carries exact- or advertiser-level creative evidence. This journey's class (" + esc(h.support["class"]) +
      ") covers " + h.support.class_users + " panelists. Times are rounded to the minute and dates relativized (Day 1, Day 2, …). " +
      "Heavy panelists can appear in more than one journey; each loop is a distinct window. " +
      "Same-minute pairs are distinct impressions with differing like and view counts in the trace.</p>" +
      "<p><strong>Creative honesty.</strong> Videos and images marked “representative” passed visual inspection as genuine ads from the named advertiser " +
      "but are matched at the advertiser level. Beats with no verified creative appear as text records transcribed from the trace. " +
      "Facebook gambling ads (3,011 exposures) had no verifiable creative and are excluded from journey display by rule — see the paper for their statistical role.</p>" +
      "<p><strong>Limits.</strong> Observational traces: ads preceded the return; the record cannot say they caused it. Same-minute pairs are distinct " +
      "captured impressions. One loop is an existence proof of pressure, not a population estimate — that is what the Burden tab is for.</p>" +
      "<p><strong>Text cleaning.</strong> Ad copy is transcribed from the trace record with four display-only changes: “hashtag X” renders as “#X”, " +
      "standalone “?” tokens left by lost emoji in capture are dropped, “Image.” capture artifacts are dropped, and a duplicated trailing “Promoted.” is removed. Nothing else is altered.</p>";
  }

  /* ---------- burden tab ---------- */
  var burdenLoaded = false;
  function loadBurden() {
    if (burdenLoaded) return;
    burdenLoaded = true;
    Promise.all([fetchCSV("data/burden_curve.csv"), fetchCSV("data/burden_shares.csv"), fetchCSV("data/burden_tail.csv")])
      .then(function (parts) {
        renderBurden(parts[0], parts[1], parts[2]);
      }).catch(function () {
        document.getElementById("burden-deck").textContent = "Could not load the burden data.";
      });
  }
  tabBurden.addEventListener("click", loadBurden);
  if (location.hash === "#burden") loadBurden();

  function renderBurden(curve, shares, tail) {
    var s1 = shares.filter(function (r) { return r.group === "top 1%"; })[0];
    var s10 = shares.filter(function (r) { return r.group === "top 10%"; })[0];
    document.getElementById("burden-deck").textContent =
      "Rank 419 panelists by how many gambling ads reached them. The top 1% — four people — absorbed " +
      s1.gambling_share + "% of all gambling-ad exposures. The top 10% absorbed " + s10.gambling_share +
      "%. For ordinary ads, the same groups carried " + s1.all_share + "% and " + s10.all_share + "%. Gambling advertising is not spread thin. It is piled on.";
    renderChart(curve, shares);
    renderTail(tail);
    document.getElementById("methods-burden").innerHTML = methodsBurden();
  }

  function renderChart(curve, shares) {
    var W = 880, H = 470, ML = 56, MR = 150, MT = 18, MB = 52;
    var iw = W - ML - MR, ih = H - MT - MB;
    function X(p) { return ML + (p / 100) * iw; }
    function Y(s) { return MT + ih - (s / 100) * ih; }
    var g = curve.filter(function (r) { return r.group === "gambling ads"; });
    var a = curve.filter(function (r) { return r.group === "all ads"; });
    function path(rows) {
      return "M" + X(0) + "," + Y(0) + rows.map(function (r) {
        return "L" + X(+r.percentile).toFixed(1) + "," + Y(+r.cum_share).toFixed(1);
      }).join("");
    }
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="presentation">';
    [0, 25, 50, 75, 100].forEach(function (t) {
      s += '<line class="grid" x1="' + ML + '" y1="' + Y(t) + '" x2="' + (W - MR) + '" y2="' + Y(t) + '"/>' +
        '<text class="axis" x="' + (ML - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + t + "%</text>";
    });
    [0, 25, 50, 75, 100].forEach(function (t) {
      s += '<text class="axis" x="' + X(t) + '" y="' + (H - MB + 20) + '" text-anchor="middle">' + (t === 0 ? "most-exposed →" : t + "%") + "</text>";
    });
    s += '<text class="axis-label" x="' + ML + '" y="' + (H - 6) + '">Panelists, ranked most- to least-exposed</text>';
    s += '<text class="axis-label" x="' + (ML + 44) + '" y="12">Cumulative share of exposures →</text>';
    // equality reference
    s += '<line x1="' + ML + '" y1="' + Y(0) + '" x2="' + (W - MR) + '" y2="' + Y(100) +
      '" stroke="#d8d4cc" stroke-width="1" stroke-dasharray="2 4"/>';
    s += '<text class="callout sub" x="' + (W - MR - 4) + '" y="' + (Y(88)) + '" text-anchor="end">equal share</text>';
    s += '<path class="line-all" d="' + path(a) + '"/>';
    s += '<path class="line-gambling" d="' + path(g) + '"/>';
    // end labels (direct, no legend)
    var gl = g[g.length - 1], al = a[a.length - 1];
    s += '<text class="direct-label" x="' + (X(100) + 10) + '" y="' + (Y(100) + 24) + '" fill="#1f5c3f">Gambling ads</text>';
    s += '<text class="direct-label" x="' + (X(100) + 10) + '" y="' + (Y(100) + 42) + '" fill="#6f6a63" font-weight="400">All ads</text>';
    // annotated dots (staggered to avoid collisions; 1-decimal to match shares)
    var marks = [
      { p: 1, dx: 10, dy: -16, anchor: "start" },
      { p: 5, dx: 10, dy: 34, anchor: "start" },
      { p: 10, dx: 12, dy: -18, anchor: "start" },
      { p: 25, dx: 14, dy: -14, anchor: "start" }
    ];
    var glook = {}, alook = {};
    g.forEach(function (r) { glook[+r.percentile] = +r.cum_share; });
    a.forEach(function (r) { alook[+r.percentile] = +r.cum_share; });
    marks.forEach(function (m) {
      var gv = glook[m.p], av = alook[m.p];
      s += '<circle class="dot-g" cx="' + X(m.p) + '" cy="' + Y(gv) + '" r="5"/>';
      s += '<circle class="dot-a" cx="' + X(m.p) + '" cy="' + Y(av) + '" r="4"/>';
      var tx = X(m.p) + m.dx;
      s += '<text class="callout" x="' + tx + '" y="' + (Y(gv) + m.dy) + '" text-anchor="' + m.anchor + '" fill="#1f5c3f">top ' + m.p + "%: " + gv.toFixed(1) + "%</text>";
      s += '<text class="callout sub" x="' + tx + '" y="' + (Y(gv) + m.dy + 14) + '" text-anchor="' + m.anchor + '">all ads: ' + av.toFixed(1) + "%</text>";
    });
    s += "</svg>";
    document.getElementById("burden-chart").innerHTML = s;
  }

  function renderTail(tail) {
    var heavy = tail.filter(function (r) { return r.group.indexOf("heaviest") === 0; })[0];
    var rest = tail.filter(function (r) { return r.group.indexOf("heaviest") !== 0; })[0];
    function card(r, cls, title) {
      return '<div class="tail-card ' + cls + '"><h4>' + esc(title) + "</h4><dl>" +
        row("Avg. gambling ads seen", r.mean_exposure, "median " + r.median_exposure) +
        row("Identify as gamblers", r.gambler_share + "%", "") +
        row("Problem-gambling score", r.pgam_mean_gamblers, "self-report mean, 1–7") +
        row("Women", r.female_share + "%", "") +
        row("Mean age", r.mean_age, "") +
        "</dl></div>";
    }
    function row(dt, dd, small) {
      return "<dt>" + esc(dt) + "</dt><dd>" + esc(dd) + (small ? " <small>" + esc(small) + "</small>" : "") + "</dd>";
    }
    document.getElementById("tail-cards").innerHTML =
      card(heavy, "heavy", "Heaviest 10% · " + heavy.n + " people") +
      card(rest, "", "Remaining 90% · " + rest.n + " people");
  }

  function methodsBurden() {
    return "<p><strong>Source.</strong> Same panel and window as the cycle tab: 419 exposure-eligible mobile users, " +
      "Oct 4 – Nov 5, 2024. Gambling-ad counts use the manually reviewed labels (6,002 matched exposures); " +
      "all-ad counts use every captured sponsored impression on Facebook, TikTok, and X in the same window.</p>" +
      "<p><strong>Reading the chart.</strong> Panelists are ranked most- to least-exposed; the lines cumulate each group's " +
      "share of exposures. The top-1% point covers 4 panelists, top 5% covers 21, top 10% covers 42, top 25% covers 105. " +
      "Ranked groups need not contain the same people across the two lines.</p>" +
      "<p><strong>Limits.</strong> A nonprobability panel, not a population frame; one month, three platforms, mobile only. " +
      "Concentration is descriptive — it does not identify a cause, and group profiles (age, gender, scores) are " +
      "associations, not explanations. See the paper for models and uncertainty.</p>";
  }

  /* live market (tab 3) v5: the slice filters, meta-visualized slice chips,
     slide-in aggregate sheets, brand record sheets, ledger and creative viewer
     all live in market-v5.js (loaded after this file by index.html). The tab
     switching above already owns #tab-market / #panel-market; nothing here changed. */
})();
