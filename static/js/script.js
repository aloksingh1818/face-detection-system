// Global variables
let video = null;
let stream = null;
let recognitionActive = false;
let lastRecognitionTime = Date.now();
// Prevent overlapping requests and rapid re-notifications
// default fallbacks; will be overridden by server-provided `window.FACEATTEND_CONFIG` if present
let RECOGNITION_COOLDOWN_MS = 2000; // 2s cooldown after a detection
let processingFrame = false;          // true while a frame request is in-flight
let recognitionCooldownUntil = 0;     // timestamp until which we skip captures

// Sound effects
// Helper to read the configured API base from the page without creating a global
function getApiBase() {
    if (typeof window === 'undefined') return '';
    return (window.API_BASE || '').replace(/\/$/, '');
}

// Helper to read the static base (where static assets are hosted).
function getStaticBase() {
    if (typeof window === 'undefined') return '';
    return (window.STATIC_BASE || '').replace(/\/$/, '');
}

const loginSound = new Audio((getStaticBase() || '') + '/static/sounds/login.mp3');
const logoutSound = new Audio((getStaticBase() || '') + '/static/sounds/logout.mp3');
const attendanceSound = new Audio((getStaticBase() || '') + '/static/sounds/attendance.mp3');
// Per-student cooldown to avoid repeated audio
let SOUND_COOLDOWN_MS = 30 * 1000; // 30 seconds (default; overridden by server config)
const lastPlayed = {}; // map student_id -> timestamp
// Single-sound gate to avoid overlapping/looped playback
let soundPlaying = false;
const markSoundPlaying = (audio) => {
    soundPlaying = true;
    const clear = () => { soundPlaying = false; audio.removeEventListener('ended', clear); };
    audio.addEventListener('ended', clear);
};

// Speech synthesis for feedback
const speak = (text) => {
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
};

// Mute state (persisted)
let muted = localStorage.getItem('faceattend_muted') === '1';
// Audio enabled flag (persisted via settings)
let audioEnabled = true;
function setMuted(v) {
    muted = !!v;
    localStorage.setItem('faceattend_muted', muted ? '1' : '0');
    const label = document.getElementById('muteLabel');
    if (label) label.textContent = muted ? 'Muted' : 'Mute';
}
document.addEventListener('DOMContentLoaded', () => {
    // wire up mute button if present
    const mb = document.getElementById('muteButton');
    if (mb) {
        setMuted(muted);
        mb.addEventListener('click', () => setMuted(!muted));
    }
    // Bootstrap server-provided config if present
    try {
        if (window.FACEATTEND_CONFIG) {
            const c = window.FACEATTEND_CONFIG;
            if (typeof c.RECOGNITION_COOLDOWN_MS === 'number') RECOGNITION_COOLDOWN_MS = c.RECOGNITION_COOLDOWN_MS;
            if (typeof c.SOUND_COOLDOWN_MS === 'number') SOUND_COOLDOWN_MS = c.SOUND_COOLDOWN_MS;
            // other server-side tuning variables are consumed server-side; we keep client-focused ones
            console.debug('FACEATTEND_CONFIG loaded', c);
        }
    } catch (e) {
        console.warn('Failed to read FACEATTEND_CONFIG', e);
    }
});

// Initialize the camera feed
async function initCamera() {
    try {
        video = document.getElementById('videoElement');
        if (!video) {
            throw new Error('Video element not found');
        }

        stream = await navigator.mediaDevices.getUserMedia({ 
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            }
        });
        
        video.srcObject = stream;
        
        // Wait for video to be ready
        await new Promise((resolve, reject) => {
            video.onloadedmetadata = () => {
                video.play()
                    .then(resolve)
                    .catch(reject);
            };
            video.onerror = () => reject(new Error('Video element error'));
        });
        
        showStatus('Camera initialized successfully', 'success');
        startFaceRecognition();
    } catch (err) {
        console.error('Error accessing camera:', err);
        showStatus(`Error accessing camera: ${err.message}`, 'error');
    }
}

// Start continuous face recognition
function startFaceRecognition() {
    recognitionActive = true;
    processVideoFrame();
}

