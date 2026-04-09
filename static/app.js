function formatSeconds(totalSeconds) {
  totalSeconds = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(totalSeconds / 3600);
  const mm = Math.floor((totalSeconds % 3600) / 60);
  const ss = totalSeconds % 60;

  if (hh > 0) {
    return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  }

  return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

function parseValue(value) {
  if (value === "" || value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : null;
}

document.addEventListener("DOMContentLoaded", () => {
  const player = document.getElementById("videoPlayer");
  const form = document.getElementById("clipForm");

  const currentSecondsInput = document.getElementById("current_seconds");
  const startSecondsInput = document.getElementById("start_seconds");
  const endSecondsInput = document.getElementById("end_seconds");

  const currentTimeLabel = document.getElementById("currentTimeLabel");
  const startTimeLabel = document.getElementById("startTimeLabel");
  const endTimeLabel = document.getElementById("endTimeLabel");
  const durationLabel = document.getElementById("durationLabel");

  const markStartBtn = document.getElementById("markStartBtn");
  const markEndBtn = document.getElementById("markEndBtn");
  const clearSelectionBtn = document.getElementById("clearSelectionBtn");

  const latestClipCard = document.getElementById("latestClipCard");
  const toggleLatestClipBtn = document.getElementById("toggleLatestClipBtn");
  const closeLatestClipBtn = document.getElementById("closeLatestClipBtn");

  if (toggleLatestClipBtn && latestClipCard) {
    toggleLatestClipBtn.addEventListener("click", () => {
      const isHidden = latestClipCard.classList.contains("clip-card-hidden");

      if (isHidden) {
        latestClipCard.classList.remove("clip-card-hidden");
        toggleLatestClipBtn.innerHTML = `
          <i class="fa-solid fa-eye-slash"></i>
          <span>Ocultar último clipe</span>
        `;
      } else {
        latestClipCard.classList.add("clip-card-hidden");
        toggleLatestClipBtn.innerHTML = `
          <i class="fa-solid fa-film"></i>
          <span>Ver último clipe</span>
        `;
      }
    });
  }

  if (closeLatestClipBtn && latestClipCard && toggleLatestClipBtn) {
    closeLatestClipBtn.addEventListener("click", () => {
      latestClipCard.classList.add("clip-card-hidden");
      toggleLatestClipBtn.innerHTML = `
        <i class="fa-solid fa-film"></i>
        <span>Ver último clipe</span>
      `;
    });
  }

  if (!player || !form) return;

  function getCurrent() {
    return Math.max(0, Math.floor(player.currentTime || 0));
  }

  function refreshCurrentTime() {
    const current = getCurrent();
    if (currentTimeLabel) {
      currentTimeLabel.textContent = formatSeconds(current);
    }
    currentSecondsInput.value = current;
  }

  function refreshMarkers() {
    const start = parseValue(startSecondsInput.value);
    const end = parseValue(endSecondsInput.value);

    if (startTimeLabel) {
      startTimeLabel.textContent = start === null ? "não definido" : formatSeconds(start);
    }

    if (endTimeLabel) {
      endTimeLabel.textContent = end === null ? "não definido" : formatSeconds(end);
    }

    if (durationLabel) {
      if (start !== null && end !== null) {
        const realStart = Math.min(start, end);
        const realEnd = Math.max(start, end);
        durationLabel.textContent = `${realEnd - realStart}s`;
      } else {
        durationLabel.textContent = "0s";
      }
    }
  }

  function markStart() {
    const current = getCurrent();
    currentSecondsInput.value = current;
    startSecondsInput.value = current;
    refreshCurrentTime();
    refreshMarkers();
  }

  function markEnd() {
    const current = getCurrent();
    currentSecondsInput.value = current;
    endSecondsInput.value = current;
    refreshCurrentTime();
    refreshMarkers();
  }

  function clearSelection() {
    startSecondsInput.value = "";
    endSecondsInput.value = "";
    refreshMarkers();
  }

  markStartBtn.addEventListener("click", markStart);
  markEndBtn.addEventListener("click", markEnd);
  clearSelectionBtn.addEventListener("click", clearSelection);

  player.addEventListener("timeupdate", refreshCurrentTime);
  player.addEventListener("loadedmetadata", refreshCurrentTime);

  document.addEventListener("keydown", (event) => {
    const tag = document.activeElement?.tagName?.toLowerCase();
    if (tag === "input" || tag === "textarea") return;

    if (event.key.toLowerCase() === "s") {
      event.preventDefault();
      markStart();
    }

    if (event.key.toLowerCase() === "e") {
      event.preventDefault();
      markEnd();
    }

    if (event.key.toLowerCase() === "g") {
      event.preventDefault();
      form.submit();
    }
  });

  form.addEventListener("submit", (event) => {
    const start = parseValue(startSecondsInput.value);
    const end = parseValue(endSecondsInput.value);

    currentSecondsInput.value = getCurrent();

    if (start === null || end === null) {
      event.preventDefault();
      alert("Marque o início e o fim antes de gerar o clip.");
      return;
    }

    if (start === end) {
      event.preventDefault();
      alert("O início e o fim não podem ser iguais.");
      return;
    }
  });

  refreshCurrentTime();
  refreshMarkers();
});