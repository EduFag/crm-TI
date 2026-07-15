# Notificações Web Push — guia de implementação

Este documento descreve como implementar notificações nativas do navegador (Web Push) em um sistema Django, com base na implementação do helpdesk deste projeto e nos problemas reais encontrados em produção.

## O que você vai ter no final

- Popup nativo do Chrome pedindo permissão ao usuário (no clique de um botão).
- Notificações do Windows/macOS mesmo com o navegador minimizado ou aba em background.
- Envio pelo servidor quando ocorrem eventos (comentário, mudança de coluna, prioridade, etc.).
- Inscrições salvas no banco por usuário/dispositivo.

## Arquitetura

```
[Evento no Django] → notifications.py → pywebpush → FCM/Mozilla push service
                                                          ↓
[Service Worker sw.js] ← push do browser ← endpoint da subscription
        ↓
showNotification() → toast do Windows/Chrome
```

Componentes principais neste repositório:

| Camada | Arquivo |
|--------|---------|
| Model | `helpdesk/models.py` → `PushSubscription` |
| Envio | `helpdesk/notifications.py` |
| API | `helpdesk/views/push.py` |
| Rotas | `helpdesk/urls.py` |
| Service Worker | `helpdesk/static/helpdesk/sw.js` |
| Frontend | `helpdesk/static/helpdesk/push.js` |
| UI | `helpdesk/templates/helpdesk/_push_banner.html`, `_nav.html` |
| Config | `setup/settings.py`, `.env` |

---

## Pré-requisitos

1. **HTTPS** em produção (ou `localhost` em dev).
2. Python: `pywebpush` no `requirements.txt`.
3. Chaves **VAPID** (identidade do servidor perante os push services do Chrome/Firefox).

### Gerar chaves VAPID na VPS

```bash
source venv/bin/activate
python -m py_vapid --applicationServerKey
# Gera private_key.pem e public_key.pem
```

### Variáveis no `.env`

```env
VAPID_PUBLIC_KEY=BGNx...   # chave pública (base64 url-safe)
VAPID_PRIVATE_KEY=/caminho/para/private_key.pem   # caminho OU conteúdo PEM
VAPID_ADMIN_EMAIL=mailto:ti@suaempresa.com.br
```

Permissão do arquivo PEM para o usuário do Gunicorn:

```bash
chown edufa:edufa /home/edufa/crm-TI/private_key.pem
chmod 600 /home/edufa/crm-TI/private_key.pem
```

No `settings.py`, carregue a chave privada de arquivo se necessário:

```python
def _carregar_vapid_private_key(valor: str) -> str:
    valor = (valor or '').strip()
    if not valor:
        return ''
    caminho = Path(valor)
    if caminho.is_file():
        return caminho.read_text(encoding='utf-8').strip()
    return valor

VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '').strip()
VAPID_PRIVATE_KEY = _carregar_vapid_private_key(os.environ.get('VAPID_PRIVATE_KEY', ''))
VAPID_ADMIN_EMAIL = os.environ.get('VAPID_ADMIN_EMAIL', 'mailto:ti@localhost')
```

---

## Passo 1 — Model no banco

```python
class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Rodar migration no servidor após deploy.

---

## Passo 2 — Endpoints da API

| Método | URL | Função |
|--------|-----|--------|
| GET | `/helpdesk/push/vapid-public-key/` | Retorna `{ publicKey }` |
| GET | `/helpdesk/push/status/` | Retorna se o usuário já tem subscription ativa |
| POST | `/helpdesk/push/subscribe/` | Salva subscription JSON do browser |
| POST | `/helpdesk/push/unsubscribe/` | Desativa subscription |
| GET | `/helpdesk/sw.js` | **Service Worker** (ver seção crítica abaixo) |

Todos os endpoints de push (exceto `sw.js`) exigem usuário autenticado e permissão no módulo.

---

## Passo 3 — Service Worker (`sw.js`)

O SW escuta eventos `push` e chama `showNotification()`:

```javascript
self.addEventListener('push', function(event) {
    const payload = event.data.json();
    event.waitUntil(
        self.registration.showNotification(payload.title, {
            body: payload.body,
            tag: payload.tag,
            renotify: true,  // importante — ver "Erros comuns"
            data: { url: payload.url },
        })
    );
});
```

### ⚠️ Erro crítico #1 — escopo do Service Worker

**Problema:** registrar o SW em `/static/helpdesk/sw.js` com escopo `/helpdesk/` **falha** no Chrome. Arquivos em `/static/` não controlam URLs em `/helpdesk/`.

**Sintoma:** alerta *"Verifique se o servidor está configurado com chaves VAPID"* ou falha silenciosa no `pushManager.subscribe()`.

**Solução:** servir o SW via Django em `/helpdesk/sw.js`:

```python
# helpdesk/views/push.py
@cache_control(max_age=0, no_cache=True, must_revalidate=True)
@require_http_methods(['GET', 'HEAD'])
def service_worker_js(request):
    caminho = finders.find('helpdesk/sw.js')
    resposta = HttpResponse(conteudo, content_type='application/javascript; charset=utf-8')
    resposta['Service-Worker-Allowed'] = '/helpdesk/'
    return resposta
