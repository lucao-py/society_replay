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

function formatDateTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("pt-BR");
}

let syncPollingInterval = null;

function renderSyncStatus(sync) {
  const card = document.getElementById("syncStatusCard");
  const message = document.getElementById("syncStatusMessage");
  const started = document.getElementById("syncStatusStarted");
  const finished = document.getElementById("syncStatusFinished");
  const downloaded = document.getElementById("syncDownloaded");
  const skipped = document.getElementById("syncSkipped");
  const ignored = document.getElementById("syncIgnored");
  const error = document.getElementById("syncStatusError");

  if (!card) return;

  card.hidden = false;
  card.dataset.status = sync.status;

  if (message) message.textContent = sync.message || "";
  if (started) started.textContent = sync.started_at ? `Início: ${formatDateTime(sync.started_at)}` : "";
  if (finished) finished.textContent = sync.finished_at ? `Fim: ${formatDateTime(sync.finished_at)}` : "";
  if (downloaded) downloaded.textContent = `Novos: ${sync.result?.downloaded ?? 0}`;
  if (skipped) skipped.textContent = `Existentes: ${sync.result?.skipped ?? 0}`;
  if (ignored) ignored.textContent = `Ignorados: ${sync.result?.ignored ?? 0}`;
  if (error) error.textContent = sync.error ? `Erro: ${sync.error}` : "";

  if (sync.status === "done" || sync.status === "error") {
    setTimeout(() => {
      const card = document.getElementById("syncStatusCard");
      if (card) {
        card.hidden = true;
      }
    }, 10000); // 10 segundos
  }
}

async function fetchSyncStatus() {
  const response = await fetch("/sync-status");
  const data = await response.json();

  if (!response.ok || !data.ok) {
    throw new Error("Não foi possível consultar o status da sincronização.");
  }

  renderSyncStatus(data.sync);

  if (data.sync.status === "processing") {
    startSyncPolling();
  } else {
    stopSyncPolling();
  }
}

function startSyncPolling() {
  if (syncPollingInterval) return;

  syncPollingInterval = setInterval(() => {
    fetchSyncStatus().catch(() => {
      stopSyncPolling();
    });
  }, 2000);
}

function stopSyncPolling() {
  if (syncPollingInterval) {
    clearInterval(syncPollingInterval);
    syncPollingInterval = null;
  }
}

