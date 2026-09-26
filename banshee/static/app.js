/**
 * Banshee Web UI — Frontend Application Logic
 *
 * Handles: file upload (drag & drop), browser mic recording,
 * settings management, API calls, and result display.
 */

(function () {
    "use strict";

    // ──────────────────────────────────────────────
    // DOM Elements
    // ──────────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const statusBadge       = $("#statusBadge");
    const btnUploadMode     = $("#btnUploadMode");
    const btnRecordMode     = $("#btnRecordMode");
    const uploadZone        = $("#uploadZone");
    const recordZone        = $("#recordZone");
    const fileInput         = $("#fileInput");
    const fileInfo          = $("#fileInfo");
    const fileName          = $("#fileName");
    const fileSize          = $("#fileSize");
    const removeFileBtn     = $("#removeFile");
    const btnRecord         = $("#btnRecord");
    const recordTimer       = $("#recordTimer");
    const recordHint        = $("#recordHint");
    const waveformCanvas    = $("#waveformCanvas");
    const modelSelector     = $("#modelSelector");
    const formatSelector    = $("#formatSelector");
    const languageSelect    = $("#languageSelect");
    const beamSizeInput     = $("#beamSize");
    const beamSizeValue     = $("#beamSizeValue");
    const btnTranscribe     = $("#btnTranscribe");
    const transcribeBtnContent  = $("#transcribeBtnContent");
    const transcribeBtnLoading  = $("#transcribeBtnLoading");
    const progressBar       = $("#progressBar");
    const progressFill      = $("#progressFill");
    const progressText      = $("#progressText");
    const outputEmpty       = $("#outputEmpty");
    const resultsSection    = $("#resultsSection");
    const resultsText       = $("#resultsText");
    const btnCopy           = $("#btnCopy");
    const btnDownload       = $("#btnDownload");
    const metaLangText      = $("#metaLangText");
    const metaDurationText  = $("#metaDurationText");
    const metaSpeedText     = $("#metaSpeedText");
    const metaModelText     = $("#metaModelText");
    const segmentsTimeline  = $("#segmentsTimeline");
    const segmentsList      = $("#segmentsList");

    // ──────────────────────────────────────────────
    // State
    // ──────────────────────────────────────────────
    let state = {
        mode: "upload",         // "upload" | "record"
        file: null,             // File object from upload or recording
        model: "base",
        format: "txt",
        language: "",
        beamSize: 5,
        isRecording: false,
        isTranscribing: false,
        lastResult: null,       // Latest transcription result from API
    };

    // Recording state
    let mediaRecorder = null;
    let audioChunks = [];
    let recordingStartTime = 0;
    let timerInterval = null;
    let audioContext = null;
    let analyserNode = null;
    let animationFrameId = null;

    // ──────────────────────────────────────────────
    // Input Mode Toggle
    // ──────────────────────────────────────────────
    btnUploadMode.addEventListener("click", () => switchMode("upload"));
    btnRecordMode.addEventListener("click", () => switchMode("record"));

    function switchMode(mode) {
        state.mode = mode;
        if (mode === "upload") {
            btnUploadMode.classList.add("input-toggle__btn--active");
            btnRecordMode.classList.remove("input-toggle__btn--active");
            uploadZone.style.display = "";
            recordZone.style.display = "none";
        } else {
            btnRecordMode.classList.add("input-toggle__btn--active");
            btnUploadMode.classList.remove("input-toggle__btn--active");
            uploadZone.style.display = "none";
            recordZone.style.display = "";
        }
        updateTranscribeButton();
    }

    // ──────────────────────────────────────────────
    // File Upload (Click + Drag & Drop)
    // ──────────────────────────────────────────────
    uploadZone.addEventListener("click", () => {
        if (!state.file) fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Drag & Drop
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("drag-over");
    });

    uploadZone.addEventListener("dragleave", () => {
        uploadZone.classList.remove("drag-over");
    });

    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("drag-over");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    function handleFileSelect(file) {
        state.file = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatBytes(file.size);
        fileInfo.style.display = "";
        uploadZone.querySelector(".upload-zone__content").style.display = "none";
        updateTranscribeButton();
    }

    removeFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        clearFile();
    });

    function clearFile() {
        state.file = null;
        fileInput.value = "";
        fileInfo.style.display = "none";
        uploadZone.querySelector(".upload-zone__content").style.display = "";
        updateTranscribeButton();
    }

    // ──────────────────────────────────────────────
    // Microphone Recording (Web Audio API + MediaRecorder)
    // ──────────────────────────────────────────────
    btnRecord.addEventListener("click", toggleRecording);

    async function toggleRecording() {
        if (state.isRecording) {
            stopRecording();
        } else {
            await startRecording();
        }
    }

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });

            // Setup MediaRecorder
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: getSupportedMimeType(),
            });
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
                const ext = mediaRecorder.mimeType.includes("webm") ? "webm" : "ogg";
                state.file = new File([blob], `recording.${ext}`, { type: blob.type });
                stream.getTracks().forEach(t => t.stop());
                updateTranscribeButton();
            };

            mediaRecorder.start(100); // 100ms chunks

            // Setup audio analyser for waveform
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(stream);
            analyserNode = audioContext.createAnalyser();
            analyserNode.fftSize = 256;
            source.connect(analyserNode);

            state.isRecording = true;
            recordingStartTime = Date.now();

            // Update UI
            btnRecord.classList.add("recording");
            recordHint.textContent = "Recording… click to stop";
            timerInterval = setInterval(updateTimer, 100);
            drawWaveform();
            updateTranscribeButton();

        } catch (err) {
            console.error("Mic access denied:", err);
            recordHint.textContent = "⚠️ Microphone access denied. Check browser permissions.";
            recordHint.style.color = "var(--error)";
            setTimeout(() => {
                recordHint.textContent = "Click the button to start recording";
                recordHint.style.color = "";
            }, 4000);
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        }

        state.isRecording = false;
        clearInterval(timerInterval);
        cancelAnimationFrame(animationFrameId);

        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }

        btnRecord.classList.remove("recording");
        recordHint.textContent = "✅ Recording saved! Click Transcribe below.";
    }

    function getSupportedMimeType() {
        const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) return type;
        }
        return "audio/webm";
    }

    function updateTimer() {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const secs = String(elapsed % 60).padStart(2, "0");
        recordTimer.textContent = `${mins}:${secs}`;
    }

    // ──────────────────────────────────────────────
    // Waveform Visualizer
    // ──────────────────────────────────────────────
    function drawWaveform() {
        if (!analyserNode || !state.isRecording) return;

        const canvas = waveformCanvas;
        const ctx = canvas.getContext("2d");
        const width = canvas.width;
        const height = canvas.height;
        const bufferLength = analyserNode.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        function draw() {
            if (!state.isRecording) return;
            animationFrameId = requestAnimationFrame(draw);

            analyserNode.getByteFrequencyData(dataArray);

            ctx.clearRect(0, 0, width, height);

            const barWidth = (width / bufferLength) * 2;
            const centerY = height / 2;

            for (let i = 0; i < bufferLength; i++) {
                const value = dataArray[i] / 255;
                const barHeight = value * centerY * 0.9;

                const hue = 260 + (i / bufferLength) * 40;  // purple → blue
                const alpha = 0.4 + value * 0.6;

                ctx.fillStyle = `hsla(${hue}, 80%, 65%, ${alpha})`;

                const x = i * barWidth;
                // Mirror bars from center
                ctx.fillRect(x, centerY - barHeight, barWidth - 1, barHeight);
                ctx.fillRect(x, centerY, barWidth - 1, barHeight);
            }
        }

        draw();
    }

    // Draw idle waveform
    function drawIdleWaveform() {
        const canvas = waveformCanvas;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const centerY = canvas.height / 2;
        ctx.strokeStyle = "rgba(139, 92, 246, 0.15)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(canvas.width, centerY);
        ctx.stroke();
    }
    drawIdleWaveform();

    // ──────────────────────────────────────────────
    // Settings Controls
    // ──────────────────────────────────────────────

    // Model chips
    modelSelector.addEventListener("click", (e) => {
        const chip = e.target.closest(".model-chip");
        if (!chip) return;
        $$(".model-chip").forEach(c => c.classList.remove("model-chip--active"));
        chip.classList.add("model-chip--active");
        state.model = chip.dataset.model;
    });

    // Format chips
    formatSelector.addEventListener("click", (e) => {
        const chip = e.target.closest(".format-chip");
        if (!chip) return;
        $$(".format-chip").forEach(c => c.classList.remove("format-chip--active"));
        chip.classList.add("format-chip--active");
        state.format = chip.dataset.format;
    });

    // Language select
    languageSelect.addEventListener("change", () => {
        state.language = languageSelect.value;
    });

    // Beam size slider
    beamSizeInput.addEventListener("input", () => {
        state.beamSize = parseInt(beamSizeInput.value);
        beamSizeValue.textContent = state.beamSize;
    });

    // ──────────────────────────────────────────────
    // Transcribe Button
    // ──────────────────────────────────────────────
    function updateTranscribeButton() {
        btnTranscribe.disabled = !state.file || state.isTranscribing || state.isRecording;
    }

    btnTranscribe.addEventListener("click", doTranscribe);

    async function doTranscribe() {
        if (!state.file || state.isTranscribing) return;

        state.isTranscribing = true;
        updateTranscribeButton();

        // UI: show loading
        transcribeBtnContent.style.display = "none";
        transcribeBtnLoading.style.display = "";
        progressBar.style.display = "";
        outputEmpty.style.display = "";
        resultsSection.style.display = "none";
        setStatus("Processing…", "processing");

        // Simulate progress (since we can't get real progress from the API)
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 85) {
                progress += Math.random() * 8;
                if (progress > 85) progress = 85;
                progressFill.style.width = progress + "%";
                if (progress < 20) {
                    progressText.textContent = "Loading model…";
                } else if (progress < 60) {
                    progressText.textContent = "Transcribing audio…";
                } else {
                    progressText.textContent = "Generating output…";
                }
            }
        }, 400);

        try {
            const formData = new FormData();
            formData.append("file", state.file);
            formData.append("model", state.model);
            formData.append("language", state.language);
            formData.append("format", state.format);
            formData.append("beam_size", state.beamSize);

            const response = await fetch("/api/transcribe", {
                method: "POST",
                body: formData,
            });

            clearInterval(progressInterval);

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || "Transcription failed");
            }

            const result = await response.json();
            state.lastResult = result;

            // Complete progress
            progressFill.style.width = "100%";
            progressText.textContent = "Done!";

            setTimeout(() => {
                progressBar.style.display = "none";
                progressFill.style.width = "0%";
                showResults(result);
            }, 600);

            setStatus("Ready", "");

        } catch (err) {
            clearInterval(progressInterval);
            progressBar.style.display = "none";
            progressFill.style.width = "0%";
            setStatus("Error", "error");
            alert("❌ " + err.message);
            console.error(err);
        } finally {
            state.isTranscribing = false;
            transcribeBtnContent.style.display = "";
            transcribeBtnLoading.style.display = "none";
            updateTranscribeButton();
        }
    }

    // ──────────────────────────────────────────────
    // Display Results
    // ──────────────────────────────────────────────
    function showResults(result) {
        outputEmpty.style.display = "none";
        resultsSection.style.display = "";

        // Set metadata pills
        const langNames = {
            en: "English", es: "Spanish", fr: "French", de: "German",
            it: "Italian", pt: "Portuguese", nl: "Dutch", ru: "Russian",
            zh: "Chinese", ja: "Japanese", ko: "Korean", ar: "Arabic",
            hi: "Hindi", tr: "Turkish", pl: "Polish", sv: "Swedish",
        };
        const lang = result.metadata.language;
        metaLangText.textContent = langNames[lang] || lang.toUpperCase();
        metaDurationText.textContent = formatDuration(result.metadata.duration);
        metaSpeedText.textContent = result.metadata.speed_ratio + "× speed";
        metaModelText.textContent = result.metadata.model;

        // Set transcript text
        resultsText.textContent = result.formatted_output;

        // Show segments timeline for formats with timing
        if (result.segments && result.segments.length > 0) {
            segmentsTimeline.style.display = "";
            segmentsList.innerHTML = "";

            result.segments.forEach(seg => {
                const el = document.createElement("div");
                el.className = "segment-item";
                el.innerHTML = `
                    <span class="segment-time">${formatTimestamp(seg.start)}</span>
                    <span class="segment-text">${escapeHtml(seg.text)}</span>
                `;
                segmentsList.appendChild(el);
            });
        } else {
            segmentsTimeline.style.display = "none";
        }

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // ──────────────────────────────────────────────
    // Copy & Download
    // ──────────────────────────────────────────────
    btnCopy.addEventListener("click", () => {
        if (!state.lastResult) return;
        navigator.clipboard.writeText(state.lastResult.formatted_output).then(() => {
            btnCopy.classList.add("copied");
            btnCopy.querySelector("svg + span") || (btnCopy.innerHTML = btnCopy.innerHTML);
            const origText = btnCopy.textContent;
            btnCopy.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
            setTimeout(() => {
                btnCopy.classList.remove("copied");
                btnCopy.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
            }, 2000);
        });
    });

    btnDownload.addEventListener("click", () => {
        if (!state.lastResult) return;

        const fmt = state.lastResult.format;
        const ext = fmt === "json" ? "json" : fmt === "srt" ? "srt" : fmt === "vtt" ? "vtt" : "txt";
        const mimeType = fmt === "json" ? "application/json" : "text/plain";
        const filename = `transcript.${ext}`;

        const blob = new Blob([state.lastResult.formatted_output], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // ──────────────────────────────────────────────
    // Status Badge
    // ──────────────────────────────────────────────
    function setStatus(text, cls) {
        statusBadge.textContent = text;
        statusBadge.className = "badge badge--status";
        if (cls) statusBadge.classList.add(cls);
    }

    // ──────────────────────────────────────────────
    // Helpers
    // ──────────────────────────────────────────────
    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    function formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        if (mins > 0) return `${mins}m ${secs}s`;
        return `${secs}s`;
    }

    function formatTimestamp(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
        return `${m}:${String(s).padStart(2, "0")}`;
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

})();
