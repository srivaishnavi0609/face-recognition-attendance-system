// face_recognize.js

document.addEventListener('DOMContentLoaded', () => {
    const webcamFeed = document.getElementById('webcam-feed');
    const openCamBtn = document.getElementById('open-cam-btn');
    const captureBtn = document.getElementById('capture-btn');
    const scanStatus = document.getElementById('scan-status');
    const registrationForm = document.getElementById('register-student-form');
    const hasFaceInput = document.getElementById('has_face_encoding');
    
    let streamActive = false;

    // --- Face Registration Stream Controls ---
    if (openCamBtn) {
        openCamBtn.addEventListener('click', () => {
            if (!streamActive) {
                // Point the image tag to our streaming endpoint
                webcamFeed.src = "/video_feed?mode=registration";
                webcamFeed.style.display = "block";
                openCamBtn.innerHTML = '<i class="fas fa-camera-retro"></i> Reset Camera';
                if (captureBtn) captureBtn.disabled = false;
                streamActive = true;
                showToast("Webcam feed opened successfully", "info");
            } else {
                // Reset feed
                webcamFeed.src = "";
                webcamFeed.style.display = "none";
                openCamBtn.innerHTML = '<i class="fas fa-video"></i> Start Webcam';
                if (captureBtn) captureBtn.disabled = true;
                streamActive = false;
            }
        });
    }

    // Capture Face for registration
    if (captureBtn) {
        captureBtn.addEventListener('click', () => {
            const studentId = document.getElementById('student_id').value;
            if (!studentId) {
                showToast("Please enter Student ID before capturing face", "error");
                return;
            }

            captureBtn.disabled = true;
            captureBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            
            // Call the capture API
            fetch('/api/capture_face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ student_id: studentId })
            })
            .then(res => res.json())
            .then(data => {
                captureBtn.disabled = false;
                captureBtn.innerHTML = '<i class="fas fa-snapchat"></i> Capture Face';
                
                if (data.success) {
                    showToast("Face encoding captured and validated!", "success");
                    hasFaceInput.value = "true";
                    
                    // Show preview of captured image
                    let previewImg = document.getElementById('captured-preview');
                    if (!previewImg) {
                        previewImg = document.createElement('img');
                        previewImg.id = 'captured-preview';
                        previewImg.className = 'mt-3 img-thumbnail';
                        previewImg.style.maxHeight = '150px';
                        document.getElementById('capture-section').appendChild(previewImg);
                    }
                    // Prevent caching by appending timestamp
                    previewImg.src = data.image_path + '?t=' + new Date().getTime();
                    
                    if (scanStatus) {
                        scanStatus.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> Face Enrolled Successfully</span>';
                    }
                } else {
                    showToast(data.message, "error");
                    if (scanStatus) {
                        scanStatus.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${data.message}</span>`;
                    }
                }
            })
            .catch(err => {
                captureBtn.disabled = false;
                captureBtn.innerHTML = '<i class="fas fa-snapchat"></i> Capture Face';
                console.error(err);
                showToast("Server communication error", "error");
            });
        });
    }

    // --- Live Attendance Scanning Polling ---
    const attendanceLogsTable = document.getElementById('live-attendance-logs');
    if (attendanceLogsTable) {
        let lastSeenId = 0;
        let processedLogs = new Set();

        const pollRecentScans = () => {
            fetch('/api/recent_scans')
                .then(res => res.json())
                .then(data => {
                    if (data && data.length > 0) {
                        // Iterate reversed so newer scans appear on top
                        data.forEach(scan => {
                            const logKey = `${scan.student_id}_${scan.time}`;
                            if (!processedLogs.has(logKey)) {
                                processedLogs.add(logKey);
                                
                                // Welcome voice / speech synthesis (optional, but incredibly premium!)
                                speakWelcome(scan.name);

                                // Add toast alert
                                showToast(`Attendance marked for ${scan.name} (${scan.class_name})`, "success");

                                // Add row to active table
                                const row = document.createElement('tr');
                                // Highlight new entry briefly
                                row.style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
                                setTimeout(() => {
                                    row.style.backgroundColor = '';
                                }, 3000);

                                const badgeClass = scan.status.toLowerCase() === 'present' ? 'badge-present' : 'badge-late';
                                row.innerHTML = `
                                    <td><strong>${scan.student_id}</strong></td>
                                    <td>${scan.name}</td>
                                    <td>${scan.class_name} - ${scan.section}</td>
                                    <td>${scan.time}</td>
                                    <td><span class="badge ${badgeClass}">${scan.status}</span></td>
                                    <td>${scan.recognition_confidence}%</td>
                                `;
                                
                                // Insert at top
                                if (attendanceLogsTable.firstChild) {
                                    attendanceLogsTable.insertBefore(row, attendanceLogsTable.firstChild);
                                } else {
                                    attendanceLogsTable.appendChild(row);
                                }

                                // Remove bottom items if list is long (limit 8 rows on screen)
                                while (attendanceLogsTable.children.length > 8) {
                                    attendanceLogsTable.removeChild(attendanceLogsTable.lastChild);
                                }
                            }
                        });
                    }
                })
                .catch(err => console.error("Error polling scans:", err));
        };

        // Poll every 1.5 seconds
        const pollInterval = setInterval(pollRecentScans, 1500);

        // Clear interval on unload
        window.addEventListener('beforeunload', () => {
            clearInterval(pollInterval);
        });
    }

    // Voice assistance
    function speakWelcome(name) {
        if ('speechSynthesis' in window) {
            const sentence = `Welcome, ${name}. Your attendance is marked.`;
            const utterance = new SpeechSynthesisUtterance(sentence);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            // Speak!
            window.speechSynthesis.speak(utterance);
        }
    }
});