// Process each video frame
// Throttle frame uploads to ~4 FPS (250ms) to reduce load and improve responsiveness
async function processVideoFrame() {
    if (!recognitionActive || !video) {
        requestAnimationFrame(processVideoFrame);
        return;
    }
    // Skip capture while in cooldown (recent recognition) or if request already in-flight
    const nowTs = Date.now();
    if (nowTs < recognitionCooldownUntil) {
        setTimeout(processVideoFrame, 333);
        return;
    }
    if (processingFrame) {
        setTimeout(processVideoFrame, 333);
        return;
    }

    try {
        // Check if video is ready and has valid source
        if (!video.srcObject || !video.videoWidth || !video.videoHeight || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
            console.log('Video not ready:', {
                srcObject: !!video.srcObject,
                width: video.videoWidth,
                height: video.videoHeight,
                readyState: video.readyState
            });
            requestAnimationFrame(processVideoFrame);
            return;
        }
        
    // Create canvas to capture video frame
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        
        // Safety check before drawing
        if (video.videoWidth > 0 && video.videoHeight > 0) {
            ctx.drawImage(video, 0, 0);
            
            // Convert canvas to blob
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));

            // Prevent another request until this one finishes
            processingFrame = true;

            // Send frame to server (throttled)
            const response = await fetch(`${getApiBase()}/api/process-frame`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame: await blobToBase64(blob) })
            });

            const data = await response.json();

            // If server processed the frame successfully, handle recognized faces.
            // If server returned an error (success:false), treat it as "no faces detected"
            if (data && data.success) {
                handleRecognizedFaces(Array.isArray(data.recognized_faces) ? data.recognized_faces : []);
            } else {
                console.warn('Frame processing failed on server:', data && data.error);
                // Normalize client behavior by sending an empty faces array to the handler
                handleRecognizedFaces([]);
            }

            // allow next request
            processingFrame = false;
        } else {
            console.warn('Invalid video dimensions');
        }
        
    } catch (err) {
        console.error('Error processing frame:', err);
    }
    
    // Continue processing frames at ~4 FPS (250ms)
    setTimeout(processVideoFrame, 250);
}

// Convert blob to base64
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// Handle recognized faces
function handleRecognizedFaces(faces) {
    if (!Array.isArray(faces)) {
        console.error('Invalid faces data:', faces);
        return;
    }

    const now = Date.now();
    
    try {
        // If any faces detected, set short cooldown to avoid immediate repeated snapshots/sounds
        if (faces.length > 0) {
            recognitionCooldownUntil = Date.now() + RECOGNITION_COOLDOWN_MS;
        }

        // Update status for each recognized face
        faces.forEach(face => {
            if (!face || typeof face !== 'object') {
                console.error('Invalid face data:', face);
                return;
            }
            
            // Show welcome message instantly for each detected face
            const name = face.name || 'Unknown';
            let statusMessage = `Welcome ${name}!`;

            // If a thumbnail is provided, update last-seen list immediately
            if (face.photo_url) {
                updateLastSeen({ student_id: face.student_id, name: name, photo_url: face.photo_url, first: face.first_timestamp, last: face.last_timestamp, hours: face.work_hours });
            }
            
            // Always show the welcome message instantly
            showStatus(statusMessage, 'success');
            
                // Only play sound and update detailed info if global throttle allows
                if (now - lastRecognitionTime > 2000) {
                
                // Add timestamps and work hours if available
                if (face.attendance_marked) {
                    const workHours = face.work_hours || 0;
                    const firstTime = formatTime(face.first_timestamp);
                    const lastTime = formatTime(face.last_timestamp);

                    // Show the status immediately with details
                    statusMessage += `\nFirst detected: ${firstTime}`;
                    statusMessage += `\nLast detected: ${lastTime}`;
                    statusMessage += `\nWork hours: ${workHours.toFixed(2)} hours`;

                    showStatus(statusMessage, 'success');

                    // Play attendance sound (throttled by lastRecognitionTime)
                    // Per-student cooldown: only play attendance sound/speech if not recently played
                    const sid = face.student_id || name;
                    const last = lastPlayed[sid] || 0;

                    if (now - last > SOUND_COOLDOWN_MS) {
                        // Only play sound and speech if not muted and audio enabled in settings
                        if (!muted && audioEnabled) {
                            if (!soundPlaying && attendanceSound.readyState >= 2) {
                                try {
                                    attendanceSound.currentTime = 0;
                                    attendanceSound.loop = false;
                                    attendanceSound.play().catch(err => console.warn('Error playing sound:', err));
                                    markSoundPlaying(attendanceSound);
                                } catch (e) {
                                    console.warn('Error starting attendance sound:', e);
                                }
                            }

                            // Voice feedback (also throttled globally)
                            let speechMessage = `Hello ${name}, `;
                            if (firstTime === lastTime) {
                                speechMessage += `Welcome! Your first check-in time is ${firstTime}`;
                            } else {
                                speechMessage += `Your total work time is ${workHours.toFixed(1)} hours, from ${firstTime} to ${lastTime}`;
                            }
                            try { window.speechSynthesis.cancel(); } catch (e) {}
                            speak(speechMessage);
                            lastPlayed[sid] = now;
                            lastRecognitionTime = now;
                        } else {
                            // muted or audio disabled: update visual state but do not play sound/speech
                            lastRecognitionTime = now;
                        }
                    }
                } else {
                    showStatus(statusMessage, 'success');
                    // Per-student cooldown for login sound as well
                    const sid = face.student_id || name;
                    const last = lastPlayed[sid] || 0;
                    if (now - last > SOUND_COOLDOWN_MS) {
                        if (!muted && audioEnabled) {
                            if (!soundPlaying && loginSound.readyState >= 2) {
                                try {
                                    loginSound.currentTime = 0;
                                    loginSound.loop = false;
                                    loginSound.play().catch(err => console.warn('Error playing sound:', err));
                                    markSoundPlaying(loginSound);
                                } catch (e) {
                                    console.warn('Error starting login sound:', e);
                                }
                            }
                            lastPlayed[sid] = now;
                            lastRecognitionTime = now;
                        } else {
                            // muted or audio disabled: just set recognition time but don't play
                            lastRecognitionTime = now;
                        }
                    }
                }
                lastRecognitionTime = now;
            }
        });
        
        // Handle no face detected case — show visual only, do NOT play any sounds
        if (faces.length === 0) {
            // Show no face detected message after a brief delay
            if (now - lastRecognitionTime > 2000) {
                showStatus('No face detected', 'error');
                // Intentionally do not play logout or alarm sounds when no face is present
            }
        }
    } catch (err) {
        console.error('Error handling recognized faces:', err);
        showStatus('Error processing recognition results', 'error');
    }
}

