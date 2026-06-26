/* Service Worker — notificações Web Push do helpdesk */

const CACHE_VERSION = 'helpdesk-push-v2';
const ICON_URL = '/static/helpdesk/images/favicon.ico';

self.addEventListener('push', function(event) {
    if (!event.data) {
        return;
    }

    let payload = {};
    try {
        payload = event.data.json();
    } catch (e) {
        payload = { title: 'Helpdesk', body: event.data.text() };
    }

    const title = payload.title || 'Helpdesk';
    const options = {
        body: payload.body || '',
        icon: payload.icon || ICON_URL,
        badge: ICON_URL,
        tag: payload.tag || ('helpdesk-' + Date.now()),
        renotify: true,
        data: { url: payload.url || '/helpdesk/' },
        requireInteraction: false,
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    const url = (event.notification.data && event.notification.data.url) || '/helpdesk/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url.indexOf('/helpdesk') !== -1 && 'focus' in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(key) { return key.startsWith('helpdesk-push-') && key !== CACHE_VERSION; })
                    .map(function(key) { return caches.delete(key); })
            );
        })
    );
});
