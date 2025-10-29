// Global variables
let video = null;
let stream = null;
let recognitionActive = false;
let lastRecognitionTime = Date.now();

// Sound effects
const loginSound = new Audio('/static/sounds/login.mp3');
const logoutSound = new Audio('/static/sounds/logout.mp3');
const attendanceSound = new Audio('/static/sounds/attendance.mp3');

// Speech synthesis for feedback
const speak = (text) => {
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
};

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
async function processVideoFrame() {
    if (!recognitionActive || !video) {
        requestAnimationFrame(processVideoFrame);
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
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg');
            });
            
            // Send frame to server
            const response = await fetch('/api/process-frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    frame: await blobToBase64(blob)
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                handleRecognizedFaces(data.recognized_faces);
            }
        } else {
            console.warn('Invalid video dimensions');
        }
        
    } catch (err) {
        console.error('Error processing frame:', err);
    }
    
    // Continue processing frames
    requestAnimationFrame(processVideoFrame);
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
        // Update status for each recognized face
        faces.forEach(face => {
            if (!face || typeof face !== 'object') {
                console.error('Invalid face data:', face);
                return;
            }
            
            // Show welcome message instantly for each detected face
            const name = face.name || 'Unknown';
            let statusMessage = `Welcome ${name}!`;
            
            // Always show the welcome message instantly
            showStatus(statusMessage, 'success');
            
            // Only play sound and update detailed info if enough time has passed
            if (now - lastRecognitionTime > 2000) {
                
                // Add timestamps and work hours if available
                if (face.attendance_marked) {
                    const workHours = face.work_hours || 0;
                    const firstTime = formatTime(face.first_timestamp);
                    const lastTime = formatTime(face.last_timestamp);
                    
                    statusMessage += `\nFirst detected: ${firstTime}`;
                    statusMessage += `\nLast detected: ${lastTime}`;
                    statusMessage += `\nWork hours: ${workHours.toFixed(2)} hours`;
                    
                    showStatus(statusMessage, 'success');
                    
                    // Play attendance sound
                    if (attendanceSound.readyState >= 2) {
                        attendanceSound.play().catch(err => console.warn('Error playing sound:', err));
                    }
                    
                    // Provide voice feedback
                    let speechMessage = `Hello ${name}, `;
                    if (firstTime === lastTime) {
                        speechMessage += `Welcome! Your first check-in time is ${firstTime}`;
                    } else {
                        speechMessage += `Your total work time is ${workHours.toFixed(1)} hours, from ${firstTime} to ${lastTime}`;
                    }
                    speak(speechMessage);
                } else {
                    showStatus(statusMessage, 'success');
                    if (loginSound.readyState >= 2) {
                        loginSound.play().catch(err => console.warn('Error playing sound:', err));
                    }
                }
                lastRecognitionTime = now;
            }
        });
        
        // Handle no face detected case
        if (faces.length === 0) {
            // Show no face detected message after a brief delay
            if (now - lastRecognitionTime > 2000) {
                showStatus('No face detected', 'error');
                if (logoutSound.readyState >= 2) { // Check if sound is loaded
                    logoutSound.play().catch(err => console.warn('Error playing sound:', err));
                }
            }
        }
    } catch (err) {
        console.error('Error handling recognized faces:', err);
        showStatus('Error processing recognition results', 'error');
    }
}

// Show status message
function showStatus(message, type) {
    const statusElement = document.getElementById('statusMessage');
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
    initCamera();
    
    // Cleanup when page is closed
    window.onbeforeunload = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        recognitionActive = false;
    };
});