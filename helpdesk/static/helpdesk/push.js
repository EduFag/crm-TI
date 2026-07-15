/**
 * Registro Web Push e pedido de permissão — helpdesk.
 * requestPermission() deve ser chamado no mesmo stack do clique (sem DOM/await antes).
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'helpdesk_push_banner';
    const SW_SCOPE = '/helpdesk/';

    function urlServiceWorker() {
        return urlBaseHelpdesk() + 'sw.js';
    }

    let estadoPermissao = 'prompt'; // granted | prompt | denied
    let registradoNoServidor = false;
    let observadorPermissao = null;

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.getAttribute('content')) {
            return meta.getAttribute('content');
        }
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function urlBaseHelpdesk() {
        const meta = document.querySelector('meta[name="helpdesk-push-base"]');
        return meta ? meta.getAttribute('content') : '/helpdesk/';
    }

    function assetVersion() {
        const meta = document.querySelector('meta[name="helpdesk-asset-v"]');
        return meta ? (meta.getAttribute('content') || '') : '';
    }

    function comVersao(url) {
        const v = assetVersion();
        if (!v) {
            return url;
        }
        return url + (url.indexOf('?') >= 0 ? '&' : '?') + 'v=' + encodeURIComponent(v);
    }

    function urlServiceWorker() {
        return comVersao(urlBaseHelpdesk() + 'sw.js');
    }

    function urlVapidKey() {
        return urlBaseHelpdesk() + 'push/vapid-public-key/';
    }

    function urlSubscribe() {
        return urlBaseHelpdesk() + 'push/subscribe/';
    }

    function urlStatus() {
        return urlBaseHelpdesk() + 'push/status/';
    }

    function permissoesConcedidas() {
        return estadoPermissao === 'granted' || Notification.permission === 'granted';
    }

    async function verificarRegistroServidor() {
        try {
            const response = await fetch(urlStatus(), { credentials: 'same-origin' });
            if (!response.ok) {
                return false;
            }
            const data = await response.json();
            registradoNoServidor = Boolean(data.registered);
            return registradoNoServidor;
        } catch (err) {
            console.error('[helpdesk push] Falha ao verificar status:', err);
            return false;
        }
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

    function mapearEstadoLegado() {
        if (Notification.permission === 'granted') {
            return 'granted';
        }
        if (Notification.permission === 'denied') {
            return 'denied';
        }
        return 'prompt';
    }

    async function sincronizarEstadoPermissao() {
        if (!suportaPush()) {
            estadoPermissao = 'denied';
            return estadoPermissao;
        }

        if ('permissions' in navigator) {
            try {
                const status = await navigator.permissions.query({ name: 'notifications' });
                estadoPermissao = status.state;

                if (!observadorPermissao) {
                    observadorPermissao = status;
                    status.onchange = function() {
                        estadoPermissao = status.state;
                        renderizarBanner();
                        atualizarToggleNav();
                        if (status.state === 'granted') {
                            concluirAtivacao();
                        }
                    };
                }
                return estadoPermissao;
            } catch (err) {
                /* Safari antigo ou API indisponível */
            }
        }

        estadoPermissao = mapearEstadoLegado();
        return estadoPermissao;
    }

    function esconderBanner() {
        const banner = document.getElementById('helpdesk-push-banner');
        if (banner) {
            banner.classList.add('hidden');
        }
    }

    function mostrarFeedbackBanner(mensagem) {
        const ajuda = document.getElementById('helpdesk-push-ajuda');
        if (ajuda) {
            ajuda.textContent = mensagem;
            ajuda.classList.remove('hidden');
        }
    }

    function textoAjudaNegado() {
        return (
            'O Chrome não permite abrir as configurações por código. ' +
            'Clique no cadeado → Notificações → Redefinir permissão → volte e ligue o toggle acima.'
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

    function atualizarToggleNav() {
        const toggle = document.getElementById('helpdesk-push-toggle');
        const track = document.getElementById('helpdesk-push-toggle-track');
        const knob = document.getElementById('helpdesk-push-toggle-knob');
        const label = document.getElementById('helpdesk-push-nav-label');
        if (!toggle || !track || !knob || !label) {
            return;
        }

        if (!suportaPush()) {
            toggle.classList.add('hidden');
            return;
        }

        toggle.classList.remove('hidden');

        const permissaoOk = permissoesConcedidas();
        const ativo = permissaoOk && registradoNoServidor;
        const pendente = permissaoOk && !registradoNoServidor;

        if (ativo) {
            label.textContent = 'Notificações ativas';
        } else if (pendente) {
            label.textContent = 'Sincronizar notificações';
        } else {
            label.textContent = 'Notificações';
        }

        label.classList.toggle('text-green-700', ativo);
        label.classList.toggle('text-amber-700', pendente);
        label.classList.toggle('text-slate-600', !ativo && !pendente);

        track.classList.toggle('bg-green-500', ativo);
        track.classList.toggle('bg-amber-400', pendente || (!ativo && !pendente && estadoPermissao === 'denied'));
        track.classList.toggle('bg-slate-300', !ativo && !pendente && estadoPermissao !== 'denied');

        knob.classList.toggle('translate-x-6', ativo || pendente);
        knob.classList.toggle('translate-x-1', !ativo && !pendente);
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
            atualizarToggleNav();
            return;
        }

        if (estadoPermissao === 'granted' && registradoNoServidor) {
            esconderBanner();
            atualizarToggleNav();
            return;
        }

        if (estadoPermissao === 'granted' && !registradoNoServidor) {
            banner.classList.remove('hidden');
            banner.classList.add('bg-amber-50', 'border-amber-300', 'text-amber-950');
            banner.classList.remove('bg-blue-50', 'border-blue-200', 'text-blue-900');
            texto.textContent = 'Permissão concedida no navegador — falta sincronizar com o servidor';
            ajuda.textContent = 'Clique em Sincronizar ou ligue o toggle Notificações no canto superior direito.';
            ajuda.classList.remove('hidden');
            acoes.innerHTML = '';
            acoes.appendChild(criarBotao(
                'Sincronizar',
                'px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors',
                concluirAtivacao
            ));
            atualizarToggleNav();
            return;
        }

        acoes.innerHTML = '';
        banner.classList.remove('hidden', 'bg-blue-50', 'border-blue-200', 'text-blue-900');
        banner.classList.remove('bg-amber-50', 'border-amber-300', 'text-amber-950');

        if (estadoPermissao === 'denied') {
            banner.classList.add('bg-amber-50', 'border-amber-300', 'text-amber-950');
            texto.textContent = 'Notificações bloqueadas pelo navegador';
            ajuda.innerHTML = textoAjudaNegado();
            ajuda.classList.remove('hidden');
            acoes.appendChild(criarBotao(
                'Como reativar',
                'px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors',
                function() {
                    mostrarFeedbackBanner(
                        'Cadeado na barra de endereço → Notificações → Redefinir permissão. ' +
                        'Depois ligue o toggle "Notificações" no canto superior direito.'
                    );
                }
            ));
            atualizarToggleNav();
            return;
        }

        // prompt — pode abrir popup nativo no clique
        if (localStorage.getItem(STORAGE_KEY) === 'dismissed') {
            esconderBanner();
            atualizarToggleNav();
            return;
        }

        banner.classList.add('bg-blue-50', 'border-blue-200', 'text-blue-900');
        texto.textContent = 'Receba alertas de chamados mesmo com o navegador fechado.';
        ajuda.classList.add('hidden');
        ajuda.textContent = '';
        acoes.appendChild(criarBotao(
            'Ativar notificações',
            'px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors',
            pedirPermissaoNoClique
        ));
        acoes.appendChild(criarBotao(
            'Agora não',
            'px-4 py-2 text-blue-700 hover:bg-blue-100 rounded-lg text-sm font-medium transition-colors',
            dispensarBanner
        ));
        atualizarToggleNav();
    }

    function tratarResultadoPermissao(resultado) {
        localStorage.setItem(STORAGE_KEY, resultado === 'default' ? 'dismissed' : resultado);

        if (resultado === 'granted') {
            estadoPermissao = 'granted';
            concluirAtivacao();
            return;
        }

        if (resultado === 'denied') {
            estadoPermissao = 'denied';
        } else {
            estadoPermissao = 'prompt';
        }

        renderizarBanner();

        if (resultado === 'denied') {
            mostrarFeedbackBanner(
                'O Chrome bloqueou o prompt (permissão negada). ' +
                'Use o cadeado → Notificações → Redefinir permissão e ligue o toggle novamente.'
            );
        }
    }

    function pedirPermissaoNoClique() {
        if (!suportaPush()) {
            alert('Seu navegador não suporta notificações push.');
            return;
        }

        if (Notification.permission === 'granted') {
            estadoPermissao = 'granted';
            concluirAtivacao();
            return;
        }

        // Sem await/DOM antes — preserva gesto do usuário para o popup nativo
        Notification.requestPermission().then(tratarResultadoPermissao);
    }

    function clicarToggleNav(event) {
        event.preventDefault();

        if (!suportaPush()) {
            alert('Seu navegador não suporta notificações push.');
            return;
        }

        if (permissoesConcedidas()) {
            concluirAtivacao();
            return;
        }

        localStorage.removeItem(STORAGE_KEY);
        pedirPermissaoNoClique();
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
        const swUrl = urlServiceWorker();
        let registration;

        try {
            registration = await navigator.serviceWorker.register(swUrl, { scope: SW_SCOPE });
        } catch (err) {
            throw new Error('Falha ao registrar Service Worker (' + swUrl + '): ' + err.message);
        }

        await navigator.serviceWorker.ready;

        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
            try {
                subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(publicKey),
                });
            } catch (err) {
                const antiga = await registration.pushManager.getSubscription();
                if (antiga) {
                    await antiga.unsubscribe();
                }
                try {
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array(publicKey),
                    });
                } catch (err2) {
                    throw new Error('Falha ao inscrever no Push: ' + err2.message);
                }
            }
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
            const detalhe = await response.text();
            throw new Error('Servidor recusou subscription (' + response.status + '): ' + detalhe);
        }

        const data = await response.json();
        registradoNoServidor = Boolean(data.success);
        return subscription;
    }

    async function concluirAtivacao() {
        try {
            await registrarSubscription();
            await verificarRegistroServidor();
            esconderBanner();
            atualizarToggleNav();
        } catch (err) {
            registradoNoServidor = false;
            atualizarToggleNav();
            console.error('[helpdesk push] Erro ao ativar:', err);
            alert(err.message || 'Não foi possível ativar as notificações.');
        }
    }

    async function tentarRegistrarSePermitido() {
        if (!permissoesConcedidas() || !suportaPush()) {
            return;
        }
        await verificarRegistroServidor();
        if (registradoNoServidor) {
            atualizarToggleNav();
            renderizarBanner();
            return;
        }
        await concluirAtivacao();
    }

    function dispensarBanner() {
        localStorage.setItem(STORAGE_KEY, 'dismissed');
        esconderBanner();
        atualizarToggleNav();
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
        ativar: pedirPermissaoNoClique,
        dispensar: dispensarBanner,
        suportaPush: suportaPush,
    };

    document.addEventListener('DOMContentLoaded', async function() {
        const toggle = document.getElementById('helpdesk-push-toggle');
        if (toggle) {
            toggle.addEventListener('click', clicarToggleNav);
        }

        await sincronizarEstadoPermissao();
        await verificarRegistroServidor();
        renderizarBanner();
        abrirChamadoDaUrl();
        tentarRegistrarSePermitido();
    });

    document.addEventListener('visibilitychange', async function() {
        if (document.visibilityState === 'visible') {
            await sincronizarEstadoPermissao();
            await verificarRegistroServidor();
            renderizarBanner();
            tentarRegistrarSePermitido();
        }
    });
})();
