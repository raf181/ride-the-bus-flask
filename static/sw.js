// Service Worker for Ride the Bus PWA
const CACHE_NAME = 'ride-the-bus-v1';
const STATIC_CACHE_NAME = 'ride-the-bus-static-v1';

// Files to cache for offline functionality
const STATIC_FILES = [
    '/',
    '/static/css/game.css',
    '/static/js/game.js',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',
    'https://cdn.socket.io/4.5.0/socket.io.min.js'
];

// Dynamic cache patterns
const CACHE_PATTERNS = [
    /^\/static\//,
    /^\/templates\//,
    /\.css$/,
    /\.js$/,
    /\.png$/,
    /\.jpg$/,
    /\.jpeg$/,
    /\.gif$/,
    /\.svg$/
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then((cache) => {
                console.log('Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => self.skipWaiting())
            .catch((error) => {
                console.error('Cache installation failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE_NAME) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-HTTP requests
    if (!request.url.startsWith('http')) {
        return;
    }
    
    // Handle API requests (always go to network first)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // Handle Socket.IO requests (always go to network)
    if (url.pathname.includes('socket.io')) {
        event.respondWith(fetch(request));
        return;
    }
    
    // Handle static assets
    if (shouldCache(request.url)) {
        event.respondWith(cacheFirst(request));
        return;
    }
    
    // Handle page requests
    if (request.mode === 'navigate') {
        event.respondWith(networkFirstWithFallback(request));
        return;
    }
    
    // Default: network first
    event.respondWith(networkFirst(request));
});

// Cache strategies
async function cacheFirst(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Cache first strategy failed:', error);
        return new Response('Offline', { status: 503 });
    }
}

async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok && shouldCache(request.url)) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        return new Response('Offline', { 
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

async function networkFirstWithFallback(request) {
    try {
        const networkResponse = await fetch(request);
        return networkResponse;
    } catch (error) {
        // Try to find cached version
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Fallback to offline page
        const offlinePage = await caches.match('/');
        if (offlinePage) {
            return offlinePage;
        }
        
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Offline - Ride the Bus</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { font-family: sans-serif; text-align: center; padding: 50px; background: #16a34a; color: white; }
                    h1 { color: #fbbf24; }
                </style>
            </head>
            <body>
                <h1>🃏 Ride the Bus</h1>
                <h2>You're Offline</h2>
                <p>Please check your internet connection and try again.</p>
                <button onclick="location.reload()">Try Again</button>
            </body>
            </html>
        `, {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/html' }
        });
    }
}

// Helper functions
function shouldCache(url) {
    return CACHE_PATTERNS.some(pattern => {
        if (pattern instanceof RegExp) {
            return pattern.test(url);
        }
        return url.includes(pattern);
    });
}

// Background sync for game actions when back online
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);
    
    if (event.tag === 'game-action-sync') {
        event.waitUntil(syncGameActions());
    }
});

async function syncGameActions() {
    try {
        // Get pending actions from IndexedDB or localStorage
        const pendingActions = getPendingGameActions();
        
        for (const action of pendingActions) {
            try {
                await fetch(action.url, {
                    method: action.method,
                    headers: action.headers,
                    body: action.body
                });
                
                // Remove from pending actions
                removePendingGameAction(action.id);
            } catch (error) {
                console.error('Failed to sync action:', action, error);
            }
        }
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}

function getPendingGameActions() {
    // Placeholder - would read from IndexedDB in production
    try {
        const stored = localStorage.getItem('pendingGameActions');
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

function removePendingGameAction(actionId) {
    try {
        const stored = localStorage.getItem('pendingGameActions');
        const actions = stored ? JSON.parse(stored) : [];
        const filtered = actions.filter(action => action.id !== actionId);
        localStorage.setItem('pendingGameActions', JSON.stringify(filtered));
    } catch (error) {
        console.error('Failed to remove pending action:', error);
    }
}

// Push notifications (for game updates)
self.addEventListener('push', (event) => {
    console.log('Push notification received:', event);
    
    const options = {
        body: 'Your turn in Ride the Bus!',
        icon: '/static/icon-192.png',
        badge: '/static/icon-72.png',
        tag: 'game-notification',
        renotify: true,
        actions: [
            {
                action: 'play',
                title: 'Play Turn',
                icon: '/static/icon-72.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ]
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            options.body = data.message || options.body;
            options.data = data;
        } catch (error) {
            console.error('Failed to parse push data:', error);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification('Ride the Bus', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event);
    
    event.notification.close();
    
    if (event.action === 'play') {
        // Open the game
        event.waitUntil(
            clients.openWindow('/')
        );
    }
    // 'dismiss' action or no action - just close notification
});

console.log('Service Worker loaded');