// Update the Last Seen list in the sidebar
function updateLastSeen(entry) {
    try {
        const list = document.getElementById('lastSeenList');
        if (!list) return;

        // Create an item with thumbnail and text
        const li = document.createElement('li');
        li.className = 'd-flex align-items-center mb-2';

        const img = document.createElement('img');
        img.src = entry.photo_url;
        img.alt = entry.name;
        img.width = 48;
        img.height = 48;
        img.style.objectFit = 'cover';
        img.className = 'rounded me-2';

        const meta = document.createElement('div');
        // Show a small sound icon if we have played a sound for this student recently (tooltip shows time)
        let soundHtml = '';
        try {
            const sid = entry.student_id;
            const lt = lastPlayed && lastPlayed[sid];
            if (lt) {
                const d = new Date(lt);
                const title = `Last announcement: ${d.toLocaleTimeString()}`;
                soundHtml = `<span class="sound-icon" title="${title}" style="margin-left:6px">🔊</span>`;
            }
        } catch (e) {
            soundHtml = '';
        }

        meta.innerHTML = `<strong>${entry.name}</strong>${soundHtml}<br><small>${entry.first ? formatTime(entry.first) : ''} - ${entry.last ? formatTime(entry.last) : ''}</small>`;

        li.appendChild(img);
        li.appendChild(meta);

        // If the list contains the placeholder 'No one seen yet.', remove it
        if (list.children.length === 1 && list.children[0].textContent.trim().startsWith('No one seen yet')) {
            list.removeChild(list.children[0]);
        }

        // Remove any existing entry for this student_id to avoid duplicates
        try {
            const existing = Array.from(list.children).find(c => c.dataset && c.dataset.sid === String(entry.student_id));
            if (existing) {
                list.removeChild(existing);
            }
        } catch (e) {}

        // Attach student id for deduplication
        li.dataset.sid = String(entry.student_id);

        // Prepend and keep only last 3 entries
        list.insertBefore(li, list.firstChild);
        while (list.children.length > 3) list.removeChild(list.lastChild);
    } catch (e) {
        console.warn('Failed to update last seen list:', e);
    }
}

// Show status message
function showStatus(message, type) {
    let statusElement = document.getElementById('statusMessage');
    // If the status element is missing (template changed or not present),
    // create a minimal one so calls to showStatus don't throw.
    if (!statusElement) {
        console.warn('showStatus: statusMessage element not found - creating transient element.');
        try {
            statusElement = document.createElement('div');
            statusElement.id = 'statusMessage';
            // Keep styling minimal; templates can supply their own CSS class rules.
            statusElement.style.position = 'fixed';
            statusElement.style.bottom = '12px';
            statusElement.style.left = '12px';
            statusElement.style.padding = '8px 12px';
            statusElement.style.zIndex = 9999;
            statusElement.style.background = 'rgba(0,0,0,0.6)';
            statusElement.style.color = '#fff';
            statusElement.style.borderRadius = '6px';
            document.body.appendChild(statusElement);
        } catch (e) {
            // If DOM is not available for some reason, just log and abort silently
            console.warn('Unable to create statusMessage element:', e);
            return;
        }
    }

    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;
}

