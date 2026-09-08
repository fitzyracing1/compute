// Mirrors the window logic in compute/core.py, so the page can show
// which part of the cycle is live right now (all times UTC).
(function () {
  const MATRIX_CLOSE = 4 * 86400 + 8 * 3600;       // Friday 17:00
  const SERVICES_MORNING_CLOSE = 8 * 3600;          // Monday 17:00
  const SERVICES_FRIDAY_OPEN = 4 * 86400;           // Friday 09:00

  function weekOffsetSeconds(date) {
    const day = date.getUTCDay(); // 0 = Sunday .. 6 = Saturday
    const daysSinceMonday = (day + 6) % 7;
    const monday = new Date(Date.UTC(
      date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() - daysSinceMonday, 9, 0, 0
    ));
    let diff = (date.getTime() - monday.getTime()) / 1000;
    if (diff < 0) diff += 7 * 86400;
    return diff;
  }

  function stateAt(offset) {
    if (offset >= MATRIX_CLOSE) return "down";
    const servicesActive =
      offset < SERVICES_MORNING_CLOSE ||
      (offset >= SERVICES_FRIDAY_OPEN && offset < MATRIX_CLOSE);
    return servicesActive ? "matrix-open" : "quiet";
  }

  function label(state) {
    if (state === "matrix-open") return "services active";
    if (state === "quiet") return "matrix up, services quiet";
    return "fully down";
  }

  function init() {
    const strip = document.getElementById("week-strip");
    const week = document.querySelector(".week");
    if (!strip || !week) return;

    const state = stateAt(weekOffsetSeconds(new Date()));

    const marker = document.createElement("p");
    marker.className = "now-marker";
    marker.innerHTML =
      '<span class="dot dot-' + state.replace("matrix-open", "open") + '"></span>' +
      "right now (UTC): " + label(state);

    week.insertBefore(marker, strip);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