```

No frontend:

```javascript
navigator.serviceWorker.register('/helpdesk/sw.js', { scope: '/helpdesk/' });
```

**Teste na VPS:**

```bash
curl -s https://seu-dominio/helpdesk/sw.js | head -3
# Deve retornar JavaScript, não HTML de login
```

`curl -I` envia HEAD — alguns setups retornam 405; use `curl -s` (GET).

---

## Passo 4 — Frontend (`push.js`)

### Fluxo correto de permissão

1. Usuário clica no toggle/botão (**gesto obrigatório**).
2. Chama `Notification.requestPermission()` **imediatamente** — sem `await`, DOM ou `alert()` antes.
3. Se `granted` → registra SW → `pushManager.subscribe()` → POST `/push/subscribe/`.

```javascript
function pedirPermissaoNoClique() {
    if (Notification.permission === 'granted') {
        concluirAtivacao();
        return;
    }
    // Sem await/DOM antes — preserva o gesto do usuário
    Notification.requestPermission().then(tratarResultadoPermissao);
}
```

### ⚠️ Erro crítico #2 — permissão `denied` vs `default`

| Estado Chrome | `Notification.permission` | O que acontece ao clicar "Ativar" |
|---------------|---------------------------|-----------------------------------|
| Sem permissão (padrão) | `default` | Abre popup nativo do Chrome |
| Bloqueado | `denied` | **Nada** — retorna `denied` na hora |

**Não existe API** para abrir as configurações do navegador por código. O usuário deve ir manualmente: cadeado → Notificações → **Redefinir permissão**.

Use a Permissions API para distinguir estados na UI:

```javascript
const status = await navigator.permissions.query({ name: 'notifications' });
// status.state: 'prompt' | 'granted' | 'denied'
```

### ⚠️ Erro crítico #3 — toggle travado

**Problema:** permissão `granted` no browser, mas subscription não salva no banco → toggle ficava verde e desabilitado.

**Solução:** consultar `GET /push/status/` e, se browser permitiu mas servidor não tem registro, mostrar **"Sincronizar notificações"** e permitir novo clique.

### CSRF no POST subscribe

Inclua token no template:

```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

E no fetch:

```javascript
headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
```

---

## Passo 5 — Envio pelo servidor

```python
from pywebpush import webpush, WebPushException

payload = json.dumps({
    'title': 'Chamado movido: #42',
    'body': 'Título do chamado\nMovido para Em Atendimento.',
    'url': '/helpdesk/?ticket=42',
    'tag': f'helpdesk-42-STATUS_CHANGED-{int(time.time() * 1000)}',
})

webpush(
    subscription_info={
        'endpoint': sub.endpoint,
        'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
    },
    data=payload,
    vapid_private_key=settings.VAPID_PRIVATE_KEY,
    vapid_claims={'sub': settings.VAPID_ADMIN_EMAIL},
)
```

Dispare após commit da transação:

```python
transaction.on_commit(lambda: notificar_evento_chamado(ticket, actor, tipo, mensagem))
```

### ⚠️ Erro crítico #4 — mesma `tag` = sem toast novo

**Problema:** usar sempre `tag: helpdesk-ticket-123` faz o Chrome/Windows **substituir** a notificação anterior sem exibir novo banner. Parece que "parou de notificar".

**Solução:** tag única por evento + `renotify: true` no SW:

```python
tag = f'helpdesk-{ticket.pk}-{tipo}-{int(time.time() * 1000)}'
```

---

## Passo 6 — Disparar nos eventos de negócio

Exemplo no Kanban ao mover coluna:

