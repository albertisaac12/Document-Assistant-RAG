document.addEventListener("DOMContentLoaded", function () {
    // 1. Auto-scroll chat window to bottom
    const chatWindow = document.getElementById('chatWindow');
    if (chatWindow) {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // 2. Auto-resize textarea
    const messageInput = document.getElementById('messageInput');
    const chatForm = document.getElementById('chatForm');

    if (messageInput) {
        messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
            if (this.value === '') {
                this.style.height = '';
            }
        });

        // Submit on enter (Shift+Enter for new line)
        messageInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (this.value.trim() !== '') {
                    // Trigger form submit event
                    if (chatForm) {
                        chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                    }
                }
            }
        });
    }

    // 3. Highlight selected document cards
    const checkboxes = document.querySelectorAll('input[name="document_ids"]');
    checkboxes.forEach(cb => {
        toggleCardHighlight(cb);
        cb.addEventListener('change', function () {
            toggleCardHighlight(this);
        });
    });

    function toggleCardHighlight(checkbox) {
        const card = checkbox.closest('.doc-card');
        if (card) {
            if (checkbox.checked) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        }
    }

    // 4. Handle Streaming Chat Submission
    if (chatForm) {
        chatForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const submitBtn = document.getElementById('sendBtn');
            const contentInfo = messageInput.value.trim();

            if (!contentInfo) return;

            // Disable input while processing
            submitBtn.disabled = true;
            messageInput.disabled = true;

            // 1. Instantly append User Message to DOM
            appendUserMessage(contentInfo);

            // Reset input
            messageInput.value = '';
            messageInput.style.height = '';

            // 2. Prepare for Bot response
            const botBubbleId = 'bot-msg-' + Date.now();
            appendEmptyBotMessage(botBubbleId);
            const botBubbleText = document.getElementById(`${botBubbleId}-text`);
            const botBubbleSources = document.getElementById(`${botBubbleId}-sources`);

            // 3. fetch the stream
            try {
                const streamUrl = chatForm.getAttribute('data-stream-url');
                const formData = new FormData(chatForm);
                formData.set('content', contentInfo); // enforce the trimmed content

                const response = await fetch(streamUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Accept': 'text/event-stream',
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let done = false;
                let buffer = "";

                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    done = readerDone;

                    if (value) {
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n\n');

                        // Keep the last part in buffer if it doesn't end with \n\n
                        buffer = lines.pop();

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const dataStr = line.substring(6);
                                try {
                                    const data = JSON.parse(dataStr);

                                    if (data.error) {
                                        botBubbleText.innerHTML = `<span class="text-danger">Error: ${data.error}</span>`;
                                    } else if (data.chunk) {
                                        // Append chunk, replace newlines with <br>
                                        const cleanChunk = data.chunk.replace(/\n/g, '<br>');
                                        botBubbleText.innerHTML += cleanChunk;
                                        scrollToBottom();
                                    } else if (data.sources && data.done) {
                                        if (data.sources.length > 0) {
                                            botBubbleSources.innerHTML = `Sources: ${data.sources.join(', ')}`;
                                            botBubbleSources.parentElement.classList.remove('d-none');
                                        }
                                    }
                                } catch (e) {
                                    console.error("Error parsing stream JSON", e, dataStr);
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                console.error("Stream failed:", error);
                botBubbleText.innerHTML = `<span class="text-danger">Connection failed. Please refresh.</span>`;
            } finally {
                submitBtn.disabled = false;
                messageInput.disabled = false;
                messageInput.focus();
                scrollToBottom();
            }
        });
    }

    function appendUserMessage(text) {
        if (!chatWindow) return;

        // Remove empty state message if exists
        const emptyState = chatWindow.querySelector('.text-center.text-muted');
        if (emptyState) emptyState.remove();

        const div = document.createElement('div');
        div.className = 'message-bubble message-user shadow-sm';
        div.textContent = text;
        chatWindow.appendChild(div);
        scrollToBottom();
    }

    function appendEmptyBotMessage(id) {
        if (!chatWindow) return;

        const div = document.createElement('div');
        div.className = 'message-bubble message-bot shadow-sm';
        div.innerHTML = `
            <div id="${id}-text">
                <span class="spinner-grow spinner-grow-sm text-secondary" role="status" aria-hidden="true"></span>
            </div>
            <div class="mt-2 pt-2 border-top small text-muted fst-italic d-none">
                <span id="${id}-sources"></span>
            </div>
        `;
        chatWindow.appendChild(div);
        scrollToBottom();
    }

    function scrollToBottom() {
        if (chatWindow) {
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
    }
});
