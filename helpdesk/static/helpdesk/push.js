/**
 * Registro Web Push e pedido de permissão — helpdesk.
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'helpdesk_push_banner';
    const SW_URL = '/static/helpdesk/sw.js';
    const SW_SCOPE = '/helpdesk/';

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function urlBaseHelpdesk() {
        const meta = document.querySelector('meta[name="helpdesk-push-base"]');
        return meta ? meta.getAttribute('content') : '/helpdesk/';
    }

    function urlVapidKey() {
        return urlBaseHelpdesk() + 'push/vapid-public-key/';
    }

    function urlSubscribe() {
        return urlBaseHelpdesk() + 'push/subscribe/';
    }

    function urlUnsubscribe() {
        return urlBaseHelpdesk() + 'push/unsubscribe/';
    }

    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function suportaPush() {
        return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    }

    function esconderBanner() {
        const banner = document.getElementById('helpdesk-push-banner');
        if (banner) {
            banner.classList.add('hidden');
        }
    }

    function mostrarBanner() {
        if (!suportaPush()) {
            return;
        }
        if (Notification.permission !== 'default') {
            return;
        }
        if (localStorage.getItem(STORAGE_KEY) === 'dismissed') {
            return;
        }
        const banner = document.getElementById('helpdesk-push-banner');
        if (banner) {
            banner.classList.remove('hidden');
        }
    }

    async function buscarChavePublica() {
        const response = await fetch(urlVapidKey(), { credentials: 'same-origin' });
        if (!response.ok) {
            throw new Error('Chave VAPID indisponível');
        }
        const data = await response.json();
        return data.publicKey;
    }

    async function registrarSubscription() {
        const publicKey = await buscarChavePublica();
        const registration = await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE });
        await navigator.serviceWorker.ready;

        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey),
            });
        }

        const response = await fetch(urlSubscribe(), {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(subscription.toJSON()),
        });

        if (!response.ok) {
            throw new Error('Falha ao salvar subscription');
        }
        return subscription;
    }

    async function ativarNotificacoes() {
        if (!suportaPush()) {
            alert('Seu navegador não suporta notificações push.');
            return;
        }

        const permissao = await Notification.requestPermission();
        localStorage.setItem(STORAGE_KEY, permissao === 'default' ? 'dismissed' : permissao);

        if (permissao !== 'granted') {
            esconderBanner();
            return;
        }

        try {
            await registrarSubscription();
            esconderBanner();
        } catch (err) {
            console.error('Erro ao ativar push:', err);
            alert('Não foi possível ativar as notificações. Verifique se o servidor está configurado com chaves VAPID.');
        }
    }

    function dispensarBanner() {
        localStorage.setItem(STORAGE_KEY, 'dismissed');
        esconderBanner();
    }

    function abrirChamadoDaUrl() {
        const params = new URLSearchParams(window.location.search);
        const ticketId = params.get('ticket');
        if (!ticketId) {
            return;
        }

        const drawerUrl = urlBaseHelpdesk() + 'ticket/' + ticketId + '/drawer/';
        if (typeof htmx !== 'undefined') {
            htmx.ajax('GET', drawerUrl, { target: '#drawer-container', swap: 'innerHTML' });
        } else {
            fetch(drawerUrl, { credentials: 'same-origin' })
                .then(function(r) { return r.text(); })
                .then(function(html) {
                    const container = document.getElementById('drawer-container');
                    if (container) {
                        container.innerHTML = html;
                    }
                });
        }

        if (window.history && window.history.replaceState) {
            window.history.replaceState({}, '', window.location.pathname);
        }
    }

    window.helpdeskPush = {
        ativar: ativarNotificacoes,
        dispensar: dispensarBanner,
        suportaPush: suportaPush,
    };

    document.addEventListener('DOMContentLoaded', function() {
        mostrarBanner();
        abrirChamadoDaUrl();

        if (Notification.permission === 'granted' && suportaPush()) {
            registrarSubscription().catch(function() {
                /* silencioso — chaves VAPID podem não estar configuradas em dev */
            });
        }
    });
})();
