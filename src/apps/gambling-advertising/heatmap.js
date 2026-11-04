/* State help-seeking heatmap with horizontal time scroller (2004 -> today).
   Data: data/meg_heatmap.json (official 2014+ spliced with anchored pytrends
   extension pre-2014) + data/us_paths.json (Albers-projected state paths). */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var DATA = null, PATHS = null, timer = null;
  function color(v) {
    if (v == null) return "#e3e0da";
    var t = Math.max(0, Math.min(1, v / 100));
    // paper white -> deep red ramp
    var r = Math.round(247 - t * 60), g = Math.round(243 - t * 175), b = Math.round(238 - t * 175);
    return "rgb(" + r + "," + g + "," + b + ")";
  }
  function render(idx) {
    if (!DATA || !PATHS) return;
    var mo = DATA.months[idx];
    $("heat-month").textContent = mo + (mo < DATA.estimated_before ? " · pre-2014 estimate" : "");
    Object.keys(PATHS.paths).forEach(function (abbr) {
      var el = document.getElementById("hs-" + abbr);
      if (!el) return;
      var s = DATA.states["US-" + abbr];
      var v = s ? s[idx] : null;
      el.setAttribute("fill", color(v));
      el.querySelector("title").textContent = abbr + " · " + mo + " · " + (v == null ? "no measurable volume" : "index " + v);
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
    $("heatmap").innerHTML = svg;
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
        var s = DATA.states["US-" + abbr];
        var idx = Number($("heat-time").value);
        $("heat-state").textContent = abbr + " in " + DATA.months[idx] + ": " + (s && s[idx] != null ? "index " + s[idx] : "no measurable volume") + " — drilled below.";
      });
    });
    $("heat-note").textContent = DATA.note;
    render(DATA.months.length - 1);
  }
  Promise.all([
    fetch("data/meg_heatmap.json").then(function (r) { return r.json(); }),
    fetch("data/us_paths.json").then(function (r) { return r.json(); })
  ]).then(function (all) {
    DATA = all[0]; PATHS = all[1];
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
