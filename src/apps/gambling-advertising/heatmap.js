/* State help-seeking heatmap with horizontal time scroller (2004 -> today).
   Data: data/meg_heatmap.json (official 2014+ spliced with anchored pytrends
   extension pre-2014) + data/us_paths.json (Albers-projected state paths). */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var DATA = null, PATHS = null, timer = null;
  var MODE = "cumulative"; // cumulative: running sum per state (only darkens)
  var CUM = null, CUMREF = 200, SMOOTH = null;
  // Monthly display series: 12-month rolling mean. Raw monthly values include
  // one-month normalization spikes (a lone measurable month reads 100), which
  // flash a state dark for a single frame; the rolling mean removes the blink
  // without inventing data (mean over months Google actually measured).
  function buildSmooth() {
    SMOOTH = {};
    Object.keys(DATA.states).forEach(function (geo) {
      var src = DATA.states[geo], out = [];
      for (var i = 0; i < src.length; i++) {
        var sum = 0, n = 0;
        for (var k = Math.max(0, i - 11); k <= i; k++) {
          if (src[k] != null) { sum += src[k]; n++; }
        }
        out.push(n ? Math.round(sum / n * 10) / 10 : null);
      }
      SMOOTH[geo] = out;
    });
  }
  function buildCumulative() {
    CUM = {};
    var finals = [];
    Object.keys(DATA.states).forEach(function (geo) {
      var run = 0, seen = false, arr = [];
      DATA.states[geo].forEach(function (v) {
        if (v != null) { run += v; seen = true; }
        arr.push(seen ? Math.round(run * 10) / 10 : null);
      });
      CUM[geo] = arr;
      if (seen) finals.push(run);
    });
    finals.sort(function (a, b) { return a - b; });
    if (finals.length) CUMREF = finals[Math.floor(finals.length * 0.92)] || 200;
  }
  function seriesFor(geo) { return MODE === "cumulative" ? CUM[geo] : SMOOTH[geo]; }
  // The index sums 10 anchor-normalized terms in one window, so it is NOT
  // bounded at 100: 2026 runs ~10x the 2015 level (max ~600). A linear 0-100
  // ramp would hide everything before 2022 and saturate 2026. Sqrt scale
  // against a fixed reference (200) keeps both ends readable.
  var VREF = 200;
  function color(v) {
    if (v == null) return "#e3e0da";
    var ref = MODE === "cumulative" ? CUMREF : VREF;
    var t = Math.sqrt(Math.max(0, Math.min(v, ref)) / ref);
    var r = Math.round(247 - t * 60), g = Math.round(243 - t * 175), b = Math.round(238 - t * 175);
    return "rgb(" + r + "," + g + "," + b + ")";
  }
  function legend() {
    var stops = MODE === "cumulative"
      ? [0, 0.1, 0.3, 0.55, 0.8, 1].map(function (f) { return Math.round(CUMREF * f); })
      : [0, 10, 25, 50, 100, 200];
    return '<div class="heat-legend"><span>' + (MODE === "cumulative" ? "Cumulative help-seeking (accumulated index)" : "Help-seeking index") + '</span>' +
      stops.map(function (v) {
        return '<span class="heat-chip"><span class="heat-swatch" style="background:' + color(v) + '"></span>' + v + (v === 200 ? "+" : "") + "</span>";
      }).join("") + '<span class="heat-chip"><span class="heat-swatch" style="background:#e3e0da"></span>no measurable volume</span></div>';
  }
  function render(idx) {
    if (!DATA || !PATHS) return;
    var mo = DATA.months[idx];
    $("heat-month").textContent = mo + (mo < DATA.estimated_before ? " · pre-2014 estimate" : "");
    Object.keys(PATHS.paths).forEach(function (abbr) {
      var el = document.getElementById("hs-" + abbr);
      if (!el) return;
      var s = seriesFor("US-" + abbr);
      var v = s ? s[idx] : null;
      el.setAttribute("fill", color(v));
      el.querySelector("title").textContent = abbr + " · " + mo + " · " + (v == null ? "no measurable volume" : (MODE === "cumulative" ? "cumulative " : "index (12-mo avg) ") + v);
    });
    $("heat-time").value = idx;
  }
  function build() {
    var b = PATHS.bounds;
    var vb = b[0] + " " + (-b[3]) + " " + (b[2] - b[0]) + " " + (b[3] - b[1]);
    var svg = '<svg viewBox="' + vb + '" width="100%" role="img" aria-label="US map of gambling help-seeking searches">';
    Object.keys(PATHS.paths).forEach(function (abbr) {
      svg += '<path id="hs-' + abbr + '" d="' + PATHS.paths[abbr] + '" stroke="#fff" stroke-width="0.0016" fill="#e3e0da" data-abbr="' + abbr + '"><title>' + abbr + "</title></path>";
    });
    svg += "</svg>";
    $("heatmap").innerHTML = svg + legend();
    Array.prototype.forEach.call(document.querySelectorAll("#heatmap path"), function (p) {
      p.addEventListener("click", function () {
        var abbr = p.getAttribute("data-abbr");
        var sel = $("dm-geo");
        if (sel) {
          for (var i = 0; i < sel.options.length; i++) {
            if (sel.options[i].value === abbr || sel.options[i].text === abbr) { sel.selectedIndex = i; break; }
          }
          sel.dispatchEvent(new Event("change"));
        }
        var s = seriesFor("US-" + abbr);
        var idx = Number($("heat-time").value);
        $("heat-state").textContent = abbr + " in " + DATA.months[idx] + ": " + (s && s[idx] != null ? (MODE === "cumulative" ? "cumulative " : "index (12-mo avg) ") + s[idx] : "no measurable volume") + " — drilled below.";
      });
    });
    $("heat-note").textContent = DATA.note;
    var tog = $("heat-mode");
    if (tog) tog.addEventListener("click", function () {
      MODE = MODE === "cumulative" ? "monthly" : "cumulative";
      tog.textContent = MODE === "cumulative" ? "Showing: cumulative (click for monthly)" : "Showing: monthly (click for cumulative)";
      var lg = document.querySelector(".heat-legend");
      if (lg) lg.outerHTML = legend();
      render(Number($("heat-time").value));
    });
    render(DATA.months.length - 1);
  }
  Promise.all([
    fetch("data/meg_heatmap.json").then(function (r) { return r.json(); }),
    fetch("data/us_paths.json").then(function (r) { return r.json(); })
  ]).then(function (all) {
    DATA = all[0]; PATHS = all[1];
    buildCumulative(); buildSmooth();
    var slider = $("heat-time");
    slider.max = DATA.months.length - 1; slider.value = DATA.months.length - 1;
    slider.addEventListener("input", function () { render(Number(slider.value)); });
    $("heat-play").addEventListener("click", function () {
      var btn = $("heat-play");
      if (timer) { clearInterval(timer); timer = null; btn.textContent = "▶ Play"; return; }
      btn.textContent = "⏸ Pause";
      var idx = Number(slider.value);
      if (idx >= DATA.months.length - 1) idx = 0;
      timer = setInterval(function () {
        idx++;
        if (idx >= DATA.months.length) { clearInterval(timer); timer = null; btn.textContent = "▶ Play"; return; }
        render(idx);
      }, 90);
    });
    build();
  }).catch(function () {});
})();
