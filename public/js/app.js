/* ============================================
   TickingSound - Web Audio API
   ============================================ */
class TickingSound {
    constructor() {
        this.audioCtx = null;
    }

    init() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    tick() {
        if (!this.audioCtx) return;
        const now = this.audioCtx.currentTime;

        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.frequency.value = 600 + Math.random() * 600;
        osc.type = 'square';

        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);

        osc.start(now);
        osc.stop(now + 0.06);
    }

    victory() {
        if (!this.audioCtx) return;
        const notes = [523, 659, 784, 1047];
        notes.forEach((freq, i) => {
            setTimeout(() => this._playNote(freq, 0.25), i * 140);
        });
    }

    _playNote(freq, duration) {
        const now = this.audioCtx.currentTime;
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.frequency.value = freq;
        osc.type = 'sine';

        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

        osc.start(now);
        osc.stop(now + duration);
    }
}

/* ============================================
   VoiceInput - Web Speech API
   ============================================ */
class VoiceInput {
    constructor(onResult, onStateChange) {
        this.onResult = onResult;
        this.onStateChange = onStateChange;
        this.isRecording = false;
        this.processing = false;
        this.cooldownUntil = 0;
        this.recognition = null;
        this.isSupported = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
    }

    toggle() {
        if (this.isRecording) {
            this.stop();
        } else {
            this.start();
        }
    }

    start() {
        if (!this.isSupported || this.isRecording || this.processing) return;
        if (Date.now() < this.cooldownUntil) return;

        this.abortPrevious();

        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SR();
        this.recognition.lang = 'es-ES';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;

        let resultFired = false;

        this.recognition.onresult = (event) => {
            if (resultFired) return;
            const result = event.results[0];
            if (!result || !result.isFinal) return;
            resultFired = true;
            this.processing = true;
            const transcript = result[0].transcript.trim();
            if (transcript) {
                this.cooldownUntil = Date.now() + 300;
                this.onResult(transcript);
            }
        };

        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.warn('Speech error:', event.error);
            }
        };

        this.recognition.onend = () => {
            this.isRecording = false;
            this.onStateChange(false);
            setTimeout(() => { this.processing = false; }, 300);
        };

        try {
            this.recognition.start();
            this.isRecording = true;
            this.onStateChange(true);
        } catch (e) {
            this.isRecording = false;
            this.onStateChange(false);
        }
    }

    stop() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.onStateChange(false);
        try { this.recognition.abort(); } catch (e) {}
    }

    abortPrevious() {
        if (this.recognition) {
            try { this.recognition.abort(); } catch (e) {}
            this.recognition = null;
        }
    }
}

/* ============================================
   RaffleApp - Main Application
   ============================================ */
class RaffleApp {
    constructor() {
        this.participants = [];
        this.maxWinners = 1;
        this.isAnimating = false;
        this.sound = new TickingSound();
        this.init();
    }