function syncWithAdminKey() {
  const key = prompt("Digite o código:");

  if (key !== "lucas123") {
    alert("Acesso negado");
    return;
  }

    const card = document.getElementById("syncStatusCard");
  if (card) {
    card.hidden = false;
  }
  const btn = document.getElementById("syncBtn");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <i class="fa-solid fa-spinner fa-spin"></i>
    `;
  }

fetch("/sync-drive", {
  method: "POST"
})
  .then(async (response) => {
    const contentType = response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
      const rawText = await response.text();
      console.error("Resposta inesperada do /sync-drive:", rawText);
      throw new Error("O servidor não retornou JSON no /sync-drive.");
    }

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.message || "Erro ao iniciar sincronização.");
    }

    startSyncPolling();
    return fetchSyncStatus();
  })
    .catch((error) => {
      alert(error.message || "Erro ao iniciar");
    })
    .finally(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `
          <i class="fa-solid fa-arrows-rotate"></i>
        `;
      }
    });
}



document.addEventListener("DOMContentLoaded", () => {
  let player = document.getElementById("videoPlayer");
  const form = document.getElementById("clipForm");
  const playerCard = document.getElementById("playerCard");

  if (!form || !playerCard) return;

  const gameId = form.dataset.gameId;
  const previewReady = playerCard.dataset.previewReady === "true";

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

  const jobStatus = document.getElementById("jobStatus");
  const dynamicResultSection = document.getElementById("dynamicResultSection");

  let isSubmitting = false;
  let currentJobId = null;
  let pollingInterval = null;

  let currentPreviewJobId = null;
  let previewPollingInterval = null;

  function setEditorEnabled(enabled) {
    [markStartBtn, markEndBtn, clearSelectionBtn, generateClipBtn].forEach((btn) => {
      if (!btn) return;
      btn.disabled = !enabled;
    });
  }

  function getCurrent() {
    if (!player) return 0;
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

  function setStatus(message, type = "info") {
    if (!jobStatus) return;

    jobStatus.hidden = false;
    jobStatus.textContent = message;
    jobStatus.dataset.type = type;
  }

  function clearStatus() {
    if (!jobStatus) return;

    jobStatus.hidden = true;
    jobStatus.textContent = "";
    delete jobStatus.dataset.type;
  }

  function updateGenerateButton() {
    if (!generateClipBtn) return;

    const valid = hasValidRange();
    const disabled = !valid || isSubmitting || !player;

    generateClipBtn.disabled = disabled;
    generateClipBtn.classList.toggle("is-disabled", disabled);

    if (isSubmitting) {
      generateClipBtn.innerHTML = `
        <i class="fa-solid fa-spinner fa-spin"></i>
        <span>Processando...</span>
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
    if (!player) return;

    const current = getCurrent();
    startSecondsInput.value = current;
    syncCurrentTime();
    updateLabels();
  }

  function markEnd() {
    if (!player) return;

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
    if (player && !player.paused) {
      player.pause();
    }
  }

  function validateBeforeSubmit(showAlert = true) {
    if (!player) {
      if (showAlert) {
        alert("O vídeo ainda está sendo preparado.");
      }
      return false;
    }

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

  function renderLatestClip(downloadUrl) {
    if (!dynamicResultSection) return;

    dynamicResultSection.innerHTML = `
      <div class="clip-card">
        <div class="clip-card-header">
          <div>
            <h2>Clipe gerado com sucesso</h2>
            <p class="section-subtitle">Visualize ou baixe o arquivo.</p>
          </div>
        </div>

        <video class="video-player" controls preload="metadata" playsinline webkit-playsinline>
          <source src="${downloadUrl}" type="video/mp4">
          Seu navegador não suporta vídeo.
        </video>

        <a class="button full" href="${downloadUrl}">
          Baixar clipe
        </a>
      </div>
    `;
  }

  async function fetchLatestClip() {
    const response = await fetch(`/latest_clip/${gameId}`);
    if (!response.ok) {
      throw new Error("Não foi possível carregar o clipe gerado.");
    }

    const data = await response.json();
    return data.clip;
  }

  async function checkJobStatus() {
    if (!currentJobId) return;

    const response = await fetch(`/clip-status/${currentJobId}`);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.message || "Erro ao consultar status do job.");
    }

    if (data.status === "pending") {
      setStatus("Seu clipe entrou na fila. Aguarde...", "info");
      return;
    }

    if (data.status === "processing") {
      setStatus("Gerando clipe em segundo plano...", "info");
      return;
    }

    if (data.status === "error") {
      stopPolling();
      isSubmitting = false;
      updateGenerateButton();
      setStatus(data.error_message || "Erro ao gerar clipe.", "error");
      return;
    }

    if (data.status === "done") {
      stopPolling();
      isSubmitting = false;
      updateGenerateButton();
      setStatus("Clipe gerado com sucesso.", "success");

      const clip = await fetchLatestClip();
      renderLatestClip(clip.download_url);
    }
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  function startPolling(jobId) {
    currentJobId = jobId;
    stopPolling();

    pollingInterval = setInterval(() => {
      checkJobStatus().catch((error) => {
        stopPolling();
        isSubmitting = false;
        updateGenerateButton();
        setStatus(error.message || "Erro ao acompanhar processamento.", "error");
      });
    }, 2000);

    checkJobStatus().catch((error) => {
      stopPolling();
      isSubmitting = false;
      updateGenerateButton();
      setStatus(error.message || "Erro ao acompanhar processamento.", "error");
    });
  }

  function bindPlayerEvents() {
    if (!player) return;

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
  }

  function renderPreviewPlayer(previewUrl) {
    playerCard.innerHTML = `
      <video
        id="videoPlayer"
        class="video-player"
        controls
        preload="metadata"
        playsinline
        webkit-playsinline
      >
        <source src="${previewUrl}" type="video/mp4">
        Seu navegador não suporta vídeo.
      </video>
    `;

    player = document.getElementById("videoPlayer");
    bindPlayerEvents();
    setEditorEnabled(true);
    syncCurrentTime();
    updateLabels();
    setStatus("Vídeo pronto para edição.", "success");
  }

  function stopPreviewPolling() {
    if (previewPollingInterval) {
      clearInterval(previewPollingInterval);
      previewPollingInterval = null;
    }
  }

  async function checkPreviewStatus() {
    if (!currentPreviewJobId) return;

    const response = await fetch(`/preview-status/${currentPreviewJobId}`);
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.message || "Erro ao consultar status do preview.");
    }

    if (data.status === "pending") {
      setStatus("Seu vídeo entrou na fila de preparação...", "info");
      return;
    }

    if (data.status === "processing") {
      setStatus("Preparando vídeo para edição...", "info");
      return;
    }

    if (data.status === "error") {
      stopPreviewPolling();
      setStatus(data.error_message || "Erro ao gerar preview.", "error");
      return;
    }

    if (data.status === "done") {
      stopPreviewPolling();
      renderPreviewPlayer(data.preview_url);
    }
  }

  function startPreviewPolling(jobId) {
    currentPreviewJobId = jobId;
    stopPreviewPolling();

    previewPollingInterval = setInterval(() => {
      checkPreviewStatus().catch((error) => {
        stopPreviewPolling();
        setStatus(error.message || "Erro ao acompanhar preview.", "error");
      });
    }, 2000);

    checkPreviewStatus().catch((error) => {
      stopPreviewPolling();
      setStatus(error.message || "Erro ao acompanhar preview.", "error");
    });
  }

  async function ensurePreviewReady() {
    setEditorEnabled(false);

    if (previewReady) {
      bindPlayerEvents();
      setEditorEnabled(true);
      syncCurrentTime();
      updateLabels();
      clearStatus();
      return;
    }

    setStatus("Solicitando preparação do vídeo...", "info");

    try {
      const response = await fetch(`/generate_preview/${playerCard.dataset.gameId}`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error(data.message || "Erro ao iniciar geração do preview.");
      }

      if (data.already_ready) {
        renderPreviewPlayer(data.preview_url);
        return;
      }

      startPreviewPolling(data.job_id);
    } catch (error) {
      setStatus(error.message || "Erro ao preparar vídeo.", "error");
    }
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

      if (!player) return;

      if (player.paused) {
        player.play().catch(() => {});
      } else {
        player.pause();
      }
      return;
    }

    if (key === "g") {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    syncCurrentTime();

    if (!validateBeforeSubmit(true)) {
      return;
    }

    normalizeRangeBeforeSubmit();

    const payload = {
      current_seconds: currentSecondsInput.value,
      start_seconds: startSecondsInput.value,
      end_seconds: endSecondsInput.value,
    };

    isSubmitting = true;
    updateGenerateButton();
    setStatus("Enviando solicitação de geração...", "info");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error(data.message || "Erro ao iniciar geração do clipe.");
      }

      startPolling(data.job_id);
    } catch (error) {
      isSubmitting = false;
      updateGenerateButton();
      setStatus(error.message || "Erro ao iniciar geração do clipe.", "error");
    }
  });

  updateLabels();
  syncCurrentTime();
  ensurePreviewReady();
});