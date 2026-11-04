/* Extra tabs (study1 / trends / spend / creatives). app.js owns cycle/burden/market. */
(function () {
  "use strict";
  var mine = [["tab-study1", "panel-study1", "study1"], ["tab-trends", "panel-trends", "trends"],
              ["tab-evidence", "panel-evidence", "evidence"], ["tab-cpm", "panel-cpm", "cpm"]];
  var alias = { spend: "study1" };
  var theirs = [["tab-cycle", "panel-cycle"], ["tab-burden", "panel-burden"], ["tab-market", "panel-market"]];
  function el(id) { return document.getElementById(id); }
  function show(which) {
    mine.concat(theirs.map(function (t) { return [t[0], t[1], null]; })).forEach(function (p) {
      var t = el(p[0]), s = el(p[1]);
      var on = p[2] === which;
      if (t) t.setAttribute("aria-selected", on ? "true" : "false");
      if (s) s.hidden = !on;
    });
    if (location.hash !== "#" + which) history.replaceState(null, "", "#" + which);
  }
  function hideMine() {
    mine.forEach(function (p) {
      var t = el(p[0]), s = el(p[1]);
      if (t) t.setAttribute("aria-selected", "false");
      if (s) { s.hidden = true; s.querySelectorAll("video").forEach(function (v) { v.pause(); }); }
    });
  }
  mine.forEach(function (p) {
    var t = el(p[0]);
    if (t) t.addEventListener("click", function (e) { e.preventDefault(); show(p[2]); });
  });
  theirs.forEach(function (p) {
    var t = el(p[0]);
    if (t) t.addEventListener("click", hideMine);
  });
  window.addEventListener("hashchange", function () {
    var h = alias[location.hash.slice(1)] || location.hash.slice(1);
    var m = mine.filter(function (p) { return p[2] === h; })[0];
    if (m) show(h); else hideMine();
  });
  var h0 = alias[location.hash.slice(1)] || location.hash.slice(1);
  if (mine.some(function (p) { return p[2] === h0; })) show(h0);
  else if (!location.hash) show("study1");
  else hideMine();
})();
