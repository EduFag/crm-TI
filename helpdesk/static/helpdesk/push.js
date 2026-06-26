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

    function mostrarBannerElemento() {
        const banner = document.getElementById('helpdesk-push-banner');
        if (banner) {
            banner.classList.remove('hidden');
            banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function atualizarNavPush() {
        const btn = document.getElementById('helpdesk-push-nav-btn');
        const label = document.getElementById('helpdesk-push-nav-label');
        if (!btn || !label) {
            return;
        }

        if (!suportaPush()) {
            btn.classList.add('hidden');
            return;
        }

        btn.classList.remove('hidden');

        const permissao = Notification.permission;
        if (permissao === 'granted') {
            label.textContent = 'Notificações ativas';
            btn.classList.remove('text-slate-500', 'hover:text-blue-600', 'text-amber-600', 'hover:text-amber-700');
            btn.classList.add('text-green-600', 'cursor-default');
            btn.disabled = true;
            return;
        }

        btn.disabled = false;
        btn.classList.remove('text-green-600', 'cursor-default');
        if (permissao === 'denied') {
            label.textContent = 'Reativar notificações';
            btn.classList.remove('text-slate-500', 'hover:text-blue-600');
            btn.classList.add('text-amber-600', 'hover:text-amber-700');
            return;
        }

        label.textContent = 'Ativar notificações';
        btn.classList.remove('text-amber-600', 'hover:text-amber-700', 'text-green-600');
        btn.classList.add('text-slate-500', 'hover:text-blue-600');
    }

    function textoAjudaNegado() {
        return (
            'No Chrome: clique no cadeado à esquerda do endereço → ' +
            '<strong>Notificações</strong> → ligue a opção (ou clique em ' +
            '<strong>Redefinir permissão</strong>) → depois clique em <strong>Verificar</strong> aqui. ' +
            'O navegador não permite que sites abram essa tela automaticamente por segurança.'
        );
    }

    function criarBotao(label, classes, onclick) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = label;
        btn.className = classes;
        btn.addEventListener('click', onclick);
        return btn;
    }

    function renderizarBanner() {
        const banner = document.getElementById('helpdesk-push-banner');
        const texto = document.getElementById('helpdesk-push-texto');
        const ajuda = document.getElementById('helpdesk-push-ajuda');
        const acoes = document.getElementById('helpdesk-push-acoes');
        if (!banner || !texto || !ajuda || !acoes) {
            return;
        }

        if (!suportaPush()) {
            esconderBanner();
            atualizarNavPush();
            return;
        }

        const permissao = Notification.permission;

        if (permissao === 'granted') {
            esconderBanner();
            atualizarNavPush();
            return;
        }

        acoes.innerHTML = '';
        banner.classList.remove('hidden', 'bg-blue-50', 'border-blue-200', 'text-blue-900');
        banner.classList.remove('bg-amber-50', 'border-amber-300', 'text-amber-950');

        if (permissao === 'denied') {
            banner.classList.add('bg-amber-50', 'border-amber-300', 'text-amber-950');
            texto.textContent = 'Notificações bloqueadas neste site';
            ajuda.innerHTML = textoAjudaNegado();
            ajuda.classList.remove('hidden');
            acoes.appendChild(criarBotao(
                'Verificar',
                'px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors',
                verificarPermissao
            ));
            atualizarNavPush();
            return;
        }

        // permission === 'default' — banner opcional; o botão da nav sempre dispara o prompt nativo
        if (localStorage.getItem(STORAGE_KEY) === 'dismissed') {
            esconderBanner();
            atualizarNavPush();
            return;
        }

        banner.classList.add('bg-blue-50', 'border-blue-200', 'text-blue-900');
        texto.textContent = 'Receba alertas de chamados mesmo com o navegador fechado — comentários, movimentações e alterações de prioridade.';
        ajuda.classList.add('hidden');
        ajuda.textContent = '';
        acoes.appendChild(criarBotao(
            'Ativar notificações',
            'px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors',
            ativarNotificacoes
        ));
        acoes.appendChild(criarBotao(
            'Agora não',
            'px-4 py-2 text-blue-700 hover:bg-blue-100 rounded-lg text-sm font-medium transition-colors',
            dispensarBanner
        ));
        atualizarNavPush();
    }

    function clicarNavPush() {
        if (!suportaPush()) {
            alert('Seu navegador não suporta notificações push.');
            return;
        }

        const permissao = Notification.permission;

        if (permissao === 'denied') {
            localStorage.removeItem(STORAGE_KEY);
            renderizarBanner();
            mostrarBannerElemento();
            return;
        }

        if (permissao === 'granted') {
            return;
        }

        // default — gesto do usuário: abre o prompt nativo do navegador (MDN)
        ativarNotificacoes();
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

        if (Notification.permission === 'denied') {
            renderizarBanner();
            return;
        }

        const permissao = await Notification.requestPermission();
        localStorage.setItem(STORAGE_KEY, permissao === 'default' ? 'dismissed' : permissao);

        if (permissao === 'denied') {
            renderizarBanner();
            return;
        }

        if (permissao !== 'granted') {
            renderizarBanner();
            return;
        }

        try {
            await registrarSubscription();
            esconderBanner();
            atualizarNavPush();
        } catch (err) {
            console.error('Erro ao ativar push:', err);
            alert('Não foi possível ativar as notificações. Verifique se o servidor está configurado com chaves VAPID.');
        }
    }

    async function verificarPermissao() {
        if (Notification.permission === 'granted') {
            localStorage.removeItem(STORAGE_KEY);
            try {
                await registrarSubscription();
            } catch (err) {
                console.error('Erro ao registrar push:', err);
            }
            esconderBanner();
            atualizarNavPush();
            return;
        }
        renderizarBanner();
        alert('Notificações ainda estão desligadas. Siga os passos no banner (cadeado → Notificações → permitir) e clique em Verificar novamente.');
    }

    function dispensarBanner() {
        localStorage.setItem(STORAGE_KEY, 'dismissed');
        esconderBanner();
        atualizarNavPush();
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
        verificar: verificarPermissao,
        dispensar: dispensarBanner,
        suportaPush: suportaPush,
    };

    document.addEventListener('DOMContentLoaded', function() {
        const navBtn = document.getElementById('helpdesk-push-nav-btn');
        if (navBtn) {
            navBtn.addEventListener('click', clicarNavPush);
        }

        renderizarBanner();
        abrirChamadoDaUrl();

        if (Notification.permission === 'granted' && suportaPush()) {
            registrarSubscription().catch(function() {
                /* silencioso — chaves VAPID podem não estar configuradas em dev */
            });
        }
    });

    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            renderizarBanner();
        }
    });
})();
