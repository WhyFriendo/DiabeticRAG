document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const uploadStatus = document.getElementById('upload-status');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const chatStatusText = document.getElementById('chat-status-text');
    const dot = document.querySelector('.dot');

    let isDataReady = false;

    // --- Upload Logic ---
    browseBtn.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileUpload(e.target.files[0]);
        }
    });

    async function handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            showUploadStatus('Please upload a valid CSV file.', 'error');
            return;
        }

        showUploadStatus('Uploading and processing your data... This may take a minute.', '');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (response.ok) {
                showUploadStatus(data.message, 'success');
                enableChat();
            } else {
                showUploadStatus(data.detail || 'Error uploading file.', 'error');
            }
        } catch (err) {
            showUploadStatus('Network error while uploading.', 'error');
        }
    }

    function showUploadStatus(msg, type) {
        uploadStatus.textContent = msg;
        uploadStatus.className = 'status-message ' + type;
    }

    function enableChat() {
        isDataReady = true;
        chatInput.disabled = false;
        sendBtn.disabled = false;
        dot.classList.add('ready');
        chatStatusText.textContent = 'Ready to chat';
        
        appendSystemMessage("Data loaded successfully! Ask me about your glucose trends, pump settings, or to summarize recent patterns.");
    }

    // --- Chat Logic ---
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const query = chatInput.value.trim();
        if (!query || !isDataReady) return;

        // Add user message
        appendUserMessage(query);
        chatInput.value = '';
        
        // Show typing indicator
        const typingId = appendTypingIndicator();
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await response.json();

            removeElement(typingId);

            if (response.ok) {
                appendSystemMessage(data.answer);
            } else {
                appendSystemMessage("Error: " + (data.detail || "Could not process request."));
            }
        } catch (err) {
            removeElement(typingId);
            appendSystemMessage("Network error. Please try again.");
        }
    }

    // --- UI Helpers ---
    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user';
        msgDiv.innerHTML = `
            <div class="avatar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            </div>
            <div class="bubble">${escapeHtml(text)}</div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendSystemMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message system';
        msgDiv.innerHTML = `
            <div class="avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"></path><path d="M12 8v14"></path><path d="M5 15l7-7 7 7"></path></svg>
            </div>
            <div class="bubble">${formatMessageText(text)}</div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.id = id;
        msgDiv.className = 'message system';
        msgDiv.innerHTML = `
            <div class="avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"></path><path d="M12 8v14"></path><path d="M5 15l7-7 7 7"></path></svg>
            </div>
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        return id;
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    function formatMessageText(text) {
        // Very simple markdown-like formatting (bold and newlines)
        return escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }
});
