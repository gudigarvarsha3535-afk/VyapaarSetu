import { API } from './api.js';

export class ChatWidget {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chat-widget-container';
        this.onEntityUpdated = options.onEntityUpdated || (() => {});
        this.isOpen = false;
        this.attachedImageBase64 = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;

        this.init();
    }

    init() {
        this.render();
        this.bindEvents();
    }

    render() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        container.innerHTML = `
            <!-- Collapsed Floating Button -->
            <button id="widget-toggle-btn" class="fixed bottom-6 right-6 bg-emerald-600 hover:bg-emerald-700 text-white rounded-full p-4 shadow-2xl flex items-center gap-3 transition-transform duration-200 hover:scale-105 z-50">
                <span class="relative flex h-3.5 w-3.5">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-300 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-white"></span>
                </span>
                <span class="font-kannada font-semibold text-base tracking-wide flex items-center gap-1.5">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
                    ವಾಣಿ ಸಹಾಯಕ (Chat)
                </span>
            </button>

            <!-- Expanded Chatbot Panel -->
            <div id="widget-panel" class="hidden fixed bottom-4 right-4 w-96 max-w-[calc(100vw-2rem)] h-[540px] max-h-[85vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden z-50 transition-all duration-300">
                
                <!-- Header -->
                <div class="bg-gradient-to-r from-emerald-600 to-teal-700 text-white p-3.5 px-4 flex items-center justify-between shadow-md">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold text-sm">
                            ವಾ
                        </div>
                        <div>
                            <h3 class="font-kannada font-bold text-sm leading-tight">ವಾಣಿ - ಅಂಗಡಿ ಸಹಾಯಕ</h3>
                            <p class="text-xs text-emerald-100 flex items-center gap-1">
                                <span class="w-2 h-2 rounded-full bg-emerald-300 inline-block animate-pulse"></span>
                                SraVaani 1.0 + AI Ready
                            </p>
                        </div>
                    </div>
                    <div class="flex items-center gap-1">
                        <button id="widget-minimize-btn" class="text-white/80 hover:text-white p-1 rounded hover:bg-white/10" title="Minimize">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </button>
                    </div>
                </div>

                <!-- Messages Container -->
                <div id="chat-messages" class="flex-1 overflow-y-auto p-3.5 space-y-3 bg-slate-50 text-sm">
                    <!-- Welcome Message -->
                    <div class="flex items-start gap-2">
                        <div class="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0">
                            ವ
                        </div>
                        <div class="chat-bubble-bot">
                            <p class="font-kannada font-medium text-slate-800">ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಅಂಗಡಿಯ ಸಹಾಯಕ ವಾಣಿ.</p>
                            <p class="font-kannada text-xs text-slate-600 mt-1">ಬೆಲೆ ಬದಲಾವಣೆ, ಸ್ಟಾಕ್ ಅಪ್ಡೇಟ್, ಆರ್ಡರ್ ಸ್ಟೇಟಸ್ ಅಥವಾ ಮಾರಾಟ ವರದಿ ಕೇಳಲು ಮೈಕ್ ಒತ್ತಿ ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.</p>
                        </div>
                    </div>
                </div>

                <!-- Quick Prompt Chips -->
                <div class="p-2 bg-white border-t border-slate-100 flex gap-1.5 overflow-x-auto whitespace-nowrap scrollbar-none text-xs">
                    <button class="quick-chip bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-full px-2.5 py-1 font-kannada font-medium shrink-0 transition" data-text="Bellulli rate 80 maadi">
                        🧅 Bellulli rate ₹80 maadi
                    </button>
                    <button class="quick-chip bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-full px-2.5 py-1 font-kannada font-medium shrink-0 transition" data-text="Akki stock mugidide">
                        🌾 Akki stock mugidide
                    </button>
                    <button class="quick-chip bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200 rounded-full px-2.5 py-1 font-kannada font-medium shrink-0 transition" data-text="Ivattina vyapara eshtu?">
                        📊 Ivattina vyapara eshtu?
                    </button>
                    <button class="quick-chip bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 rounded-full px-2.5 py-1 font-kannada font-medium shrink-0 transition" data-text="Mysore Pak 500g 220 rs ge add maadi">
                        🍬 Mysore Pak ₹220 add maadi
                    </button>
                </div>

                <!-- Image Attachment Preview (if any) -->
                <div id="image-preview-bar" class="hidden px-3 py-1.5 bg-slate-100 border-t border-slate-200 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <img id="image-preview-thumb" src="" class="w-8 h-8 rounded object-cover border border-slate-300" />
                        <span class="text-xs text-slate-600 font-medium truncate max-w-[180px]">Product photo attached</span>
                    </div>
                    <button id="remove-image-btn" class="text-slate-400 hover:text-red-500 p-1">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>

                <!-- Input Controls Bar -->
                <div class="p-2.5 bg-white border-t border-slate-200 flex items-center gap-2">
                    
                    <!-- Hidden File Input for Camera / Gallery -->
                    <input type="file" id="camera-file-input" accept="image/*" class="hidden" capture="environment" />
                    <input type="file" id="gallery-file-input" accept="image/*" class="hidden" />

                    <!-- Camera & Gallery dropdown/buttons -->
                    <div class="flex items-center gap-1">
                        <button id="camera-btn" class="p-2 text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition" title="Take photo with camera">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        </button>
                        <button id="gallery-btn" class="p-2 text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition" title="Pick from gallery">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                        </button>
                    </div>

                    <!-- Hold-to-Talk Mic Button -->
                    <button id="mic-btn" class="p-2.5 bg-emerald-100 hover:bg-emerald-200 text-emerald-700 rounded-full transition flex items-center justify-center shrink-0" title="Hold or Click to Speak Kannada">
                        <svg id="mic-icon" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
                    </button>

                    <!-- Text Input -->
                    <input type="text" id="chat-input" class="flex-1 bg-slate-100 focus:bg-white text-slate-800 text-sm px-3 py-2 rounded-xl border border-transparent focus:border-emerald-500 focus:outline-none font-kannada transition" placeholder="ಕನ್ನಡ / Kanglish ನಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ..." />

                    <!-- Send Button -->
                    <button id="send-btn" class="p-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition shrink-0">
                        <svg class="w-4 h-4 transform rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                    </button>
                </div>
            </div>
        `;
    }

    bindEvents() {
        const toggleBtn = document.getElementById('widget-toggle-btn');
        const panel = document.getElementById('widget-panel');
        const minBtn = document.getElementById('widget-minimize-btn');
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        const cameraBtn = document.getElementById('camera-btn');
        const galleryBtn = document.getElementById('gallery-btn');
        const cameraInput = document.getElementById('camera-file-input');
        const galleryInput = document.getElementById('gallery-file-input');
        const removeImageBtn = document.getElementById('remove-image-btn');
        const micBtn = document.getElementById('mic-btn');

        // Toggle Expand / Collapse with pb-80 dashboard clearance
        toggleBtn?.addEventListener('click', () => this.setOpen(true));
        minBtn?.addEventListener('click', () => this.setOpen(false));

        // Text Send
        sendBtn?.addEventListener('click', () => this.handleSendMessage());
        chatInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.handleSendMessage();
            }
        });

        // Quick prompt chips
        document.querySelectorAll('.quick-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const text = chip.getAttribute('data-text');
                this.handleSendMessage(text);
            });
        });

        // Camera & Gallery Uploads
        cameraBtn?.addEventListener('click', () => cameraInput?.click());
        galleryBtn?.addEventListener('click', () => galleryInput?.click());

        cameraInput?.addEventListener('change', (e) => this.handleImagePicked(e));
        galleryInput?.addEventListener('change', (e) => this.handleImagePicked(e));
        removeImageBtn?.addEventListener('click', () => this.clearAttachedImage());

        // Voice Recording (Click / Hold-to-Talk)
        micBtn?.addEventListener('click', () => this.toggleVoiceRecording());
    }

    setOpen(open) {
        this.isOpen = open;
        const toggleBtn = document.getElementById('widget-toggle-btn');
        const panel = document.getElementById('widget-panel');
        const dashboardMain = document.getElementById('seller-dashboard-content');

        if (open) {
            panel?.classList.remove('hidden');
            toggleBtn?.classList.add('hidden');
            // Add pb-80 clearance padding to main dashboard content so bottom cards are never covered
            if (dashboardMain) {
                dashboardMain.classList.add('pb-80');
            }
            document.getElementById('chat-input')?.focus();
        } else {
            panel?.classList.add('hidden');
            toggleBtn?.classList.remove('hidden');
            // Remove pb-80 clearance padding
            if (dashboardMain) {
                dashboardMain.classList.remove('pb-80');
            }
        }
    }

    handleImagePicked(e) {
        const file = e.target.files?.[0];
        if (!file) return;

        // Ensure max 5MB
        if (file.size > 5 * 1024 * 1024) {
            alert("Please select an image smaller than 5 MB.");
            return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            this.attachedImageBase64 = event.target.result;
            const previewBar = document.getElementById('image-preview-bar');
            const previewThumb = document.getElementById('image-preview-thumb');
            if (previewThumb && previewBar) {
                previewThumb.src = this.attachedImageBase64;
                previewBar.classList.remove('hidden');
            }
        };
        reader.readAsDataURL(file);
    }

    clearAttachedImage() {
        this.attachedImageBase64 = null;
        document.getElementById('image-preview-bar')?.classList.add('hidden');
        const camIn = document.getElementById('camera-file-input');
        const galIn = document.getElementById('gallery-file-input');
        if (camIn) camIn.value = '';
        if (galIn) galIn.value = '';
    }

    async toggleVoiceRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioChunks = [];
            
            // Prefer webm/opus or wav
            let mimeType = 'audio/webm';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/ogg';
            }

            this.mediaRecorder = new MediaRecorder(stream, { mimeType });
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: mimeType });
                stream.getTracks().forEach(track => track.stop());
                await this.handleAudioBlob(audioBlob);
            };

            this.mediaRecorder.start();
            this.isRecording = true;

            const micBtn = document.getElementById('mic-btn');
            micBtn?.classList.add('recording-pulse');
            micBtn?.classList.remove('bg-emerald-100', 'text-emerald-700');
            micBtn?.classList.add('text-white');
            micBtn.setAttribute('title', 'Recording... Click to send');

        } catch (err) {
            console.error("Mic access denied or unavailable:", err);
            this.appendMessage("bot", "ಮೈಕ್ರೋಫೋನ್ ಅನುಮತಿ ಸಿಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಬ್ರೌಸರ್ ಸೆಟ್ಟಿಂಗ್ಸ್‌ನಲ್ಲಿ ಮೈಕ್ ಆನ್ ಮಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.");
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;

            const micBtn = document.getElementById('mic-btn');
            micBtn?.classList.remove('recording-pulse', 'text-white');
            micBtn?.classList.add('bg-emerald-100', 'text-emerald-700');
            micBtn.setAttribute('title', 'Click to Speak Kannada');
        }
    }

    async handleAudioBlob(blob) {
        this.appendMessage("user", "🎤 [ಧ್ವನಿ ಸಂದೇಶ ರೆಕಾರ್ಡ್ ಮಾಡಲಾಗಿದೆ...]");
        this.showTypingIndicator();

        const reader = new FileReader();
        reader.onloadend = async () => {
            const base64Audio = reader.result;
            try {
                const response = await API.sendBotMessage({
                    inputType: "voice",
                    audioBase64: base64Audio,
                    imageBase64: this.attachedImageBase64,
                    activeTab: "HOME"
                });
                this.removeTypingIndicator();
                this.handleBotResponse(response);
            } catch (err) {
                this.removeTypingIndicator();
                this.appendMessage("bot", "ಕ್ಷಮಿಸಿ, ಧ್ವನಿ ಸಂಸ್ಕರಣೆಯಲ್ಲಿ ದೋಷ ಉಂಟಾಗಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ.");
            }
        };
        reader.readAsDataURL(blob);
    }

    async handleSendMessage(customText = null) {
        const input = document.getElementById('chat-input');
        const text = customText !== null ? customText : (input ? input.value.trim() : '');

        if (!text && !this.attachedImageBase64) return;

        // Display user message in UI
        let displayMsg = text;
        if (this.attachedImageBase64 && !text) {
            displayMsg = "📷 [Product photo attached]";
        }
        this.appendMessage("user", displayMsg, this.attachedImageBase64);

        if (input) input.value = '';
        const imgToSend = this.attachedImageBase64;
        this.clearAttachedImage();

        this.showTypingIndicator();

        try {
            const res = await API.sendBotMessage({
                inputType: "text",
                text: text,
                imageBase64: imgToSend,
                activeTab: "HOME"
            });
            this.removeTypingIndicator();
            this.handleBotResponse(res);
        } catch (err) {
            this.removeTypingIndicator();
            this.appendMessage("bot", "ಕ್ಷಮಿಸಿ, ಸರ್ವರ್ ಜೊತೆ ಸಂಪರ್ಕ ಸಾಧ್ಯವಾಗುತ್ತಿಲ್ಲ.");
        }
    }

    handleBotResponse(response) {
        if (!response) return;

        // If transcribed text is available from SraVaani, we can show what was heard
        if (response.transcribedText) {
            // Note in chat
            const msgEl = this.appendMessage("bot", `🗣️ ಕೇಳಿಸಿದ್ದು: "${response.transcribedText}"\n\n${response.replyKn}`);
        } else {
            this.appendMessage("bot", response.replyKn);
        }

        // If mutating action succeeded, trigger dashboard refresh and flash highlight!
        if (response.refreshRequired && response.updatedEntity) {
            const entityId = response.updatedEntity.id || (response.updatedEntity.orderId ? response.updatedEntity.orderId : null);
            this.onEntityUpdated(response.intent, response.updatedEntity, entityId);
        }
    }

    appendMessage(sender, text, imageUrl = null) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return null;

        const row = document.createElement('div');
        row.className = sender === 'user' ? 'flex justify-end' : 'flex items-start gap-2';

        let innerHtml = '';
        if (sender === 'bot') {
            innerHtml += `
                <div class="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0">
                    ವ
                </div>
            `;
        }

        const bubbleClass = sender === 'user' ? 'chat-bubble-user font-kannada' : 'chat-bubble-bot font-kannada';
        let contentHtml = `<p class="whitespace-pre-line">${this.escapeHtml(text)}</p>`;

        if (imageUrl) {
            contentHtml = `<img src="${imageUrl}" class="w-24 h-24 object-cover rounded-lg mb-1 border border-white/20" />` + contentHtml;
        }

        innerHtml += `<div class="${bubbleClass}">${contentHtml}</div>`;
        row.innerHTML = innerHtml;

        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return row;
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const indicator = document.createElement('div');
        indicator.id = 'bot-typing-indicator';
        indicator.className = 'flex items-start gap-2';
        indicator.innerHTML = `
            <div class="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0">
                ವ
            </div>
            <div class="chat-bubble-bot flex items-center gap-1.5 py-2 px-3">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"></span>
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.2s]"></span>
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.4s]"></span>
            </div>
        `;
        chatMessages.appendChild(indicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    removeTypingIndicator() {
        document.getElementById('bot-typing-indicator')?.remove();
    }

    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
}
