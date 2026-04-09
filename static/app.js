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
  if (!Number.isFinite(n)) return null;

  return Math.max(0, Math.floor(n));
}

document.addEventListener("DOMContentLoaded", () => {
  const player = document.getElementById("videoPlayer");
  const form = document.getElementById("clipForm");

  if (!player || !form) return;

  const currentSecondsInput = document.getElementById("current_seconds");
  const startSecondsInput = document.getElementById("start_seconds");
  const endSecondsInput = document.getElementById("end_seconds");

  const startTimeLabel = document.getElementById("startTimeLabel");
  const endTimeLabel = document.getElementById("endTimeLabel");

  const markStartBtn = document.getElementById("markStartBtn");
  const markEndBtn = document.getElementById("markEndBtn");
  const clearSelectionBtn = document.getElementById("clearSelectionBtn");
  const generateClipBtn = document.getElementById("generateClipBtn");

  const latestClipCard = document.getElementById("latestClipCard");
  const toggleLatestClipBtn = document.getElementById("toggleLatestClipBtn");
  const closeLatestClipBtn = document.getElementById("closeLatestClipBtn");

  let isSubmitting = false;

  function getCurrent() {
    return Math.max(0, Math.floor(player.currentTime || 0));
  }

  function getStart() {
    return parseValue(startSecondsInput.value);
  }

  function getEnd() {
    return parseValue(endSecondsInput.value);
  }

  function hasValidRange() {
    const start = getStart();
    const end = getEnd();

    return start !== null && end !== null && start !== end;
  }

  function getOrderedRange() {
    const start = getStart();
    const end = getEnd();

    if (start === null || end === null) return null;

    return {
      start: Math.min(start, end),
      end: Math.max(start, end),
    };
  }

  function setButtonState(button, isActive) {
    if (!button) return;

    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  }

  function updateGenerateButton() {
    if (!generateClipBtn) return;

    const valid = hasValidRange();

    generateClipBtn.disabled = !valid || isSubmitting;
    generateClipBtn.classList.toggle("is-disabled", !valid || isSubmitting);

    if (isSubmitting) {
      generateClipBtn.innerHTML = `
        <i class="fa-solid fa-spinner fa-spin"></i>
        <span>Gerando...</span>
      `;
      return;
    }

    generateClipBtn.innerHTML = `
      <i class="fa-solid fa-scissors"></i>
      <span>Gerar clipe</span>
    `;
  }

  function updateLabels() {
    const start = getStart();
    const end = getEnd();

    if (startTimeLabel) {
      startTimeLabel.textContent = start === null ? "não definido" : formatSeconds(start);
    }

    if (endTimeLabel) {
      endTimeLabel.textContent = end === null ? "não definido" : formatSeconds(end);
    }

    setButtonState(markStartBtn, start !== null);
    setButtonState(markEndBtn, end !== null);
    updateGenerateButton();
  }

  function syncCurrentTime() {
    currentSecondsInput.value = getCurrent();
  }

  function markStart() {
    const current = getCurrent();
    startSecondsInput.value = current;
    syncCurrentTime();
    updateLabels();
  }

  function markEnd() {
    const current = getCurrent();
    endSecondsInput.value = current;
    syncCurrentTime();
    updateLabels();
  }

  function clearSelection() {
    startSecondsInput.value = "";
    endSecondsInput.value = "";
    syncCurrentTime();
    updateLabels();
  }

  function seekBy(seconds) {
    if (!player || !Number.isFinite(player.duration)) return;

    const nextTime = Math.min(
      Math.max((player.currentTime || 0) + seconds, 0),
      player.duration
    );

    player.currentTime = nextTime;
    syncCurrentTime();
  }

  function pauseBeforeMark() {
    if (!player.paused) {
      player.pause();
    }
  }

  function validateBeforeSubmit(showAlert = true) {
    const start = getStart();
    const end = getEnd();

    if (start === null || end === null) {
      if (showAlert) {
        alert("Marque o início e o fim antes de gerar o clipe.");
      }
      return false;
    }

    if (start === end) {
      if (showAlert) {
        alert("O início e o fim não podem ser iguais.");
      }
      return false;
    }

    return true;
  }

  function normalizeRangeBeforeSubmit() {
    const range = getOrderedRange();
    if (!range) return;

    startSecondsInput.value = range.start;
    endSecondsInput.value = range.end;
  }

  function toggleLatestClip(show) {
    if (!toggleLatestClipBtn || !latestClipCard) return;

    const shouldShow = typeof show === "boolean"
      ? show
      : latestClipCard.classList.contains("clip-card-hidden");

    latestClipCard.classList.toggle("clip-card-hidden", !shouldShow);

    toggleLatestClipBtn.innerHTML = shouldShow
      ? `
        <i class="fa-solid fa-eye-slash"></i>
        <span>Ocultar último clipe</span>
      `
      : `
        <i class="fa-solid fa-film"></i>
        <span>Ver último clipe</span>
      `;
  }

  if (toggleLatestClipBtn && latestClipCard) {
    toggleLatestClipBtn.addEventListener("click", () => {
      toggleLatestClip();
    });
  }

  if (closeLatestClipBtn) {
    closeLatestClipBtn.addEventListener("click", () => {
      toggleLatestClip(false);
    });
  }

  markStartBtn?.addEventListener("click", () => {
    pauseBeforeMark();
    markStart();
  });

  markEndBtn?.addEventListener("click", () => {
    pauseBeforeMark();
    markEnd();
  });

  clearSelectionBtn?.addEventListener("click", clearSelection);

  player.addEventListener("loadedmetadata", () => {
    syncCurrentTime();
    updateLabels();
  });

  player.addEventListener("timeupdate", syncCurrentTime);

  player.addEventListener("play", () => {
    syncCurrentTime();
  });

  player.addEventListener("pause", () => {
    syncCurrentTime();
  });

  document.addEventListener("keydown", (event) => {
    const tag = document.activeElement?.tagName?.toLowerCase();
    if (tag === "input" || tag === "textarea") return;

    const key = event.key.toLowerCase();

    if (key === "s") {
      event.preventDefault();
      pauseBeforeMark();
      markStart();
      return;
    }

    if (key === "e") {
      event.preventDefault();
      pauseBeforeMark();
      markEnd();
      return;
    }

    if (key === "arrowleft") {
      event.preventDefault();
      seekBy(-1);
      return;
    }

    if (key === "arrowright") {
      event.preventDefault();
      seekBy(1);
      return;
    }

    if (key === ",") {
      event.preventDefault();
      seekBy(-5);
      return;
    }

    if (key === ".") {
      event.preventDefault();
      seekBy(5);
      return;
    }

    if (key === " ") {
      event.preventDefault();

      if (player.paused) {
        player.play().catch(() => {});
      } else {
        player.pause();
      }
      return;
    }

    if (key === "g") {
      event.preventDefault();

      if (!validateBeforeSubmit(true)) return;

      normalizeRangeBeforeSubmit();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", (event) => {
    syncCurrentTime();

    if (!validateBeforeSubmit(true)) {
      event.preventDefault();
      return;
    }

    normalizeRangeBeforeSubmit();
    isSubmitting = true;
    updateGenerateButton();
  });

  updateLabels();
  syncCurrentTime();
});