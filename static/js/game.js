// Main JavaScript for Ride the Bus game
class RideTheBusGame {
    constructor() {
        this.socket = null;
        this.gameState = null;
        this.playerId = null;
        this.roomCode = null;
        
        this.init();
    }
    
    init() {
        // Initialize Socket.IO if available
        if (typeof io !== 'undefined') {
            this.socket = io();
            this.setupSocketEvents();
        }
        
        // Setup game event listeners
        this.setupEventListeners();
        
        // Setup PWA service worker
        this.setupServiceWorker();
    }
    
    setupSocketEvents() {
        this.socket.on('connect', () => {
            console.log('Connected to game server');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from game server');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('game_update', (data) => {
            this.handleGameUpdate(data);
        });
        
        this.socket.on('player_joined', (data) => {
            this.handlePlayerJoined(data);
        });
        
        this.socket.on('player_left', (data) => {
            this.handlePlayerLeft(data);
        });
    }
    
    setupEventListeners() {
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });
        
        // Card selection
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('card') && !e.target.classList.contains('card-back')) {
                this.handleCardSelection(e.target);
            }
        });
        
        // Settings persistence
        this.loadSettings();
        
        // Setup settings change handlers
        const alcoholModeToggle = document.getElementById('alcohol-mode');
        const soundEffectsToggle = document.getElementById('sound-effects');
        const animationsToggle = document.getElementById('animations');
        
        if (alcoholModeToggle) {
            alcoholModeToggle.addEventListener('change', () => {
                this.saveSetting('alcoholMode', alcoholModeToggle.checked);
                this.updateGameLabels();
            });
        }
        
        if (soundEffectsToggle) {
            soundEffectsToggle.addEventListener('change', () => {
                this.saveSetting('soundEffects', soundEffectsToggle.checked);
            });
        }
        
        if (animationsToggle) {
            animationsToggle.addEventListener('change', () => {
                this.saveSetting('animations', animationsToggle.checked);
                document.body.classList.toggle('no-animations', !animationsToggle.checked);
            });
        }
    }
    
    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then((registration) => {
                    console.log('SW registered:', registration);
                })
                .catch((error) => {
                    console.log('SW registration failed:', error);
                });
        }
    }
    
    handleKeyboardNavigation(e) {
        // Escape key closes modals
        if (e.key === 'Escape') {
            this.closeAllModals();
        }
        
        // Arrow keys for card navigation
        if (e.key.startsWith('Arrow')) {
            this.handleArrowKeyNavigation(e);
        }
        
        // Number keys for quick guesses
        if (e.key >= '1' && e.key <= '4') {
            this.handleNumberKeyGuess(parseInt(e.key));
        }
        
        // Space or Enter to confirm actions
        if (e.key === ' ' || e.key === 'Enter') {
            const focusedElement = document.activeElement;
            if (focusedElement && focusedElement.classList.contains('guess-btn')) {
                e.preventDefault();
                focusedElement.click();
            }
        }
    }
    
    handleArrowKeyNavigation(e) {
        const cards = document.querySelectorAll('.card:not(.card-back)');
        const currentIndex = Array.from(cards).findIndex(card => card === document.activeElement);
        
        let newIndex = currentIndex;
        
        switch (e.key) {
            case 'ArrowLeft':
                newIndex = Math.max(0, currentIndex - 1);
                break;
            case 'ArrowRight':
                newIndex = Math.min(cards.length - 1, currentIndex + 1);
                break;
        }
        
        if (newIndex !== currentIndex && cards[newIndex]) {
            cards[newIndex].focus();
            e.preventDefault();
        }
    }
    
    handleNumberKeyGuess(number) {
        const guessButtons = document.querySelectorAll('.guess-btn:not(:disabled)');
        if (guessButtons[number - 1]) {
            guessButtons[number - 1].click();
        }
    }
    
    handleCardSelection(cardElement) {
        // Add visual feedback
        cardElement.classList.add('selected');
        
        // Remove selection from other cards
        document.querySelectorAll('.card.selected').forEach(card => {
            if (card !== cardElement) {
                card.classList.remove('selected');
            }
        });
        
        // Enable/disable action buttons based on selection
        this.updateActionButtons();
    }
    
    handleGameUpdate(data) {
        console.log('Game state updated:', data);
        
        // Update game state
        this.gameState = data;
        
        // Update UI elements
        this.updatePlayerTurn();
        this.updateGamePhase();
        this.updatePlayerHands();
        this.updateGameLog();
        
        // Play sound effects if enabled
        if (this.getSetting('soundEffects', true)) {
            this.playGameSound(data.action);
        }
        
        // Show animations if enabled
        if (this.getSetting('animations', true)) {
            this.playGameAnimation(data.action);
        }
    }
    
    handlePlayerJoined(data) {
        this.showNotification(`${data.playerName} joined the game`);
        this.updatePlayersList();
    }
    
    handlePlayerLeft(data) {
        this.showNotification(`${data.playerName} left the game`);
        this.updatePlayersList();
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            statusIndicator.classList.toggle('connected', connected);
            statusIndicator.classList.toggle('disconnected', !connected);
        }
    }
    
    updateGameLabels() {
        const alcoholMode = this.getSetting('alcoholMode', true);
        const drinkUnit = alcoholMode ? 'sip' : 'point';
        const assignAction = alcoholMode ? 'assign' : 'give';
        
        // Update all drink-related text
        document.querySelectorAll('[data-drink-unit]').forEach(el => {
            el.textContent = el.textContent.replace(/sip|point/g, drinkUnit);
        });
        
        document.querySelectorAll('[data-assign-action]').forEach(el => {
            el.textContent = el.textContent.replace(/assign|give/g, assignAction);
        });
    }
    
    closeAllModals() {
        document.querySelectorAll('.modal, [id$="-modal"]').forEach(modal => {
            modal.classList.add('hidden');
        });
    }
    
    updateActionButtons() {
        const selectedCard = document.querySelector('.card.selected');
        const commitMatchBtn = document.getElementById('commit-match-btn');
        
        if (commitMatchBtn) {
            commitMatchBtn.disabled = !selectedCard;
        }
    }
    
    playGameSound(action) {
        // Placeholder for sound effects
        // In a full implementation, you'd load and play audio files
        const sounds = {
            'card_dealt': 'card-flip',
            'guess_correct': 'success',
            'guess_wrong': 'fail',
            'pyramid_flip': 'card-flip',
            'bus_flip': 'card-flip',
            'game_start': 'start',
            'game_end': 'end'
        };
        
        const soundName = sounds[action];
        if (soundName) {
            // In a full implementation, you'd load and play audio files
            // this.audioManager.play(soundName);
        }
    }
    
    playGameAnimation(action) {
        // Placeholder for animations
        const animations = {
            'card_dealt': () => this.animateCardDeal(),
            'pyramid_flip': () => this.animatePyramidFlip(),
            'bus_flip': () => this.animateBusFlip()
        };
        
        const animationFn = animations[action];
        if (animationFn) {
            animationFn();
        }
    }
    
    animateCardDeal() {
        const newCard = document.querySelector('.card:last-child');
        if (newCard) {
            newCard.classList.add('card-flip');
            setTimeout(() => newCard.classList.remove('card-flip'), 600);
        }
    }
    
    animatePyramidFlip() {
        const flippedCard = document.querySelector('.pyramid-card[data-just-flipped]');
        if (flippedCard) {
            flippedCard.classList.add('card-flip');
            setTimeout(() => {
                flippedCard.classList.remove('card-flip');
                flippedCard.removeAttribute('data-just-flipped');
            }, 600);
        }
    }
    
    animateBusFlip() {
        const busCard = document.querySelector('.bus-card[data-just-flipped]');
        if (busCard) {
            busCard.classList.add('card-flip');
            setTimeout(() => {
                busCard.classList.remove('card-flip');
                busCard.removeAttribute('data-just-flipped');
            }, 600);
        }
    }
    
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} fixed top-4 right-4 bg-green-800 text-white px-4 py-2 rounded-lg shadow-lg z-50`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Remove after duration
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
    
    // Settings management
    saveSetting(key, value) {
        localStorage.setItem(`rtb_${key}`, JSON.stringify(value));
    }
    
    getSetting(key, defaultValue = null) {
        const stored = localStorage.getItem(`rtb_${key}`);
        return stored ? JSON.parse(stored) : defaultValue;
    }
    
    loadSettings() {
        const alcoholMode = this.getSetting('alcoholMode', true);
        const soundEffects = this.getSetting('soundEffects', true);
        const animations = this.getSetting('animations', true);
        
        const alcoholModeToggle = document.getElementById('alcohol-mode');
        const soundEffectsToggle = document.getElementById('sound-effects');
        const animationsToggle = document.getElementById('animations');
        
        if (alcoholModeToggle) alcoholModeToggle.checked = alcoholMode;
        if (soundEffectsToggle) soundEffectsToggle.checked = soundEffects;
        if (animationsToggle) animationsToggle.checked = animations;
        
        // Apply settings
        this.updateGameLabels();
        document.body.classList.toggle('no-animations', !animations);
    }
}

// Initialize game when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.rideTheBusGame = new RideTheBusGame();
});

// Utility functions
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleTimeString();
}

function getCardDisplay(card) {
    const suitIcons = {
        'HEARTS': '♥️',
        'DIAMONDS': '♦️',
        'CLUBS': '♣️',
        'SPADES': '♠️'
    };
    return `${card.rank}${suitIcons[card.suit] || card.suit}`;
}

function isRed(suit) {
    return suit === 'HEARTS' || suit === 'DIAMONDS';
}

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RideTheBusGame;
}