```python
if status_anterior != new_status:
    agendar_notificacao_chamado(
        ticket,
        request.user,
        EVENTO_STATUS_CHANGED,
        f'Movido para {novo_status}.',
    )
```

Destinatários típicos (exceto quem fez a ação):

- Criador do chamado
- Solicitante
- Responsável (`assigned_to`)
- Co-autores

---

## Passo 7 — Deploy em produção

Checklist após cada `git pull`:

```bash
python manage.py migrate          # se houver migrations novas
python manage.py collectstatic --noinput   # push.js e sw.js
sudo systemctl restart crm-ti
```

**Problema comum:** `git pull` manual sem `collectstatic` → browser usa JS antigo de `staticfiles/`.

Confirme que copiou:

```
1 static file copied to '.../staticfiles'
```

### Verificações rápidas na VPS

```bash
# Chaves VAPID carregadas
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()
from django.conf import settings
print('PUBLIC:', bool(settings.VAPID_PUBLIC_KEY))
print('PRIVATE:', len(settings.VAPID_PRIVATE_KEY), 'chars')
"

# Subscriptions ativas
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()
from helpdesk.models import PushSubscription
print('Ativas:', PushSubscription.objects.filter(is_active=True).count())
"
```

`PRIVATE` deve ter centenas de caracteres (conteúdo PEM), não ~30 (só o caminho do arquivo).

---

## Passo 8 — Configurar Windows 11 + Chrome

### Windows

Configurações → Sistema → Notificações → ligar **Notificações** → **Google Chrome** permitido.

### Chrome

1. `chrome://settings/content/notifications` → sites podem pedir permissão.
2. No site: toggle **Notificações** no helpdesk → aceitar popup.
3. Confirmar toggle verde: **Notificações ativas**.

Se bloqueou antes: cadeado na URL → Notificações → **Redefinir permissão** → recarregar com Ctrl+F5.

### Atualizar Service Worker após deploy

Chrome pode cachear o SW. Opções:

- Ctrl+F5 no helpdesk
- `chrome://serviceworker-internals` → Unregister → recarregar

---

## Erros comuns — resumo

| Sintoma | Causa | Correção |
|---------|-------|----------|
| Popup nativo não abre | Permissão `denied` ou gesto perdido antes de `requestPermission()` | Redefinir permissão; chamar API no clique direto |
| Alerta genérico VAPID | SW em `/static/` com escopo `/helpdesk/` | Servir SW em `/helpdesk/sw.js` |
| `PRIVATE: 30 chars` | `.pem` não lido, só caminho na string | `_carregar_vapid_private_key()` + permissão do arquivo |
| Subscription 0 no banco | JS antigo / toggle travado / CSRF | `collectstatic`, meta CSRF, endpoint `/push/status/` |
| Primeira notificação OK, depois nada | Mesma `tag` no mesmo chamado | Tag única + `renotify: true` |
| `curl -I sw.js` → 405 | HEAD não permitido | Testar com `curl -s` (GET) |
| Push para endpoint 410 | Subscription expirou | Marcar `is_active=False` e pedir reativar no browser |

---

## Checklist de implementação do zero

- [ ] `pywebpush` instalado
- [ ] Chaves VAPID no `.env` + email `mailto:` ou `https:`
- [ ] Model `PushSubscription` + migration
- [ ] Views: vapid-key, subscribe, unsubscribe, status, **sw.js**
- [ ] `notifications.py` com envio e tags únicas
- [ ] `sw.js` com `push` + `notificationclick` + `renotify`
- [ ] `push.js` com gesto de usuário, CSRF, sync browser↔servidor
- [ ] UI: banner + toggle na nav
- [ ] Hooks nos eventos de negócio (`agendar_notificacao_chamado`)
- [ ] HTTPS em produção
- [ ] Deploy: migrate + collectstatic + restart
- [ ] Teste: 2 usuários, mover chamado 3x, comentar — 4 toasts distintos

---

## Referências

- [MDN — Notifications API](https://developer.mozilla.org/pt-BR/docs/Web/API/Notifications_API)
- [MDN — Push API](https://developer.mozilla.org/pt-BR/docs/Web/API/Push_API)
- [MDN — Service Worker API](https://developer.mozilla.org/pt-BR/docs/Web/API/Service_Worker_API)
- [pywebpush](https://github.com/web-push-libs/pywebpush)