// Format timestamp to readable time
function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize the camera on pages that include the video element
    // (admin/dashboard and some other pages don't include the camera UI).
    if (document.getElementById('videoElement')) {
        initCamera();
    } else {
        console.debug('initCamera: videoElement not present on this page — skipping camera initialization.');
    }
    
    // Cleanup when page is closed
    window.onbeforeunload = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        recognitionActive = false;
    };
    // Wire settings button if present
    const sb = document.getElementById('settingsButton');
    if (sb) sb.addEventListener('click', showSettingsModal);
    // Load persisted local settings (if any)
    try { loadLocalSettings(); } catch (e) { console.warn('Failed loading local settings', e); }
});

// Settings modal helpers
function showSettingsModal() {
    // populate fields from current effective settings
    const rc = document.getElementById('setting_recognition_cooldown');
    const sc = document.getElementById('setting_sound_cooldown');
    const mf = document.getElementById('setting_min_consecutive');
    const ae = document.getElementById('setting_audio_enabled');
    if (rc) rc.value = RECOGNITION_COOLDOWN_MS;
    if (sc) sc.value = SOUND_COOLDOWN_MS;
    if (mf) mf.value = (window.FACEATTEND_CONFIG && window.FACEATTEND_CONFIG.MIN_CONSECUTIVE_FRAMES) || (typeof window.FACEATTEND_CONFIG === 'object' && window.FACEATTEND_CONFIG.MIN_CONSECUTIVE_FRAMES) || 3;
    if (ae) ae.checked = (typeof audioEnabled === 'boolean') ? audioEnabled : true;
    // show bootstrap modal
    try {
        const modalEl = document.getElementById('settingsModal');
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } catch (e) {
        // fallback: show inline
        const modalEl = document.getElementById('settingsModal');
        if (modalEl) modalEl.style.display = 'block';
    }
}

function saveSettingsFromModal() {
    const rc = document.getElementById('setting_recognition_cooldown');
    const sc = document.getElementById('setting_sound_cooldown');
    const mf = document.getElementById('setting_min_consecutive');
    const settings = {};
    if (rc) settings.RECOGNITION_COOLDOWN_MS = parseInt(rc.value) || RECOGNITION_COOLDOWN_MS;
    if (sc) settings.SOUND_COOLDOWN_MS = parseInt(sc.value) || SOUND_COOLDOWN_MS;
    if (mf) settings.MIN_CONSECUTIVE_FRAMES = parseInt(mf.value) || (window.FACEATTEND_CONFIG && window.FACEATTEND_CONFIG.MIN_CONSECUTIVE_FRAMES) || 3;
    const ae = document.getElementById('setting_audio_enabled');
    if (ae) settings.AUDIO_ENABLED = !!ae.checked;
    // persist
    localStorage.setItem('faceattend_settings', JSON.stringify(settings));
    applyLocalSettings(settings);
    // hide modal
    try { const m = bootstrap.Modal.getInstance(document.getElementById('settingsModal')); if (m) m.hide(); } catch(e){}
    // show confirmation toast
    try { showSettingsSavedToast('Settings saved'); } catch (e) { console.warn('Toast show failed', e); }
}

function showSettingsSavedToast(message) {
    try {
        const toastEl = document.getElementById('settingsToast');
        if (!toastEl) return;
        const body = toastEl.querySelector('.toast-body');
        if (body) body.textContent = message;
        const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 2500 });
        toast.show();
    } catch (e) {
        console.warn('Could not show settings toast', e);
    }
}

function loadLocalSettings() {
    const raw = localStorage.getItem('faceattend_settings');
    if (!raw) return;
    try {
        const s = JSON.parse(raw);
        applyLocalSettings(s);
    } catch (e) { console.warn('Invalid local settings', e); }
}

function applyLocalSettings(s) {
    if (!s) return;
    if (typeof s.RECOGNITION_COOLDOWN_MS === 'number') RECOGNITION_COOLDOWN_MS = s.RECOGNITION_COOLDOWN_MS;
    if (typeof s.SOUND_COOLDOWN_MS === 'number') SOUND_COOLDOWN_MS = s.SOUND_COOLDOWN_MS;
    // also apply MIN_CONSECUTIVE_FRAMES locally for client hinting; server still enforces canonical value
    if (typeof s.MIN_CONSECUTIVE_FRAMES === 'number') {
        // store locally for UI hints
        window.FACEATTEND_LOCAL = window.FACEATTEND_LOCAL || {};
        window.FACEATTEND_LOCAL.MIN_CONSECUTIVE_FRAMES = s.MIN_CONSECUTIVE_FRAMES;
    }
    if (typeof s.AUDIO_ENABLED === 'boolean') {
        audioEnabled = s.AUDIO_ENABLED;
    }
}