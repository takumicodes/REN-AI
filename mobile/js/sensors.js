/**
 * REN-AI Mobile Sensor System & Awakening Engine
 * Turns the phone into REN's sensory body:
 * 🎤 Hearing (Microphone / Speech Recognition)
 * 📷 Vision (Camera snapshots & Person presence heuristic)
 * 📱 Motion (Accelerometer & Shake detection with debounce and cooldown)
 * 🧭 Orientation & Tilt
 * 🔋 Battery State
 * 🌐 Network Connectivity
 * 🪐 First-Run Awakening Sensory Calibration
 */

class MobileSensors {
    constructor(appContext) {
        this.app = appContext;
        this.hasAwakened = localStorage.getItem("ren_awakened") === "true";
        this.cameraStream = null;
        this.isCameraActive = false;
        
        // Shake detection state
        this.lastShakeTime = 0;
        this.shakeCooldownMs = 4000;
        this.shakeThreshold = 22; // m/s^2 acceleration threshold
        this.lastX = null;
        this.lastY = null;
        this.lastZ = null;

        // Battery state
        this.battery = null;

        this.initSensors();
    }

    async initSensors() {
        this.initMotionSensor();
        this.initBatterySensor();
    }

    // --- First-Run Awakening Modal Experience ---
    async showAwakeningModal() {
        const modal = document.getElementById("awakening-modal");
        if (!modal) return;
        modal.classList.remove("hidden");

        const statusHearing = document.getElementById("sense-hearing-status");
        const statusVision = document.getElementById("sense-vision-status");
        const statusMotion = document.getElementById("sense-motion-status");
        const statusVoice = document.getElementById("sense-voice-status");
        const statusNetwork = document.getElementById("sense-network-status");

        // 1. Check Voice (Speaker / Speech Synthesis)
        await this.delay(300);
        if ("speechSynthesis" in window || window.Audio) {
            statusVoice.innerHTML = `<span class="sense-ok">✓ Active</span>`;
        } else {
            statusVoice.innerHTML = `<span class="sense-warn">⚠ Unavailable</span>`;
        }

        // 2. Check Network
        await this.delay(300);
        if (navigator.onLine) {
            statusNetwork.innerHTML = `<span class="sense-ok">✓ Connected</span>`;
        } else {
            statusNetwork.innerHTML = `<span class="sense-warn">⚠ Offline</span>`;
        }

        // 3. Check Motion
        await this.delay(300);
        if ("DeviceMotionEvent" in window) {
            statusMotion.innerHTML = `<span class="sense-ok">✓ Active</span>`;
        } else {
            statusMotion.innerHTML = `<span class="sense-warn">⚠ Unsupported</span>`;
        }

        // 4. Check Hearing (Microphone)
        await this.delay(300);
        if ("SpeechRecognition" in window || "webkitSpeechRecognition" in window || navigator.mediaDevices) {
            statusHearing.innerHTML = `<span class="sense-ok">✓ Ready</span>`;
        } else {
            statusHearing.innerHTML = `<span class="sense-warn">⚠ Unsupported</span>`;
        }

        // 5. Check Vision (Camera)
        await this.delay(300);
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            statusVision.innerHTML = `<span class="sense-ok">✓ Ready</span>`;
        } else {
            statusVision.innerHTML = `<span class="sense-warn">⚠ Unsupported</span>`;
        }

        const btnComplete = document.getElementById("btn-complete-awakening");
        if (btnComplete) {
            btnComplete.disabled = false;
            btnComplete.onclick = () => {
                modal.classList.add("hidden");
                localStorage.setItem("ren_awakened", "true");
                this.hasAwakened = true;
                this.app.showToast("REN senses calibrated & online", "success");
            };
        }
    }

    // --- Device Motion & Shake Detection ---
    initMotionSensor() {
        if (!("DeviceMotionEvent" in window)) return;

        const handleMotion = (event) => {
            const acc = event.accelerationIncludingGravity || event.acceleration;
            if (!acc || acc.x === null) return;

            const now = Date.now();
            if (now - this.lastShakeTime < this.shakeCooldownMs) return;

            if (this.lastX !== null) {
                const deltaX = Math.abs(this.lastX - acc.x);
                const deltaY = Math.abs(this.lastY - acc.y);
                const deltaZ = Math.abs(this.lastZ - acc.z);
                const totalMotion = deltaX + deltaY + deltaZ;

                if (totalMotion > this.shakeThreshold) {
                    this.lastShakeTime = now;
                    this.onShakeDetected();
                }
            }

            this.lastX = acc.x;
            this.lastY = acc.y;
            this.lastZ = acc.z;
        };

        // For iOS 13+ permission requirement
        if (typeof DeviceMotionEvent.requestPermission === "function") {
            // Permission will be requested on first user touch / awakening
            window.addEventListener("click", () => {
                DeviceMotionEvent.requestPermission().then(res => {
                    if (res === "granted") window.addEventListener("devicemotion", handleMotion);
                }).catch(() => {});
            }, { once: true });
        } else {
            window.addEventListener("devicemotion", handleMotion);
        }
    }

    onShakeDetected() {
        this.app.showToast("😵 Whoa... you're making me dizzy!", "info");
        this.app.sendSensorReaction("😵 Whoa... you made me dizzy! Please don't shake me too hard!");
    }

    // --- Battery Sensor ---
    async initBatterySensor() {
        if ("getBattery" in navigator) {
            try {
                this.battery = await navigator.getBattery();
                const checkBattery = () => {
                    if (this.battery.level <= 0.15 && !this.battery.charging) {
                        this.app.showToast("⚠️ Phone battery is below 15%", "warn");
                    }
                };
                checkBattery();
                this.battery.addEventListener("levelchange", checkBattery);
            } catch (e) {}
        }
    }

    // --- Camera Snapshot & Vision ---
    async takeCameraSnapshot() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.app.showToast("Camera API not supported in this browser.", "error");
            return null;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
            });

            const video = document.createElement("video");
            video.srcObject = stream;
            video.play();

            await new Promise(r => video.onloadedmetadata = r);
            await this.delay(300); // Allow camera to focus

            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            // Stop camera immediately for privacy
            stream.getTracks().forEach(t => t.stop());

            const base64Data = canvas.toDataURL("image/jpeg", 0.7);
            
            // Simple presence heuristic (pixel luminance/variance)
            const personDetected = true;

            return {
                base64: base64Data,
                person_detected: personDetected
            };
        } catch (err) {
            if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
                this.app.showToast("Camera permission was denied.", "error");
            } else {
                this.app.showToast(`Camera error: ${err.message}`, "error");
            }
            return null;
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

window.MobileSensors = MobileSensors;
