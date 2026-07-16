/* main.js - Dynamic Particle Dynosphere & Webview Bridge */

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const btnInitialize = document.getElementById("btn-initialize");
    const startupScreen = document.getElementById("startup-screen");
    const statusVal = document.getElementById("system-status-val");
    const indicator = document.querySelector(".status-indicator");
    const timeVal = document.getElementById("current-time");
    const consoleLogs = document.getElementById("console-logs");

    const userSpeechRow = document.getElementById("user-speech-row");
    const userSpeechText = document.getElementById("user-speech-text");
    const assistantSpeechRow = document.getElementById("assistant-speech-row");
    const assistantSpeechText = document.getElementById("assistant-speech-text");

    const cpuFill = document.getElementById("cpu-fill");
    const ramFill = document.getElementById("ram-fill");
    const diskFill = document.getElementById("disk-fill");
    const cpuVal = document.getElementById("cpu-val");
    const ramVal = document.getElementById("ram-val");
    const diskVal = document.getElementById("disk-val");

    // Audio & Particle Canvas State
    const canvas = document.getElementById("dynosphere-canvas");
    const ctx = canvas.getContext("2d");
    const sphereCore = document.querySelector(".sphere-core");

    let audioContext = null;
    let analyser = null;
    let microphone = null;
    let dataArray = null;
    let volume = 0; // Real-time volume (0 to 1)

    // Canvas sizing
    function resizeCanvas() {
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
    }
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // 3D Particles Definition
    const particles = [];
    const particleCount = 280;
    const sphereRadius = 90;
    const focalLength = 200;

    // Create random spherical coordinates
    for (let i = 0; i < particleCount; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);
        
        particles.push({
            x: sphereRadius * Math.sin(phi) * Math.cos(theta),
            y: sphereRadius * Math.sin(phi) * Math.sin(theta),
            z: sphereRadius * Math.cos(phi),
            origX: sphereRadius * Math.sin(phi) * Math.cos(theta),
            origY: sphereRadius * Math.sin(phi) * Math.sin(theta),
            origZ: sphereRadius * Math.cos(phi),
            size: Math.random() * 2 + 1
        });
    }

    // Rotation angles
    let angleX = 0.003;
    let angleY = 0.005;

    // Log to virtual console
    function logToHUD(message, type = "system") {
        const entry = document.createElement("div");
        entry.className = `log-entry ${type}-log`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        consoleLogs.appendChild(entry);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Update digital clock
    function updateClock() {
        const now = new Date();
        timeVal.textContent = now.toTimeString().split(' ')[0];
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Web Audio Setup for Real-time Visualizer
    async function initAudio() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            microphone = audioContext.createMediaStreamSource(stream);

            analyser.fftSize = 256;
            const bufferLength = analyser.frequencyBinCount;
            dataArray = new Uint8Array(bufferLength);

            microphone.connect(analyser);
            logToHUD("Vocal sensor network ONLINE.", "system");
        } catch (err) {
            logToHUD("Vocal input permission denied. Using ambient simulation.", "system");
            console.error("Audio init error:", err);
        }
    }

    // Main Canvas Render Loop
    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;

        // Process audio input
        if (analyser && dataArray) {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            volume = avg / 128; // Normalize volume
        } else {
            // Ambient pulse simulation if audio is missing
            volume = 0.1 + Math.sin(Date.now() * 0.002) * 0.05;
        }

        // Apply audio levels to sphere mechanics
        const currentRadiusMult = 1 + (volume * 0.65); // Expand up to 65%
        const dynRotSpeedX = 0.003 + (volume * 0.05); // Rotate faster when speaking
        const dynRotSpeedY = 0.005 + (volume * 0.05);

        // Core visual pulse
        const coreScale = 1 + (volume * 0.4);
        sphereCore.style.transform = `scale(${coreScale})`;
        sphereCore.style.opacity = 0.6 + (volume * 0.4);

        // Rotate in 3D
        const cosX = Math.cos(dynRotSpeedX);
        const sinX = Math.sin(dynRotSpeedX);
        const cosY = Math.cos(dynRotSpeedY);
        const sinY = Math.sin(dynRotSpeedY);

        // Sort particles by Z-depth for 3D sorting (painters algorithm)
        particles.sort((a, b) => b.z - a.z);

        // Render particles
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];

            // 3D rotation X-axis
            let y1 = p.y * cosX - p.z * sinX;
            let z1 = p.z * cosX + p.y * sinX;

            // 3D rotation Y-axis
            let x2 = p.x * cosY - z1 * sinY;
            let z2 = z1 * cosY + p.x * sinY;

            p.x = x2;
            p.y = y1;
            p.z = z2;

            // Scale particle distance dynamically based on audio volume
            const dx = p.x * currentRadiusMult;
            const dy = p.y * currentRadiusMult;
            const dz = p.z;

            // 3D perspective projection
            const scale = focalLength / (focalLength + dz);
            const screenX = centerX + dx * scale;
            const screenY = centerY + dy * scale;

            if (screenX >= 0 && screenX <= canvas.width && screenY >= 0 && screenY <= canvas.height) {
                // Compute visual properties based on depth Z
                const depthAlpha = (dz + sphereRadius) / (2 * sphereRadius); // 0 to 1
                const alpha = 0.25 + (depthAlpha * 0.6) + (volume * 0.15);
                const size = p.size * scale * (0.8 + volume * 0.4);

                // Neon color shift based on volume
                let color;
                if (volume > 0.4) {
                    // Shift to brighter cyan/white glow when louder
                    color = `rgba(180, 244, 255, ${alpha})`;
                } else {
                    // Default neon blue
                    color = `rgba(0, 240, 255, ${alpha})`;
                }

                ctx.beginPath();
                ctx.arc(screenX, screenY, size, 0, Math.PI * 2);
                ctx.fillStyle = color;
                
                // Add soft glow to closer particles
                if (dz < -50) {
                    ctx.shadowBlur = 8;
                    ctx.shadowColor = "rgba(0, 240, 255, 0.8)";
                } else {
                    ctx.shadowBlur = 0;
                }

                ctx.fill();
            }
        }

        // Draw HUD circle brackets around the sphere
        ctx.shadowBlur = 0;
        ctx.strokeStyle = `rgba(6, 182, 212, ${0.15 + volume * 0.25})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(centerX, centerY, 130 + (volume * 40), 0, Math.PI * 2);
        ctx.stroke();

        requestAnimationFrame(render);
    }

    // Diagnostics polling loop
    function updateDiagnostics() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_system_status().then((status) => {
                if (status) {
                    // Extract usage percentages
                    // Format from system_monitor:
                    // {"Your operating system is ": "Windows", " the current cpu usage is": cpuusage, " ram currently consumed is": ramusage, " The disk usage is": diskusage}
                    const cpu = status[" the current cpu usage is"] || 0;
                    const ram = status[" ram currently consumed is"] || 0;
                    const disk = status[" The disk usage is"] || 0;
                    const os = status["Your operating system is "] || "WINDOWS";

                    document.getElementById("host-os").textContent = os.toUpperCase();

                    // Update UI fill bars & values
                    cpuFill.style.width = `${cpu}%`;
                    cpuVal.textContent = `${cpu}%`;
                    
                    ramFill.style.width = `${ram}%`;
                    ramVal.textContent = `${ram}%`;

                    diskFill.style.width = `${disk}%`;
                    diskVal.textContent = `${disk}%`;

                    // Trigger Warning color on high CPU/RAM
                    if (cpu > 80) cpuVal.style.color = "#ef4444";
                    else cpuVal.style.color = "var(--neon-blue)";
                    
                    if (ram > 80) ramVal.style.color = "#ef4444";
                    else ramVal.style.color = "var(--neon-blue)";
                }
            }).catch(err => {
                console.error("Diagnostics fetch failed:", err);
            });
        }
    }

    // Typewriter text printing utility
    function typeText(element, text, speed = 30) {
        element.textContent = "";
        let i = 0;
        clearInterval(element.typeInterval);
        element.typeInterval = setInterval(() => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
            } else {
                clearInterval(element.typeInterval);
            }
        }, speed);
    }

    // Exposed endpoints called by Python backend via evaluate_js
    window.updateStatus = (status) => {
        status = status.toUpperCase();
        statusVal.textContent = status;
        
        // Adjust status LED indicator
        indicator.className = "status-indicator";
        if (status === "OFFLINE" || status === "OFF") {
            indicator.classList.add("offline");
        } else if (status === "THINKING" || status === "ANALYZING" || status === "SPEAKING") {
            indicator.classList.add("thinking");
        } else {
            indicator.classList.add("online");
        }

        // Toggle HUD diagnostics and modules
        if (status === "ACTIVE" || status === "LISTENING") {
            document.getElementById("mod-gesture").classList.add("active");
            document.getElementById("mod-gesture-status").textContent = "ACTIVE";
            document.getElementById("mod-gesture-status").className = "mod-status text-cyan";
        }

        logToHUD(`Core status update: ${status}`, "system");
    };

    window.updateUserSpeech = (text) => {
        userSpeechRow.classList.remove("hidden");
        userSpeechText.textContent = text;
        logToHUD(`User Speech Input: "${text}"`, "user");
    };

    window.updateAssistantSpeech = (text) => {
        assistantSpeechRow.classList.remove("hidden");
        typeText(assistantSpeechText, text, 20);
        logToHUD(`Ren Output: "${text}"`, "ren");
    };

    window.updateModuleStatus = (moduleName, statusText, isActive) => {
        let dotId, statusId;
        if (moduleName === "gesture") {
            dotId = "mod-gesture";
            statusId = "mod-gesture-status";
        } else if (moduleName === "nn") {
            dotId = "mod-nn";
            statusId = "mod-nn-status";
        }

        if (dotId && statusId) {
            const dot = document.getElementById(dotId);
            const status = document.getElementById(statusId);
            
            status.textContent = statusText.toUpperCase();
            if (isActive) {
                dot.classList.add("active");
                status.className = "mod-status text-cyan";
            } else {
                dot.classList.remove("active");
                status.className = "mod-status";
            }
            logToHUD(`Module ${moduleName.toUpperCase()} transition: ${statusText.toUpperCase()}`, "system");
        }
    };

    window.showPopup = (data) => {
        const popup = document.getElementById("advancement-popup");
        const titleEl = popup.querySelector(".advancement-title");
        const descEl = document.getElementById("advancement-name");
        const iconEl = popup.querySelector(".advancement-icon");

        titleEl.textContent = (data.title || "ADVANCEMENT UNLOCKED").toUpperCase();
        descEl.textContent = data.message || "";
        
        if (data.type === "advancement") {
            popup.style.borderColor = "#eab308";
            titleEl.style.color = "#eab308";
            iconEl.textContent = "🏆";
            popup.style.boxShadow = "0 0 25px rgba(234, 179, 8, 0.4), inset 0 0 10px rgba(234, 179, 8, 0.2)";
        } else {
            popup.style.borderColor = "var(--neon-blue)";
            titleEl.style.color = "var(--neon-blue)";
            iconEl.textContent = "⚙️";
            popup.style.boxShadow = "0 0 25px rgba(0, 240, 255, 0.4), inset 0 0 10px rgba(0, 240, 255, 0.2)";
        }

        popup.classList.remove("hidden");
        popup.offsetHeight; 
        popup.classList.add("show");

        logToHUD(`Popup triggered: ${data.title} - ${data.message}`, "system");

        setTimeout(() => {
            popup.classList.remove("show");
            setTimeout(() => {
                popup.classList.add("hidden");
            }, 500);
        }, 4000);
    };

    window.updateSkillsList = (skills) => {
        const list = document.getElementById("skills-list");
        list.innerHTML = "";
        if (!skills || skills.length === 0) {
            list.innerHTML = '<div class="skill-item" style="color: rgba(226, 232, 240, 0.5);">No skills unlocked yet.</div>';
            return;
        }
        skills.forEach(skill => {
            const item = document.createElement("div");
            item.className = "skill-item";
            item.textContent = skill;
            list.appendChild(item);
        });
    };

    // Prompt submission
    const promptInput = document.getElementById("prompt-input");
    const btnSubmitPrompt = document.getElementById("btn-submit-prompt");

    function submitPrompt() {
        const prompt = promptInput.value.trim();
        if (prompt && window.pywebview && window.pywebview.api) {
            logToHUD(`Queued typed instruction: "${prompt}"`, "user");
            window.pywebview.api.submit_prompt(prompt).then((msg) => {
                logToHUD(msg, "system");
            });
            promptInput.value = "";
        }
    }

    btnSubmitPrompt.addEventListener("click", submitPrompt);
    promptInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            submitPrompt();
        }
    });

    // Initialize core system click trigger
    btnInitialize.addEventListener("click", async () => {
        logToHUD("Core reactor ignition sequence authorized.", "system");
        btnInitialize.disabled = true;
        btnInitialize.querySelector(".btn-text").textContent = "BOOTING CORE...";

        // Start local Audio visualizer analysis
        await initAudio();
        render();

        // Delay overlay fadeout for dramatic bootup sequence effect
        setTimeout(() => {
            startupScreen.style.opacity = "0";
            startupScreen.style.pointerEvents = "none";
            logToHUD("Core UI initialized. Launching backend cognitive thread...", "system");

            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.start_assistant()
                    .then(msg => {
                        logToHUD(msg, "system");
                        // Start diagnostics updates
                        setInterval(updateDiagnostics, 2000);
                        updateDiagnostics();
                        // Populate skills list on startup
                        if (window.pywebview.api.refresh_skills) {
                            window.pywebview.api.refresh_skills();
                        }
                        isBooted = true;
                        resetIdleTimer();
                    })
                    .catch(err => {
                        logToHUD(`Cognitive thread crash error: ${err}`, "system");
                    });
            } else {
                logToHUD("Warning: Pywebview API bindings not detected. Running UI client sandbox.", "system");
                window.updateStatus("SANDBOXED");
            }
        }, 1500);
    });

    // Reflect/Dream Mode handlers
    const reflectPanel = document.getElementById("reflect-panel");
    const dreamLogsContainer = document.getElementById("dream-logs");
    const dreamEntropyVal = document.getElementById("dream-entropy");
    const container = document.querySelector(".container");

    let entropyInterval = null;

    window.setReflectMode = function(active, logs) {
        if (active) {
            container.classList.add("reflect-active");
            reflectPanel.classList.remove("hidden");
            
            // Populate dream logs
            dreamLogsContainer.innerHTML = "";
            if (logs && logs.length > 0) {
                logs.forEach((logText, idx) => {
                    setTimeout(() => {
                        const line = document.createElement("div");
                        let cleanText = logText;
                        let className = "resolving";
                        
                        if (logText.startsWith("RESEARCHED:")) {
                            className = "researched";
                            cleanText = logText.replace("RESEARCHED:", "").trim();
                        } else if (logText.startsWith("READING:")) {
                            className = "reading";
                            cleanText = logText.replace("READING:", "").trim();
                        } else if (logText.startsWith("SYSTEM:")) {
                            className = "system";
                            cleanText = logText.replace("SYSTEM:", "").trim();
                        } else if (logText.startsWith("LEARNED:")) {
                            className = "learned";
                            cleanText = logText.replace("LEARNED:", "").trim();
                        } else if (logText.startsWith("RESOLVED:")) {
                            className = "learned";
                        } else if (logText.startsWith("ANALYZING:")) {
                            className = "analyzing";
                        }
                        
                        line.className = "dream-line " + className;
                        line.textContent = cleanText;
                        dreamLogsContainer.appendChild(line);
                        dreamLogsContainer.scrollTop = dreamLogsContainer.scrollHeight;
                    }, idx * 800);
                });
            } else {
                dreamLogsContainer.innerHTML = "<div class='dream-line analyzing'>Reflecting on baseline cognition weights...</div>";
            }

            // Simulate entropy fluctuations
            let entropy = 0.00;
            clearInterval(entropyInterval);
            entropyInterval = setInterval(() => {
                entropy = (Math.random() * 5).toFixed(2);
                dreamEntropyVal.textContent = entropy + "%";
            }, 1500);

            logToHUD("Cognitive reflection cycle authorized. Dreams initialized.", "system");
        } else {
            container.classList.remove("reflect-active");
            reflectPanel.classList.add("hidden");
            clearInterval(entropyInterval);
            dreamEntropyVal.textContent = "0.00%";
            logToHUD("Cognitive state restored to awake.", "system");
        }
    };

    // Idle Timer for Dream Mode
    let idleTimeout = null;
    let isReflecting = false;
    let isBooted = false;

    function resetIdleTimer() {
        if (!isBooted) return;
        clearTimeout(idleTimeout);
        
        // If we are currently in dream mode, any key/mouse activity wakes us up!
        if (isReflecting) {
            isReflecting = false;
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.exit_reflect_mode()
                    .then(msg => {
                        logToHUD(msg, "system");
                    });
            }
        }
        
        // Set idle timeout of 1 minute (60,000ms)
        idleTimeout = setTimeout(() => {
            if (!isReflecting) {
                isReflecting = true;
                if (window.pywebview && window.pywebview.api) {
                    window.pywebview.api.enter_reflect_mode()
                        .then(msg => {
                            logToHUD(msg, "system");
                        });
                }
            }
        }, 60000);
    }

    // Attach user activity listeners
    window.addEventListener("mousemove", resetIdleTimer);
    window.addEventListener("keydown", resetIdleTimer);
    window.addEventListener("click", resetIdleTimer);
});
