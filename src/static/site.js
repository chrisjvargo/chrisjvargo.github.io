(function () {
  var input = document.getElementById("pub-filter");
  if (!input) {
    return;
  }

  var items = Array.prototype.slice.call(document.querySelectorAll(".pub-item"));
  input.addEventListener("input", function () {
    var q = (input.value || "").toLowerCase().trim();
    items.forEach(function (item) {
      var hay = item.getAttribute("data-pub-text") || item.textContent.toLowerCase();
      item.style.display = hay.indexOf(q) >= 0 ? "" : "none";
    });
  });
})();
