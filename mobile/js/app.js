/**
 * REN-AI Mobile Web Client Application 2.0
 * Multi-user session isolation, SSE token streaming, Sensory body integration,
 * Skill cards, Web search status, Dream/Sleep mode, and edge TTS speech.
 */

// Register PWA Service Worker for standalone mobile mode
if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
}

document.addEventListener("DOMContentLoaded", () => {
    // --- Application State ---
    let currentSessionId = null;
    let isGenerating = false;
    let activeAbortController = null;
    let autoSpeak = localStorage.getItem("ren_auto_speak") === "true";
    let recognition = null;
    let isListening = false;
    let isSleeping = false;
    let activeAudioElement = document.getElementById("tts-audio");

    // REN 2.0 Multimodal & Thinking State
    let attachedImageBase64 = null;
    let attachedImageName = "";
    let isThinkHardActive = false;
    let developerToken = localStorage.getItem("ren_dev_token") || null;

    // --- User Session Identity Isolation ---
    function getUserId() {
        let uid = localStorage.getItem("ren_user_id");
        if (!uid) {
            uid = "usr_" + Math.random().toString(16).substring(2, 10) + Date.now().toString(16);
            localStorage.setItem("ren_user_id", uid);
        }
        return uid;
    }

    const userId = getUserId();

    // --- Authentication & Token Handling ---
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get("token") || urlParams.get("key");
    if (tokenFromUrl) {
        localStorage.setItem("ren_access_key", tokenFromUrl);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    function getAuthToken() {
        return localStorage.getItem("ren_access_key") || "";
    }

    function setAuthToken(token) {
        if (token) {
            localStorage.setItem("ren_access_key", token);
        } else {
            localStorage.removeItem("ren_access_key");
        }
    }

    async function apiFetch(url, options = {}) {
        options.headers = options.headers || {};
        const token = getAuthToken();
        if (token && !options.headers["Authorization"]) {
            options.headers["Authorization"] = `Bearer ${token}`;
        }
        if (developerToken) {
            options.headers["X-Developer-Token"] = developerToken;
        }
        options.headers["X-User-Session-ID"] = userId;

        const res = await fetch(url, options);
        if (res.status === 401) {
            showAuthModal();
        }
        return res;
    }

    // --- DOM Elements ---
    const sidebar = document.getElementById("sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    const btnOpenSidebar = document.getElementById("btn-open-sidebar");
    const btnCloseSidebar = document.getElementById("btn-close-sidebar");
    const btnNewChat = document.getElementById("btn-new-chat");
    const btnHeaderNewChat = document.getElementById("btn-header-new-chat");
    const conversationsList = document.getElementById("conversations-list");
    
    const chatContainer = document.getElementById("chat-container");
    const welcomeView = document.getElementById("welcome-view");
    const messagesList = document.getElementById("messages-list");
    const stageIndicator = document.getElementById("stage-indicator");
    const stageText = document.getElementById("stage-text");
    
    const userInput = document.getElementById("user-input");
    const btnSend = document.getElementById("btn-send");
    const btnStop = document.getElementById("btn-stop");
    const btnMic = document.getElementById("btn-mic");
    const btnCamera = document.getElementById("btn-camera");

    // REN 2.0 Controls
    const mobileThinkingMode = document.getElementById("mobile-thinking-mode");
    const mobileBtnThinkHard = document.getElementById("mobile-btn-think-hard");
    const mobileImageFile = document.getElementById("mobile-image-file");
    const mobileImagePreview = document.getElementById("mobile-image-preview");
    const mobilePreviewName = document.getElementById("mobile-preview-name");
    const mobileBtnClearImage = document.getElementById("mobile-btn-clear-image");

    const btnOpenDev = document.getElementById("btn-open-dev");
    const devModal = document.getElementById("dev-modal");
    const btnCloseDev = document.getElementById("btn-close-dev");
    const devBackdrop = document.getElementById("dev-backdrop");
    const btnSubmitDevAuth = document.getElementById("btn-submit-dev-auth");
    const devSecretInput = document.getElementById("dev-secret-input");
    const devAuthSection = document.getElementById("dev-auth-section");
    const devActiveSection = document.getElementById("dev-active-section");
    const btnRevokeDev = document.getElementById("btn-revoke-dev");
    
    const listeningBanner = document.getElementById("listening-banner");
    const transcriptPreview = document.getElementById("transcript-preview");
    const btnCancelVoice = document.getElementById("btn-cancel-voice");
    
    const statusBadge = document.getElementById("status-badge");
    const statusLabel = document.getElementById("status-label");
    const systemModelVal = document.getElementById("system-model-val");
    const systemCpuRamVal = document.getElementById("system-cpu-ram-val");
    
    const btnToggleVoice = document.getElementById("btn-toggle-voice");
    const voiceToggleLabel = document.getElementById("voice-toggle-label");
    const btnToggleDream = document.getElementById("btn-toggle-dream");
    const btnOpenAwakening = document.getElementById("btn-open-awakening");
    
    const btnOpenSkills = document.getElementById("btn-open-skills");
    const skillsModal = document.getElementById("skills-modal");
    const btnCloseSkills = document.getElementById("btn-close-skills");
    const skillsBackdrop = document.getElementById("skills-backdrop");
    const skillsListContainer = document.getElementById("skills-list-container");

    const authModal = document.getElementById("auth-modal");
    const authPasskeyInput = document.getElementById("auth-passkey-input");
    const btnUnlockAuth = document.getElementById("btn-unlock-auth");
    const authErrorMsg = document.getElementById("auth-error-msg");
    const authStatusContainer = document.getElementById("auth-status-container");
    const btnLockAuth = document.getElementById("btn-lock-auth");

    // Multi-Device DOM Elements
    const btnOpenDevices = document.getElementById("btn-open-devices");
    const deviceBadge = document.getElementById("device-badge");
    const deviceCountLabel = document.getElementById("device-count-label");
    const devicesModal = document.getElementById("devices-modal");
    const btnCloseDevices = document.getElementById("btn-close-devices");
    const devicesBackdrop = document.getElementById("devices-backdrop");
    const tabBtnPairQr = document.getElementById("tab-btn-pair-qr");
    const tabBtnPairedList = document.getElementById("tab-btn-paired-list");
    const deviceViewQr = document.getElementById("device-view-qr");
    const deviceViewList = document.getElementById("device-view-list");
    const qrLoading = document.getElementById("qr-loading");
    const qrContainer = document.getElementById("qr-container");
    const pairingQrImg = document.getElementById("pairing-qr-img");
    const pairingCodeLabel = document.getElementById("pairing-code-label");
    const pairingCountdown = document.getElementById("pairing-countdown");
    const btnRefreshQr = document.getElementById("btn-refresh-qr");
    const manualChallengeInput = document.getElementById("manual-challenge-input");
    const manualDevName = document.getElementById("manual-dev-name");
    const btnSubmitPairing = document.getElementById("btn-submit-pairing");
    const pairedDevicesContainer = document.getElementById("paired-devices-container");

    // --- Sensory Context Bridge ---
    const appContext = {
        showToast,
        sendSensorReaction: (text) => {
            if (!isGenerating) {
                const { body } = createAssistantMessageCard();
                body.setAttribute("data-raw-text", text);
                body.innerHTML = renderMarkdown(text);
                if (autoSpeak) playSpeech(text);
            }
        }
    };
    const sensors = new MobileSensors(appContext);

    // --- Status Badge Helper ---
    function setStatus(type, label) {
        statusBadge.className = `status-badge status-${type}`;
        statusLabel.textContent = label;
    }

    // --- Authentication UI Controls ---
    function showAuthModal() {
        authModal.classList.remove("hidden");
        authPasskeyInput.value = "";
        authErrorMsg.classList.add("hidden");
        setTimeout(() => authPasskeyInput.focus(), 150);
    }

    function hideAuthModal() {
        authModal.classList.add("hidden");
    }

    async function unlockAssistant() {
        const key = authPasskeyInput.value.trim();
        if (!key) return;

        btnUnlockAuth.disabled = true;
        btnUnlockAuth.textContent = "Verifying...";
        authErrorMsg.classList.add("hidden");

        try {
            const res = await fetch("/api/auth/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ key: key })
            });

            if (res.ok) {
                setAuthToken(key);
                hideAuthModal();
                authStatusContainer.classList.remove("hidden");
                showToast("Assistant unlocked", "success");
                boot();
            } else {
                const data = await res.json().catch(() => ({}));
                authErrorMsg.textContent = data.detail || "Invalid passkey. Please try again.";
                authErrorMsg.classList.remove("hidden");
            }
        } catch (err) {
            authErrorMsg.textContent = "Connection error. Please check server status.";
            authErrorMsg.classList.remove("hidden");
        } finally {
            btnUnlockAuth.disabled = false;
            btnUnlockAuth.textContent = "Unlock Assistant";
        }
    }

    btnUnlockAuth.addEventListener("click", unlockAssistant);
    authPasskeyInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") unlockAssistant();
    });

    btnLockAuth.addEventListener("click", () => {
        setAuthToken("");
        showAuthModal();
        closeSidebar();
    });

    // --- Voice Toggle UI ---
    function updateVoiceToggleUI() {
        if (autoSpeak) {
            voiceToggleLabel.textContent = "Voice On";
            btnToggleVoice.classList.add("btn-primary");
            btnToggleVoice.classList.remove("btn-secondary");
        } else {
            voiceToggleLabel.textContent = "Voice Off";
            btnToggleVoice.classList.remove("btn-primary");
            btnToggleVoice.classList.add("btn-secondary");
        }
    }
    updateVoiceToggleUI();

    btnToggleVoice.addEventListener("click", () => {
        autoSpeak = !autoSpeak;
        localStorage.setItem("ren_auto_speak", autoSpeak ? "true" : "false");
        updateVoiceToggleUI();
        showToast(autoSpeak ? "Voice auto-playback enabled" : "Voice auto-playback disabled", "info");
    });

    // --- Sleep & Dream Mode Controls ---
    async function toggleSleepMode() {
        try {
            if (isSleeping) {
                const res = await apiFetch("/api/dream/wake", { method: "POST" });
                if (res.ok) {
                    isSleeping = false;
                    btnToggleDream.innerHTML = "<span>🌙 Sleep Mode (Dream)</span>";
                    setStatus("online", "Online");
                    showToast("REN is awake and listening", "info");
                }
            } else {
                const res = await apiFetch("/api/dream/sleep", { method: "POST" });
                if (res.ok) {
                    isSleeping = true;
                    btnToggleDream.innerHTML = "<span>☀️ Wake Up</span>";
                    setStatus("sleeping", "Sleeping");
                    showToast("REN entered Dream Mode", "info");
                }
            }
        } catch (e) {
            showToast("Failed to toggle sleep state", "error");
        }
        closeSidebar();
    }

    btnToggleDream.addEventListener("click", toggleSleepMode);
    btnOpenAwakening.addEventListener("click", () => {
        closeSidebar();
        sensors.showAwakeningModal();
    });

    // --- Toast Notifications ---
    function showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 250);
        }, 3500);
    }

    // --- Sidebar Drawer Controls ---
    function openSidebar() {
        sidebar.classList.add("active");
        sidebarBackdrop.classList.add("active");
    }

    function closeSidebar() {
        sidebar.classList.remove("active");
        sidebarBackdrop.classList.remove("active");
    }

    btnOpenSidebar.addEventListener("click", openSidebar);
    btnCloseSidebar.addEventListener("click", closeSidebar);
    sidebarBackdrop.addEventListener("click", closeSidebar);

    // --- Input Auto-Resize ---
    userInput.addEventListener("input", () => {
        userInput.style.height = "auto";
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
        btnSend.disabled = userInput.value.trim().length === 0;
    });

    // --- Handle Enter Key ---
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!btnSend.disabled && !isGenerating) {
                sendMessage();
            }
        }
    });

    // --- Visual Viewport Adjustment (Mobile Keyboard) ---
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", () => {
            setTimeout(() => scrollToBottom(true), 100);
        });
    }

    function scrollToBottom(force = false) {
        if (force || chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 200) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    // --- Quick Prompt Chips ---
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const prompt = chip.getAttribute("data-prompt");
            if (prompt) {
                userInput.value = prompt;
                userInput.dispatchEvent(new Event("input"));
                sendMessage();
            }
        });
    });

    // --- Safe Markdown Parser ---
    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function renderMarkdown(rawText) {
        if (!rawText) return "";

        const codeBlocks = [];
        let text = rawText.replace(/```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const id = `__CODE_BLOCK_${codeBlocks.length}__`;
            codeBlocks.push({ lang: lang || "code", code: code.trim() });
            return id;
        });

        text = escapeHtml(text);

        // Headers
        text = text.replace(/^### (.*$)/gim, "<h3>$1</h3>");
        text = text.replace(/^## (.*$)/gim, "<h2>$1</h2>");
        text = text.replace(/^# (.*$)/gim, "<h1>$1</h1>");

        // Bold & Italic
        text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");

        // Inline code
        text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

        // Render Image Asset Cards: ![alt](url)
        text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
            return `<div class="ren-image-card"><img src="${src}" alt="${alt}" class="ren-rendered-image" loading="lazy" onclick="window.open('${src}', '_blank')">${alt ? `<div class="ren-image-caption">${alt}</div>` : ""}</div>`;
        });

        // Also handle asset comments: &lt;!-- ren:image_asset:(.*?) --&gt;
        text = text.replace(/&lt;!--\s*ren:image_asset:([a-zA-Z0-9_-]+)\s*--&gt;/g, (match, assetId) => {
            const src = `/api/assets/images/${assetId}`;
            return `<div class="ren-image-card"><img src="${src}" alt="REN Generated Asset" class="ren-rendered-image" loading="lazy" onclick="window.open('${src}', '_blank')"><div class="ren-image-caption">Asset ID: ${assetId}</div></div>`;
        });

        // Markdown Links: [text](url)
        text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:underline;">$1</a>');

        // Unordered lists
        text = text.replace(/^\s*[-*]\s+(.*)$/gim, "<li>$1</li>");
        text = text.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

        // Line breaks & Paragraphs
        const paragraphs = text.split(/\n\n+/);
        text = paragraphs.map(p => {
            if (p.startsWith("<h") || p.startsWith("<ul") || p.startsWith("<ol") || p.startsWith("__CODE_BLOCK_")) {
                return p;
            }
            return `<p>${p.replace(/\n/g, "<br>")}</p>`;
        }).join("");

        // Re-inject Code Blocks
        codeBlocks.forEach((block, idx) => {
            const id = `__CODE_BLOCK_${idx}__`;
            const codeHtml = `<div class="code-block-wrapper">
                <div class="code-block-header">
                    <span>${escapeHtml(block.lang)}</span>
                    <button class="code-copy-btn" onclick="navigator.clipboard.writeText(decodeURIComponent('${encodeURIComponent(block.code)}')).then(() => alert('Code copied!'))">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                        Copy
                    </button>
                </div>
                <pre><code>${escapeHtml(block.code)}</code></pre>
            </div>`;
            text = text.replace(id, codeHtml);
        });

        return text;
    }

    // --- Message Elements Builder ---
    function appendUserMessage(text) {
        welcomeView.classList.add("hidden");
        const row = document.createElement("div");
        row.className = "message-row user-row";
        
        const bubble = document.createElement("div");
        bubble.className = "user-bubble";
        bubble.textContent = text;
        
        row.appendChild(bubble);
        messagesList.appendChild(row);
        scrollToBottom(true);
    }

    function createAssistantMessageCard() {
        welcomeView.classList.add("hidden");
        const row = document.createElement("div");
        row.className = "message-row assistant-row";

        const card = document.createElement("div");
        card.className = "assistant-card";

        const header = document.createElement("div");
        header.className = "assistant-header";

        const titleArea = document.createElement("div");
        titleArea.className = "assistant-title-area";
        titleArea.innerHTML = `<span style="font-size:1.1rem;">🪐</span> <span class="assistant-name">REN</span>`;

        const actions = document.createElement("div");
        actions.className = "message-actions";

        const btnSpeak = document.createElement("button");
        btnSpeak.className = "msg-action-btn";
        btnSpeak.title = "Read aloud";
        btnSpeak.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg> Read`;
        
        actions.appendChild(btnSpeak);
        header.appendChild(titleArea);
        header.appendChild(actions);

        const badgeContainer = document.createElement("div");
        badgeContainer.className = "badge-container";

        const body = document.createElement("div");
        body.className = "markdown-body";

        card.appendChild(header);
        card.appendChild(badgeContainer);
        card.appendChild(body);
        row.appendChild(card);
        messagesList.appendChild(row);

        btnSpeak.addEventListener("click", () => {
            const raw = body.getAttribute("data-raw-text") || body.textContent;
            playSpeech(raw, btnSpeak);
        });

        scrollToBottom(true);
        return { row, card, badgeContainer, body, btnSpeak };
    }

    // --- Audio TTS Playback (Isolated & Non-blocking) ---
    async function playSpeech(text, triggerBtn = null) {
        if (!text || text.trim().length === 0) return;

        if (triggerBtn) {
            triggerBtn.innerHTML = `<span class="stage-spinner" style="width:10px;height:10px;"></span> Playing`;
        }

        setStatus("speaking", "Speaking");

        try {
            const res = await apiFetch("/api/tts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });

            if (res.ok) {
                const blob = await res.blob();
                const audioUrl = URL.createObjectURL(blob);
                activeAudioElement.src = audioUrl;
                activeAudioElement.play();

                activeAudioElement.onended = () => {
                    if (triggerBtn) {
                        triggerBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg> Read`;
                    }
                    if (!isGenerating) setStatus("online", "Online");
                };
                return;
            }
        } catch (e) {
            console.warn("Server TTS playback error, falling back to browser speech:", e);
        }

        // Fallback to browser SpeechSynthesis
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text.replace(/```.*?```/gs, ""));
            utterance.rate = 1.05;
            utterance.onend = () => {
                if (triggerBtn) {
                    triggerBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg> Read`;
                }
                if (!isGenerating) setStatus("online", "Online");
            };
            window.speechSynthesis.speak(utterance);
        } else if (triggerBtn) {
            triggerBtn.innerHTML = `Read`;
            if (!isGenerating) setStatus("online", "Online");
        }
    }

    // --- Chat SSE Streaming Send Logic ---
    async function sendMessage() {
        const text = userInput.value.trim();
        const img = attachedImageBase64;
        const thinkingMode = mobileThinkingMode ? mobileThinkingMode.value : "MEDIUM";
        const thinkHard = isThinkHardActive;

        if ((!text && !img) || isGenerating) return;

        isGenerating = true;
        userInput.value = "";
        userInput.dispatchEvent(new Event("input"));
        
        btnSend.classList.add("hidden");
        btnStop.classList.remove("hidden");
        
        stageIndicator.classList.remove("hidden");
        stageText.textContent = thinkHard ? "Analyzing deeply..." : "Thinking...";

        setStatus("thinking", thinkHard ? "Deep Thinking" : "Thinking");

        let displayText = text;
        if (img && !text) {
            displayText = "Analyze attached image";
        }
        appendUserMessage(displayText);

        // Reset image input after displaying in UI
        attachedImageBase64 = null;
        attachedImageName = "";
        if (mobileImageFile) mobileImageFile.value = "";
        if (mobileImagePreview) mobileImagePreview.classList.add("hidden");
        if (isThinkHardActive) {
            isThinkHardActive = false;
            if (mobileBtnThinkHard) mobileBtnThinkHard.classList.remove("active");
        }

        const { card, badgeContainer, body, btnSpeak } = createAssistantMessageCard();
        body.innerHTML = `<span class="streaming-cursor"></span>`;

        let accumulatedText = "";
        let hasShownWebSearch = false;
        activeAbortController = new AbortController();

        try {
            const token = getAuthToken();
            const headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "X-User-Session-ID": userId,
            };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }
            if (developerToken) {
                headers["X-Developer-Token"] = developerToken;
            }

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: headers,
                body: JSON.stringify({
                    message: text || "Analyze this image",
                    image_base64: img,
                    thinking_mode: thinkingMode,
                    think_hard: thinkHard,
                    developer_token: developerToken,
                    session_id: currentSessionId,
                    stream: true
                }),
                signal: activeAbortController.signal
            });

            if (response.status === 401) {
                showAuthModal();
                throw new Error("Authentication required. Please enter passkey.");
            }

            if (!response.ok) {
                throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop();

                for (const block of lines) {
                    if (!block.startsWith("data: ")) continue;
                    const jsonStr = block.substring(6).trim();
                    if (!jsonStr) continue;

                    try {
                        const evt = JSON.parse(jsonStr);

                        if (evt.type === "start") {
                            if (evt.session_id) {
                                currentSessionId = evt.session_id;
                                localStorage.setItem("ren_last_active_session", currentSessionId);
                            }
                        } else if (evt.type === "status") {
                            stageText.textContent = evt.message || `Stage: ${evt.stage}`;
                        } else if (evt.type === "tool") {
                            if (evt.tool === "web_search" && !hasShownWebSearch) {
                                hasShownWebSearch = true;
                                const pill = document.createElement("div");
                                pill.className = "web-search-pill";
                                pill.innerHTML = `🌐 Live Web Search Used`;
                                badgeContainer.appendChild(pill);
                            }
                            stageText.textContent = evt.message || `Tool: ${evt.tool}`;
                        } else if (evt.type === "skill_created") {
                            const skillCard = document.createElement("div");
                            skillCard.className = "skill-created-card";
                            skillCard.innerHTML = `
                                <div class="skill-created-icon">✨</div>
                                <div class="skill-created-info">
                                    <span class="skill-created-title">New Skill Created</span>
                                    <span class="skill-created-sub">${escapeHtml(evt.name || "Custom Automation Skill")} registered & ready</span>
                                </div>
                            `;
                            card.insertBefore(skillCard, body);
                            showToast(`✨ Skill created: ${evt.name}`, "success");
                        } else if (evt.type === "token") {
                            accumulatedText += evt.token;
                            body.innerHTML = renderMarkdown(accumulatedText) + `<span class="streaming-cursor"></span>`;
                            stageIndicator.classList.add("hidden");
                            scrollToBottom();
                        } else if (evt.type === "done") {
                            accumulatedText = evt.response || accumulatedText;
                            if (evt.session_id) {
                                currentSessionId = evt.session_id;
                                localStorage.setItem("ren_last_active_session", currentSessionId);
                            }
                            body.setAttribute("data-raw-text", accumulatedText);
                            body.innerHTML = renderMarkdown(accumulatedText);
                            scrollToBottom(true);

                            if (autoSpeak) {
                                playSpeech(accumulatedText, btnSpeak);
                            }

                            loadConversations();
                        } else if (evt.type === "error") {
                            showToast(`Error: ${evt.error}`, "error");
                            body.innerHTML += `<div style="color:var(--accent-red);margin-top:8px;">[Generation error: ${escapeHtml(evt.error)}]</div>`;
                        }
                    } catch (err) {
                        console.error("Error parsing SSE line:", err, jsonStr);
                    }
                }
            }

            body.setAttribute("data-raw-text", accumulatedText);
            body.innerHTML = renderMarkdown(accumulatedText || "Done.");

        } catch (error) {
            if (error.name === "AbortError") {
                body.innerHTML = renderMarkdown(accumulatedText) + `<div style="color:var(--text-muted);font-style:italic;margin-top:6px;">[Generation stopped]</div>`;
            } else {
                showToast(error.message, "error");
                body.innerHTML = `<div style="color:var(--accent-red);">${escapeHtml(error.message)}</div>`;
            }
        } finally {
            isGenerating = false;
            activeAbortController = null;
            btnStop.classList.add("hidden");
            btnSend.classList.remove("hidden");
            stageIndicator.classList.add("hidden");
            
            if (!autoSpeak || !activeAudioElement || activeAudioElement.paused) {
                setStatus(isSleeping ? "sleeping" : "online", isSleeping ? "Sleeping" : "Online");
            }
        }
    }

    // --- Stop Button Handler (Session-Isolated Stop) ---
    btnStop.addEventListener("click", async () => {
        if (activeAbortController) {
            activeAbortController.abort();
        }
        try {
            await apiFetch("/api/chat/stop", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: currentSessionId })
            });
        } catch (e) {
            console.warn("Failed to notify server of stop:", e);
        }
        if (activeAudioElement) {
            activeAudioElement.pause();
        }
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    });

    btnSend.addEventListener("click", sendMessage);

    // --- Camera Vision Snapshot Handler ---
    btnCamera.addEventListener("click", async () => {
        showToast("Taking camera snapshot...", "info");
        const snap = await sensors.takeCameraSnapshot();
        if (snap && snap.base64) {
            userInput.value = "What is in front of the camera?";
            userInput.dispatchEvent(new Event("input"));
            sendMessage();
        }
    });

    // --- Web Speech API (Microphone Input) ---
    function initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            btnMic.style.display = "none";
            return;
        }

        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onstart = () => {
            isListening = true;
            btnMic.classList.add("active");
            listeningBanner.classList.remove("hidden");
            transcriptPreview.textContent = "Listening... Speak now";
            setStatus("listening", "Listening");
        };

        recognition.onresult = (event) => {
            let interim = "";
            let finalTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interim += event.results[i][0].transcript;
                }
            }

            const current = finalTranscript || interim;
            transcriptPreview.textContent = current || "Listening...";
            userInput.value = current;
            userInput.dispatchEvent(new Event("input"));
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            if (event.error === "not-allowed") {
                showToast("Microphone permission denied", "error");
            }
            stopListening();
        };

        recognition.onend = () => {
            stopListening();
            if (userInput.value.trim().length > 0) {
                sendMessage();
            }
        };
    }

    function startListening() {
        if (!recognition) return;
        try {
            recognition.start();
        } catch (e) {
            console.warn("Recognition already started:", e);
        }
    }

    function stopListening() {
        isListening = false;
        btnMic.classList.remove("active");
        listeningBanner.classList.add("hidden");
        if (recognition) {
            try { recognition.stop(); } catch (e) {}
        }
        if (!isGenerating) {
            setStatus(isSleeping ? "sleeping" : "online", isSleeping ? "Sleeping" : "Online");
        }
    }

    btnMic.addEventListener("click", () => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    });

    btnCancelVoice.addEventListener("click", () => {
        userInput.value = "";
        userInput.dispatchEvent(new Event("input"));
        stopListening();
    });

    initSpeechRecognition();

    // --- Conversation Sessions Management (Strict User Scoping) ---
    async function loadConversations() {
        try {
            const res = await apiFetch("/api/conversations");
            if (!res.ok) return;

            const sessions = await res.json();
            conversationsList.innerHTML = "";

            if (sessions.length === 0) {
                conversationsList.innerHTML = `<div class="loading-state-mini">No past chats</div>`;
                return;
            }

            sessions.forEach(sess => {
                const item = document.createElement("div");
                item.className = `conversation-item ${sess.session_id === currentSessionId ? "active" : ""}`;
                item.setAttribute("data-session-id", sess.session_id);

                const title = document.createElement("span");
                title.className = "conv-title";
                title.textContent = sess.title || "Untitled Conversation";

                const delBtn = document.createElement("button");
                delBtn.className = "conv-delete-btn";
                delBtn.title = "Delete conversation";
                delBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;

                delBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    if (confirm(`Delete conversation "${sess.title}"?`)) {
                        await deleteConversation(sess.session_id);
                    }
                });

                item.appendChild(title);
                item.appendChild(delBtn);

                item.addEventListener("click", () => {
                    selectConversation(sess.session_id);
                    closeSidebar();
                });

                conversationsList.appendChild(item);
            });
        } catch (e) {
            console.error("Failed loading conversations:", e);
        }
    }

    async function selectConversation(sessionId) {
        if (isGenerating) return;
        currentSessionId = sessionId;
        localStorage.setItem("ren_last_active_session", currentSessionId);

        document.querySelectorAll(".conversation-item").forEach(el => {
            el.classList.toggle("active", el.getAttribute("data-session-id") === sessionId);
        });

        messagesList.innerHTML = "";
        welcomeView.classList.add("hidden");

        try {
            const res = await apiFetch(`/api/conversations/${sessionId}`);
            if (!res.ok) throw new Error("Conversation not found");

            const data = await res.json();
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    if (msg.role === "user") {
                        appendUserMessage(msg.content);
                    } else if (msg.role === "assistant") {
                        const { body } = createAssistantMessageCard();
                        body.setAttribute("data-raw-text", msg.content);
                        body.innerHTML = renderMarkdown(msg.content);
                    }
                });
                scrollToBottom(true);
            } else {
                welcomeView.classList.remove("hidden");
            }
        } catch (err) {
            showToast(err.message, "error");
            welcomeView.classList.remove("hidden");
        }
    }

    async function deleteConversation(sessionId) {
        try {
            const res = await apiFetch(`/api/conversations/${sessionId}`, { method: "DELETE" });
            if (res.ok) {
                showToast("Conversation deleted", "info");
                if (currentSessionId === sessionId) {
                    localStorage.removeItem("ren_last_active_session");
                    startNewChat();
                } else {
                    loadConversations();
                }
            }
        } catch (e) {
            showToast("Failed to delete conversation", "error");
        }
    }

    function startNewChat() {
        currentSessionId = null;
        localStorage.removeItem("ren_last_active_session");
        messagesList.innerHTML = "";
        welcomeView.classList.remove("hidden");
        userInput.value = "";
        userInput.dispatchEvent(new Event("input"));
        loadConversations();
        closeSidebar();
    }

    btnNewChat.addEventListener("click", startNewChat);
    btnHeaderNewChat.addEventListener("click", startNewChat);

    // --- Skills Viewer Modal ---
    async function loadSkills() {
        try {
            const res = await apiFetch("/api/skills");
            if (!res.ok) return;

            const skills = await res.json();
            skillsListContainer.innerHTML = "";

            if (skills.length === 0) {
                skillsListContainer.innerHTML = `<div class="loading-state-mini">No unlocked skills</div>`;
                return;
            }

            skills.forEach(sk => {
                const card = document.createElement("div");
                card.className = "skill-card";
                card.innerHTML = `
                    <div class="skill-card-header">
                        <span class="skill-title">${escapeHtml(sk.name)}</span>
                        <span class="skill-safety">${escapeHtml(sk.safety_level || "Safe")}</span>
                    </div>
                    <div class="skill-desc">${escapeHtml(sk.description || "Custom Python automation skill.")}</div>
                `;
                skillsListContainer.appendChild(card);
            });
        } catch (e) {
            console.error("Failed loading skills:", e);
        }
    }

    btnOpenSkills.addEventListener("click", () => {
        skillsModal.classList.remove("hidden");
        loadSkills();
    });

    btnCloseSkills.addEventListener("click", () => skillsModal.classList.add("hidden"));
    skillsBackdrop.addEventListener("click", () => skillsModal.classList.add("hidden"));

    // --- Multi-Device & QR Pairing Logic ---
    let qrTimerInterval = null;
    let currentPairingChallenge = null;

    function openDevicesModal() {
        if (devicesModal) {
            devicesModal.classList.remove("hidden");
            closeSidebar();
            switchDeviceTab("qr");
            loadPairingQR();
        }
    }

    function closeDevicesModal() {
        if (devicesModal) devicesModal.classList.add("hidden");
        if (qrTimerInterval) {
            clearInterval(qrTimerInterval);
            qrTimerInterval = null;
        }
    }

    function switchDeviceTab(tab) {
        if (!tabBtnPairQr || !tabBtnPairedList || !deviceViewQr || !deviceViewList) return;
        if (tab === "qr") {
            tabBtnPairQr.className = "btn btn-primary btn-sm";
            tabBtnPairedList.className = "btn btn-secondary btn-sm";
            deviceViewQr.classList.remove("hidden");
            deviceViewList.classList.add("hidden");
        } else {
            tabBtnPairQr.className = "btn btn-secondary btn-sm";
            tabBtnPairedList.className = "btn btn-primary btn-sm";
            deviceViewQr.classList.add("hidden");
            deviceViewList.classList.remove("hidden");
            loadPairedDevices();
        }
    }

    async function loadPairingQR() {
        if (!qrLoading || !qrContainer) return;
        qrLoading.classList.remove("hidden");
        qrLoading.textContent = "Generating Pairing QR...";
        qrContainer.classList.add("hidden");
        if (qrTimerInterval) {
            clearInterval(qrTimerInterval);
            qrTimerInterval = null;
        }

        try {
            const res = await apiFetch("/api/devices/pairing/qr");
            if (!res.ok) {
                qrLoading.textContent = "Failed to generate pairing QR.";
                return;
            }
            const data = await res.json();
            currentPairingChallenge = data;

            if (pairingQrImg) pairingQrImg.src = data.qr_image_base64;
            const codePart = (data.payload && data.payload.pairing_id) ? data.payload.pairing_id : data.pairing_id;
            if (pairingCodeLabel) pairingCodeLabel.textContent = codePart || "---";

            qrLoading.classList.add("hidden");
            qrContainer.classList.remove("hidden");

            let remaining = data.ttl_seconds || 300;
            if (pairingCountdown) pairingCountdown.textContent = `${remaining}s`;

            qrTimerInterval = setInterval(() => {
                remaining -= 1;
                if (remaining <= 0) {
                    clearInterval(qrTimerInterval);
                    qrTimerInterval = null;
                    if (pairingCountdown) pairingCountdown.textContent = "Expired";
                    if (pairingCodeLabel) pairingCodeLabel.textContent = "EXPIRED";
                } else {
                    if (pairingCountdown) pairingCountdown.textContent = `${remaining}s`;
                }
            }, 1000);
        } catch (e) {
            qrLoading.textContent = "Error loading pairing QR.";
        }
    }

    async function submitManualPairing() {
        const challengeInput = manualChallengeInput ? manualChallengeInput.value.trim() : "";
        const devName = (manualDevName && manualDevName.value.trim()) ? manualDevName.value.trim() : "Companion Phone";
        if (!challengeInput) {
            showToast("Please enter a pairing challenge code", "warn");
            return;
        }

        if (btnSubmitPairing) {
            btnSubmitPairing.disabled = true;
            btnSubmitPairing.textContent = "Verifying...";
        }

        try {
            let pairingId = currentPairingChallenge ? currentPairingChallenge.pairing_id : "";
            let challenge = challengeInput;
            if (challengeInput.startsWith("{")) {
                try {
                    const parsed = JSON.parse(challengeInput);
                    pairingId = parsed.pairing_id || pairingId;
                    challenge = parsed.challenge || challenge;
                } catch (e) {}
            }

            let myDevId = localStorage.getItem("ren_device_id");
            if (!myDevId) {
                myDevId = "phone_" + Math.random().toString(16).substring(2, 10);
                localStorage.setItem("ren_device_id", myDevId);
            }

            const platform = /iPhone|iPad|iPod/i.test(navigator.userAgent) ? "ios" : /Android/i.test(navigator.userAgent) ? "android" : "browser";

            const res = await apiFetch("/api/devices/pairing/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    pairing_id: pairingId,
                    challenge: challenge,
                    device_id: myDevId,
                    device_name: devName,
                    platform: platform,
                    capabilities: ["camera", "microphone", "sensors", "battery"]
                })
            });

            if (res.ok) {
                const creds = await res.json();
                if (creds.auth_token) {
                    setAuthToken(creds.auth_token);
                }
                localStorage.setItem("ren_device_id", creds.device_id || myDevId);
                showToast("Device linked & verified!", "success");
                if (manualChallengeInput) manualChallengeInput.value = "";
                switchDeviceTab("list");
                updateDeviceCountBadge();
            } else {
                const err = await res.json().catch(() => ({}));
                showToast(err.detail || "Pairing failed. Code expired or invalid.", "error");
            }
        } catch (e) {
            showToast("Connection failed during pairing", "error");
        } finally {
            if (btnSubmitPairing) {
                btnSubmitPairing.disabled = false;
                btnSubmitPairing.textContent = "Verify & Link This Device";
            }
        }
    }

    async function loadPairedDevices() {
        if (!pairedDevicesContainer) return;
        pairedDevicesContainer.innerHTML = `<div class="loading-state-mini">Loading paired devices...</div>`;

        try {
            const res = await apiFetch("/api/devices");
            if (!res.ok) {
                pairedDevicesContainer.innerHTML = `<div class="loading-state-mini">Failed to load devices</div>`;
                return;
            }
            const devices = await res.json();
            if (devices.length === 0) {
                pairedDevicesContainer.innerHTML = `<div class="loading-state-mini">No companion devices paired yet.</div>`;
                return;
            }

            pairedDevicesContainer.innerHTML = "";
            devices.forEach(d => {
                const item = document.createElement("div");
                item.className = "device-item";

                const isConnected = d.connection_state === "connected";
                const badgeClass = isConnected ? "device-badge-active" : "device-badge-inactive";
                const badgeText = isConnected ? "Active" : (d.connection_state || "Offline");

                let batteryText = "";
                if (d.battery && d.battery.level !== undefined) {
                    batteryText = ` • 🔋 ${d.battery.level}%`;
                }

                item.innerHTML = `
                    <div class="device-info-col">
                        <div class="device-item-name">
                            <span>${d.platform === "android" || d.platform === "ios" ? "📱" : "💻"} ${escapeHtml(d.device_name || d.device_id)}</span>
                            <span class="${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="device-item-meta">
                            Platform: ${escapeHtml(d.platform || "host")} | ID: ${escapeHtml(d.device_id.substring(0, 12))}${batteryText}
                        </div>
                    </div>
                    <button class="device-action-btn" data-dev-id="${escapeHtml(d.device_id)}">Revoke</button>
                `;

                const btnRevoke = item.querySelector(".device-action-btn");
                btnRevoke.addEventListener("click", async () => {
                    if (confirm(`Revoke pairing for "${d.device_name || d.device_id}"?`)) {
                        await revokeDevice(d.device_id);
                    }
                });

                pairedDevicesContainer.appendChild(item);
            });

            if (deviceCountLabel) {
                deviceCountLabel.textContent = `${devices.length} Device${devices.length === 1 ? "" : "s"}`;
            }
        } catch (e) {
            pairedDevicesContainer.innerHTML = `<div class="loading-state-mini">Error loading devices</div>`;
        }
    }

    async function revokeDevice(deviceId) {
        try {
            const res = await apiFetch(`/api/devices/${deviceId}/revoke`, { method: "POST" });
            if (res.ok) {
                showToast("Device revoked", "info");
                loadPairedDevices();
                updateDeviceCountBadge();
            } else {
                showToast("Failed to revoke device", "error");
            }
        } catch (e) {
            showToast("Network error revoking device", "error");
        }
    }

    async function updateDeviceCountBadge() {
        try {
            const res = await apiFetch("/api/devices");
            if (res.ok) {
                const devices = await res.json();
                if (deviceCountLabel) {
                    deviceCountLabel.textContent = `${devices.length} Device${devices.length === 1 ? "" : "s"}`;
                }
            }
        } catch (e) {}
    }

    async function sendDeviceHeartbeat() {
        const devId = localStorage.getItem("ren_device_id");
        if (!devId) return;

        let batteryInfo = null;
        if (sensors && sensors.battery) {
            batteryInfo = {
                level: Math.round(sensors.battery.level * 100),
                charging: !!sensors.battery.charging
            };
        }

        try {
            await apiFetch("/api/devices/heartbeat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    device_id: devId,
                    battery: batteryInfo,
                    storage: {}
                })
            });
        } catch (e) {}
    }

    if (btnOpenDevices) btnOpenDevices.addEventListener("click", openDevicesModal);
    if (deviceBadge) deviceBadge.addEventListener("click", openDevicesModal);
    if (btnCloseDevices) btnCloseDevices.addEventListener("click", closeDevicesModal);
    if (devicesBackdrop) devicesBackdrop.addEventListener("click", closeDevicesModal);
    if (tabBtnPairQr) tabBtnPairQr.addEventListener("click", () => switchDeviceTab("qr"));
    if (tabBtnPairedList) tabBtnPairedList.addEventListener("click", () => switchDeviceTab("list"));
    if (btnRefreshQr) btnRefreshQr.addEventListener("click", loadPairingQR);
    if (btnSubmitPairing) btnSubmitPairing.addEventListener("click", submitManualPairing);

    // --- Network Connectivity Listeners ---
    window.addEventListener("online", () => {
        showToast("Phone internet connection restored", "info");
        fetchSystemStatus();
    });

    window.addEventListener("offline", () => {
        setStatus("internet-offline", "No Internet");
        showToast("Internet connection lost on your phone. Please check data/Wi-Fi.", "error");
    });

    // --- Telemetry Polling (Status & Health) ---
    async function fetchSystemStatus() {
        if (!navigator.onLine) {
            setStatus("internet-offline", "No Internet");
            return;
        }

        try {
            const res = await apiFetch("/api/status");
            
            if (res.status === 401 || res.status === 403) {
                setStatus("auth-failed", "Auth Required");
                return;
            }

            if (!res.ok) {
                setStatus("tunnel-offline", "Server Error");
                return;
            }

            const data = await res.json();
            if (data.system) {
                systemCpuRamVal.textContent = `${data.system.cpu_percent.toFixed(0)}% / ${data.system.ram_percent.toFixed(0)}%`;
            }
            if (data.agent) {
                systemModelVal.textContent = data.agent.active_model || "hermes3:3b";
            }

            if (data.ollama && data.ollama.online === false) {
                if (!isGenerating) {
                    setStatus("ollama-offline", "Ollama Offline");
                }
            } else if (!isGenerating && !isSleeping) {
                setStatus("online", "Online");
            }
        } catch (e) {
            if (!navigator.onLine) {
                setStatus("internet-offline", "No Internet");
            } else if (!isGenerating) {
                setStatus("tunnel-offline", "Tunnel Offline");
            }
        }
    }

    // --- Check Authentication Requirement on Startup ---
    async function checkAuthRequirement() {
        try {
            const res = await fetch("/api/auth/check");
            if (res.ok) {
                const data = await res.json();
                if (data.auth_required) {
                    authStatusContainer.classList.remove("hidden");
                    if (!getAuthToken()) {
                        showAuthModal();
                        return false;
                    }
                }
            }
        } catch (e) {
            if (!navigator.onLine) {
                setStatus("internet-offline", "No Internet");
            } else {
                setStatus("tunnel-offline", "Tunnel Offline");
            }
        }
        return true;
    }

    // --- REN 2.0 Image & Think Hard Event Listeners ---
    if (mobileImageFile) {
        mobileImageFile.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    attachedImageBase64 = evt.target.result;
                    attachedImageName = file.name;
                    mobilePreviewName.textContent = file.name;
                    mobileImagePreview.classList.remove("hidden");
                    showToast(`📎 Image attached: ${file.name}`, "info");
                };
                reader.readAsDataURL(file);
            }
        });
    }

    if (mobileBtnClearImage) {
        mobileBtnClearImage.addEventListener("click", () => {
            attachedImageBase64 = null;
            attachedImageName = "";
            mobileImageFile.value = "";
            mobileImagePreview.classList.add("hidden");
        });
    }

    if (btnCamera) {
        btnCamera.addEventListener("click", () => {
            if (mobileImageFile) mobileImageFile.click();
        });
    }

    if (mobileBtnThinkHard) {
        mobileBtnThinkHard.addEventListener("click", () => {
            isThinkHardActive = !isThinkHardActive;
            mobileBtnThinkHard.classList.toggle("active", isThinkHardActive);
            if (isThinkHardActive) {
                showToast("🧠 Think Hard armed: Deep reasoning enabled for next request", "info");
            }
        });
    }

    // --- Developer Mode Modal Handlers ---
    if (btnOpenDev) {
        btnOpenDev.addEventListener("click", () => {
            devModal.classList.remove("hidden");
            if (developerToken) {
                devAuthSection.classList.add("hidden");
                devActiveSection.classList.remove("hidden");
            } else {
                devAuthSection.classList.remove("hidden");
                devActiveSection.classList.add("hidden");
            }
        });
    }

    if (btnCloseDev) {
        btnCloseDev.addEventListener("click", () => devModal.classList.add("hidden"));
    }
    if (devBackdrop) {
        devBackdrop.addEventListener("click", () => devModal.classList.add("hidden"));
    }

    if (btnSubmitDevAuth) {
        btnSubmitDevAuth.addEventListener("click", async () => {
            const secret = devSecretInput.value.trim();
            if (!secret) return;
            try {
                const res = await apiFetch("/api/developer/auth", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ secret: secret })
                });
                if (res.ok) {
                    const data = await res.json();
                    developerToken = data.token;
                    localStorage.setItem("ren_dev_token", developerToken);
                    devAuthSection.classList.add("hidden");
                    devActiveSection.classList.remove("hidden");
                    showToast("🛠️ Developer Mode Authorized!", "success");
                } else {
                    showToast("Invalid Developer Secret", "error");
                }
            } catch (e) {
                showToast("Auth request failed", "error");
            }
        });
    }

    if (btnRevokeDev) {
        btnRevokeDev.addEventListener("click", async () => {
            try {
                await apiFetch("/api/developer/revoke", { method: "POST" });
            } catch (e) {}
            developerToken = null;
            localStorage.removeItem("ren_dev_token");
            devModal.classList.add("hidden");
            showToast("Developer Mode deactivated.", "info");
        });
    }

    // --- Autonomous Proactive Initiative Sync ---
    async function checkAutonomousNotifications() {
        try {
            const res = await apiFetch("/api/autonomy/pending");
            if (res.ok) {
                const msgs = await res.json();
                for (const m of msgs) {
                    // Render proactive message card
                    const { card, badgeContainer, body } = createAssistantMessageCard();
                    const pill = document.createElement("div");
                    pill.className = "autonomous-badge";
                    pill.innerHTML = `🪐 REN Initiative (${escapeHtml(m.source || "Insight")})`;
                    badgeContainer.appendChild(pill);
                    body.setAttribute("data-raw-text", m.content);
                    body.innerHTML = renderMarkdown(m.content);
                    scrollToBottom(true);
                    showToast(`🪐 Proactive Insight: ${m.title}`, "info");

                    // Acknowledge delivery
                    await apiFetch("/api/autonomy/ack", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ message_id: m.message_id })
                    });
                }
            }
        } catch (e) {}
    }

    // --- Startup Boot Sequence ---
    async function boot() {
        if (!navigator.onLine) {
            setStatus("internet-offline", "No Internet");
        }

        const canProceed = await checkAuthRequirement();
        if (!canProceed) return;

        // Show awakening calibration modal if first run
        if (!sensors.hasAwakened) {
            sensors.showAwakeningModal();
        }

        await fetchSystemStatus();
        await updateDeviceCountBadge();
        await sendDeviceHeartbeat();
        await loadConversations();
        await checkAutonomousNotifications();

        // Restore last active session if saved and belongs to this user
        const lastSessionId = localStorage.getItem("ren_last_active_session");
        if (lastSessionId) {
            await selectConversation(lastSessionId);
        } else {
            // Load most recent conversation
            try {
                const res = await apiFetch("/api/conversations");
                if (res.ok) {
                    const sessions = await res.json();
                    if (sessions.length > 0) {
                        selectConversation(sessions[0].session_id);
                    }
                }
            } catch (e) {}
        }

        setInterval(fetchSystemStatus, 10000);
        setInterval(checkAutonomousNotifications, 20000);
        setInterval(updateDeviceCountBadge, 30000);
        setInterval(sendDeviceHeartbeat, 45000);
    }

    boot();
});