    init() {
        this.nameInput = document.getElementById('nameInput');
        this.addBtn = document.getElementById('addBtn');
        this.micBtn = document.getElementById('micBtn');
        this.micStatus = document.getElementById('micStatus');
        this.tagsContainer = document.getElementById('tagsContainer');
        this.emptyMessage = document.getElementById('emptyMessage');
        this.participantCount = document.getElementById('participantCount');
        this.decreaseBtn = document.getElementById('decreaseBtn');
        this.increaseBtn = document.getElementById('increaseBtn');
        this.winnerCountDisplay = document.getElementById('winnerCount');
        this.odometerSection = document.getElementById('odometerSection');
        this.odometerViewport = document.getElementById('odometerViewport');
        this.raffleBtn = document.getElementById('raffleBtn');
        this.resultSection = document.getElementById('resultSection');
        this.resultWinners = document.getElementById('resultWinners');
        this.clearBtn = document.getElementById('clearBtn');
        this.csvInput = document.getElementById('csvInput');
        this.saveBtn = document.getElementById('saveBtn');
        this.raffleNameInput = document.getElementById('raffleNameInput');
        this.rafflesList = document.getElementById('rafflesList');
        this.raffleCount = document.getElementById('raffleCount');
        this.currentRaffleId = null;

        this.addBtn.addEventListener('click', () => this.addParticipant());
        this.nameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.addParticipant();
        });
        this.decreaseBtn.addEventListener('click', () => this.changeWinners(-1));
        this.increaseBtn.addEventListener('click', () => this.changeWinners(1));
        this.raffleBtn.addEventListener('click', () => this.startRaffle());
        this.clearBtn.addEventListener('click', () => this.clearAll());
        this.csvInput.addEventListener('change', (e) => this.handleCsvImport(e));
        this.saveBtn.addEventListener('click', () => this.saveRaffle());
        this.raffleNameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.saveRaffle();
        });

        this.voiceInput = new VoiceInput(
            (transcript) => this.handleVoiceResult(transcript),
            (isRecording) => this.updateMicUI(isRecording)
        );

        if (this.voiceInput.isSupported) {
            this.micBtn.addEventListener('click', () => this.voiceInput.toggle());
        } else {
            this.micBtn.style.display = 'none';
        }

        this.nameInput.focus();
        this.loadRafflesList();
    }

    handleVoiceResult(transcript) {
        const name = transcript.trim();
        if (name.length < 1 || name.length > 50) return;
        if (this.participants.length >= 100) return;
        if (this.participants.includes(name)) return;

        this.participants.push(name);
        this.renderTags();
        this.updateUI();

        this.micBtn.classList.add('success');
        setTimeout(() => this.micBtn.classList.remove('success'), 600);
    }

    handleCsvImport(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            let text = e.target.result;

            // Strip BOM
            if (text.charCodeAt(0) === 0xFEFF) {
                text = text.substring(1);
            }

            // Strip RTF header and extract plain text
            if (text.trimStart().startsWith('{\\rtf')) {
                text = this._parseRtf(text);
            }

            const names = text
                .split(/[\n\r;]+/)
                .map(n => n.trim())
                .filter(n => n.length > 1 && n.length <= 50)
                .map(n => {
                    return n.replace(/[^\x20-\x7E\u00C0-\u024F]/g, '');
                })
                .filter(n => n.length > 1);

            const MAX = 100;
            let added = 0;
            let skipped = 0;

            for (const name of names) {
                if (this.participants.length >= MAX) break;
                if (this.participants.includes(name)) {
                    skipped++;
                    continue;
                }
                this.participants.push(name);
                added++;
            }

            this.renderTags();
            this.updateUI();

            if (skipped > 0 || added < names.length) {
                const msg = added + " agregados" +
                    (skipped > 0 ? ", " + skipped + " duplicados" : "") +
                    (names.length > MAX ? ". Maximo " + MAX + " participantes." : "");
                alert(msg);
            }
        };
        reader.readAsText(file, 'UTF-8');
        event.target.value = '';
    }

    _parseRtf(rtf) {
        let result = '';
        let i = 0;
        let inControlWord = false;
        let controlWord = '';

        while (i < rtf.length) {
            const ch = rtf[i];

            if (ch === '{') {
                i++;
                continue;
            }

            if (ch === '}') {
                i++;
                continue;
            }

            if (ch === '\\' && rtf[i + 1] === '\\') {
                result += '\\';
                i += 2;
                continue;
            }

            if (ch === '\\' && /[a-zA-Z]/.test(rtf[i + 1] || '')) {
                i++;
                let word = '';
                while (i < rtf.length && /[a-zA-Z]/.test(rtf[i])) {
                    word += rtf[i];
                    i++;
                }
                // Skip numeric parameter
                if (i < rtf.length && (rtf[i] === '-' || /[0-9]/.test(rtf[i]))) {
                    if (rtf[i] === '-') i++;
                    while (i < rtf.length && /[0-9]/.test(rtf[i])) i++;
                }
                // Handle special commands
                if (word === 'par' || word === 'tab' || word === 'line') {
                    result += '\n';
                } else if (word === 'space') {
                    result += ' ';
                } else if (word === 'uc' || word === 'uc0') {
                    // Skip unicode count
                } else if (word[0] === 'u' && word.length > 1) {
                    // Unicode escape: \uN? - read the char
                    const code = parseInt(word.substring(1));
                    if (code > 0) {
                        result += String.fromCharCode(code);
                    }
                    // Skip the ? placeholder
                    if (rtf[i] === '?') i++;
                } else if (word === 'tab') {
                    result += '\t';
                }
                i++;
                continue;
            }

            if (ch === '\\' && rtf[i + 1] === '\'') {
                // Hex escape: \'XX
                i += 2;
                const hex = rtf.substring(i, i + 2);
                i += 2;
                const code = parseInt(hex, 16);
                if (!isNaN(code) && code > 0) {
                    result += String.fromCharCode(code);
                }
                continue;
            }

            if (ch === '\\' && rtf[i + 1] === '~') {
                result += '\u00A0';
                i += 2;
                continue;
            }

            if (ch === '\\' && rtf[i + 1] === '-') {
                i += 2;
                continue;
            }

            if (ch === '\\' && rtf[i + 1] === '\\') {
                result += '\\';
                i += 2;
                continue;
            }

            // Skip unknown control words
            if (ch === '\\') {
                i += 2;
                continue;
            }

            // Regular text character
            if (ch !== '\r' && ch !== '\n') {
                result += ch;
            } else {
                result += '\n';
            }
            i++;
        }

        return result
            .replace(/\n{3,}/g, '\n\n')
            .replace(/[ \t]+/g, ' ')
            .trim();
    }

    updateMicUI(isRecording) {
        if (isRecording) {
            this.micBtn.classList.add('recording');
            this.micStatus.textContent = 'Habla...';
        } else {
            this.micBtn.classList.remove('recording');
            this.micStatus.textContent = '';
        }
    }

    addParticipant() {
        const name = this.nameInput.value.trim();
        if (!name) return;
        if (this.participants.length >= 100) {
            alert('Maximo 100 participantes');
            return;
        }
        if (this.participants.includes(name)) {
            this.nameInput.classList.add('shake');
            setTimeout(() => this.nameInput.classList.remove('shake'), 400);
            return;
        }

        this.participants.push(name);
        this.nameInput.value = '';
        this.nameInput.focus();
        this.renderTags();
        this.updateUI();
    }

    removeParticipant(index) {
        this.participants.splice(index, 1);
        this.renderTags();
        this.updateUI();
    }

    renderTags() {
        this.tagsContainer.innerHTML = '';

        if (this.participants.length === 0) {
            this.tagsContainer.innerHTML = '<p class="empty-message">Agrega participantes para comenzar</p>';
            return;
        }

        this.participants.forEach((name, index) => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.innerHTML = `
                <span class="tag-name" title="Click para editar">${this.escapeHtml(name)}</span>
                <button class="tag-remove" title="Eliminar">&times;</button>
            `;

            tag.querySelector('.tag-remove').addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeParticipant(index);
            });

            tag.querySelector('.tag-name').addEventListener('click', (e) => {
                e.stopPropagation();
                this.editParticipant(index, tag);
            });

            this.tagsContainer.appendChild(tag);
        });
    }

    editParticipant(index, tagElement) {
        const nameSpan = tagElement.querySelector('.tag-name');
        const currentName = this.participants[index];

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'tag-edit-input';
        input.value = currentName;
        input.maxLength = 50;

        nameSpan.replaceWith(input);
        input.focus();
        input.select();

        const save = () => {
            const newName = input.value.trim();
            if (newName && newName !== currentName && !this.participants.includes(newName)) {
                this.participants[index] = newName;
            }
            this.renderTags();
            this.updateUI();
        };

        input.addEventListener('blur', save);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                save();
            }
            if (e.key === 'Escape') {
                this.renderTags();
            }
        });
    }

    updateUI() {
        const count = this.participants.length;
        this.participantCount.textContent = count;

        if (count >= 2) {
            this.maxWinners = count;
            this.raffleBtn.disabled = false;
        } else {
            this.maxWinners = 1;
            this.raffleBtn.disabled = true;
        }

        if (this.maxWinners <= 1) {
            this.maxWinners = 1;
        }

        if (this.participants.length === 0) {
            this.maxWinners = 1;
        }

        this.decreaseBtn.disabled = this.maxWinners <= 1;
        this.increaseBtn.disabled = this.participants.length === 0 || this.maxWinners >= this.participants.length;

        if (this.participants.length === 0) {
            this.raffleBtn.disabled = true;
        }

        this.odometerSection.classList.remove('visible');
        this.resultSection.classList.add('hidden');
    }

    changeWinners(delta) {
        const newVal = this.maxWinners + delta;
        if (newVal >= 1 && newVal <= this.participants.length) {
            this.maxWinners = newVal;
            this.winnerCountDisplay.textContent = this.maxWinners;
            this.decreaseBtn.disabled = this.maxWinners <= 1;
            this.increaseBtn.disabled = this.maxWinners >= this.participants.length;
        }
    }

    async startRaffle() {
        if (this.isAnimating || this.participants.length < 2) return;

        this.isAnimating = true;
        this.sound.init();

        this.raffleBtn.disabled = true;
        this.raffleBtn.classList.add('spinning');
        this.raffleBtn.querySelector('.btn-raffle-text').textContent = 'SORTEANDO...';
        this.resultSection.classList.add('hidden');

        try {
            const response = await fetch('/api/raffle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    participants: this.participants,
                    numberOfWinners: this.maxWinners
                })
            });

            if (!response.ok) {
                const error = await response.text();
                alert(error);
                this.resetButton();
                return;
            }

            const data = await response.json();
            await this.animateOdometer(data.winners);
            this.showWinners(data.winners);
        } catch (err) {
            alert('Error al conectar con el servidor');
            this.resetButton();
        }
    }

    animateOdometer(winners) {
        return new Promise((resolve) => {
            this.odometerSection.classList.add('visible');
            this.odometerViewport.innerHTML = '';

            const allNames = [...this.participants];
            const finalName = winners[0];

            const items = [];
            for (let i = 0; i < 3; i++) {
                const div = document.createElement('div');
                div.className = 'odometer-item';
                div.textContent = '---';
                this.odometerViewport.appendChild(div);
                items.push(div);
            }

            items[1].classList.add('center');

            let position = 0;
            const totalTicks = 40 + Math.floor(Math.random() * 15);
            let tick = 0;

            const baseInterval = 50;
            const slowDownStart = totalTicks * 0.6;
            const slowDownEnd = totalTicks * 0.85;

            const spin = () => {
                if (tick >= totalTicks) {
                    items.forEach(item => {
                        item.classList.remove('above', 'below');
                    });
                    items[1].textContent = finalName;
                    items[1].classList.add('winner');
                    items[0].textContent = allNames[(allNames.indexOf(finalName) - 1 + allNames.length) % allNames.length];
                    items[2].textContent = allNames[(allNames.indexOf(finalName) + 1) % allNames.length];
                    this.sound.victory();
                    resolve();
                    return;
                }

                const name = allNames[position % allNames.length];
                items[0].textContent = allNames[(position - 1 + allNames.length * 100) % allNames.length];
                items[1].textContent = name;
                items[2].textContent = allNames[(position + 1) % allNames.length];

                items[0].className = 'odometer-item above';
                items[1].className = 'odometer-item center';
                items[2].className = 'odometer-item below';

                if (tick >= slowDownStart) {
                    const progress = (tick - slowDownStart) / (slowDownEnd - slowDownStart);
                    const blurAmount = Math.max(0, 4 * (1 - progress));
                    items[0].style.filter = `blur(${blurAmount}px)`;
                    items[2].style.filter = `blur(${blurAmount}px)`;
                } else {
                    items[0].style.filter = 'blur(4px)';
                    items[2].style.filter = 'blur(4px)';
                }

                this.sound.tick();
                position++;
                tick++;

                let delay;
                if (tick < slowDownStart) {
                    delay = baseInterval;
                } else if (tick < slowDownEnd) {
                    const progress = (tick - slowDownStart) / (slowDownEnd - slowDownStart);
                    delay = baseInterval + (350 * progress * progress);
                } else {
                    delay = 400;
                }

                setTimeout(spin, delay);
            };

            spin();
        });
    }

    showWinners(winners) {
        this.resultSection.classList.remove('hidden');
        this.resultWinners.innerHTML = '';

        if (winners.length === 1) {
            document.querySelector('.result-title').textContent = 'GANADOR';
        } else {
            document.querySelector('.result-title').textContent = 'GANADORES';
        }

        winners.forEach(name => {
            const div = document.createElement('div');
            div.className = 'winner-name';
            div.textContent = name;
            this.resultWinners.appendChild(div);
        });

        this.createConfetti();
        this.resetButton();
    }

    createConfetti() {
        const container = document.createElement('div');
        container.className = 'confetti-container';
        document.body.appendChild(container);

        const colors = [
            '#009688', '#E88700', '#035C80', '#FFFFFF', '#00769A',
            '#007B6F', '#FF9500', '#2F7499', '#CB3232', '#67A5CD',
            '#FFFFFF', '#009688', '#E88700', '#00ABDE', '#00642F'
        ];
        const shapes = ['circle', 'rect', 'line'];

        for (let i = 0; i < 120; i++) {
            this._spawnConfetti(container, colors, shapes);
        }
        setTimeout(() => {
            for (let i = 0; i < 60; i++) {
                this._spawnConfetti(container, colors, shapes);
            }
        }, 400);
        setTimeout(() => {
            for (let i = 0; i < 30; i++) {
                this._spawnConfetti(container, colors, shapes);
            }
        }, 800);

        setTimeout(() => container.remove(), 5500);
    }

    _spawnConfetti(container, colors, shapes) {
        const el = document.createElement('div');
        const shape = shapes[Math.floor(Math.random() * shapes.length)];
        el.className = `confetti ${shape}`;

        el.style.left = Math.random() * 100 + '%';
        el.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];

        const size = Math.random() * 12 + 4;
        if (shape === 'line') {
            el.style.width = '3px';
            el.style.height = (size * 2) + 'px';
        } else {
            el.style.width = size + 'px';
            el.style.height = size + 'px';
        }

        const duration = Math.random() * 2.5 + 2;
        el.style.setProperty('--fall-duration', duration + 's');
        el.style.animationDelay = (Math.random() * 0.6) + 's';

        container.appendChild(el);
    }

    resetButton() {
        this.isAnimating = false;
        this.raffleBtn.disabled = false;
        this.raffleBtn.classList.remove('spinning');
        this.raffleBtn.querySelector('.btn-raffle-text').textContent = 'SORTEAR';

        if (this.participants.length < 2) {
            this.raffleBtn.disabled = true;
        }
    }

    async saveRaffle() {
        const name = this.raffleNameInput.value.trim();
        if (!name) {
            this.raffleNameInput.classList.add('shake');
            setTimeout(() => this.raffleNameInput.classList.remove('shake'), 400);
            return;
        }
        if (this.participants.length === 0) {
            alert('Agrega participantes antes de guardar');
            return;
        }

        this.saveBtn.disabled = true;

        try {
            const res = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    participants: this.participants,
                    numberOfWinners: this.maxWinners
                })
            });

            const data = await res.json();
            if (data.ok) {
                this.currentRaffleId = data.id;
                this.raffleNameInput.value = '';
                this.loadRafflesList();
            } else {
                alert(data.error || 'Error al guardar');
            }
        } catch (err) {
            alert('Error al conectar con el servidor. Verifica que Vercel KV este configurado.');
        }
        this.saveBtn.disabled = false;
    }

    async loadRafflesList() {
        try {
            const res = await fetch('/api/list');
            const data = await res.json();
            const raffles = data.raffles || [];

            this.raffleCount.textContent = raffles.length;

            if (raffles.length === 0) {
                this.rafflesList.innerHTML = '<p class="empty-message">No hay sorteos guardados</p>';
                return;
            }

            this.rafflesList.innerHTML = '';
            raffles.forEach(raffle => {
                const item = document.createElement('div');
                item.className = 'raffle-item';
                const date = new Date(raffle.createdAt).toLocaleDateString('es-AR');
                item.innerHTML = `
                    <div class="raffle-item-info">
                        <span class="raffle-item-name">${this.escapeHtml(raffle.name)}</span>
                        <span class="raffle-item-meta">${raffle.participantCount} participantes · ${raffle.numberOfWinners} ganador(es) · ${date}</span>
                    </div>
                    <div class="raffle-item-actions">
                        <button class="btn-raffle-action load" data-id="${raffle.id}" title="Cargar sorteo">Cargar</button>
                        <button class="btn-raffle-action delete" data-id="${raffle.id}" title="Eliminar sorteo">X</button>
                    </div>
                `;
                this.rafflesList.appendChild(item);
            });

            this.rafflesList.querySelectorAll('.btn-raffle-action.load').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.loadRaffle(btn.dataset.id);
                });
            });

            this.rafflesList.querySelectorAll('.btn-raffle-action.delete').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.deleteRaffle(btn.dataset.id);
                });
            });
        } catch (err) {
            this.rafflesList.innerHTML = '<p class="empty-message">Error al cargar sorteos</p>';
        }
    }

    async loadRaffle(id) {
        try {
            const res = await fetch('/api/load?id=' + encodeURIComponent(id));
            if (!res.ok) {
                alert('Sorteo no encontrado');
                return;
            }
            const raffle = await res.json();

            this.participants = raffle.participants || [];
            this.maxWinners = raffle.numberOfWinners || 1;
            this.currentRaffleId = raffle.id;
            this.winnerCountDisplay.textContent = this.maxWinners;
            this.raffleNameInput.value = raffle.name;

            this.renderTags();
            this.updateUI();
            this.odometerSection.classList.remove('visible');
            this.resultSection.classList.add('hidden');
        } catch (err) {
            alert('Error al cargar el sorteo');
        }
    }

    async deleteRaffle(id) {
        if (!confirm('Eliminar este sorteo guardado?')) return;

        try {
            await fetch('/api/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            this.loadRafflesList();
        } catch (err) {
            alert('Error al eliminar');
        }
    }

    clearAll() {
        this.participants = [];
        this.maxWinners = 1;
        this.isAnimating = false;
        this.currentRaffleId = null;
        this.winnerCountDisplay.textContent = '1';
        this.renderTags();
        this.updateUI();
        this.odometerSection.classList.remove('visible');
        this.resultSection.classList.add('hidden');
        this.nameInput.focus();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new RaffleApp();
});
