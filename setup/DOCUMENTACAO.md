# Documentação — `setup/`

Pacote de **configuração do projeto Django** (antigo `startproject`). Não contém regras de negócio; apenas wiring global.

## Para que serve

Define apps instalados, banco, templates, `AUTH_USER_MODEL`, URLs raiz e pontos de deploy (WSGI/ASGI).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `settings.py` | Configurações: `INSTALLED_APPS` (core, helpdesk, chips, emails, equipment, discador), SQLite, `CustomUser`, mídia estática, etc. `BASE_DIR` aponta para a raiz do repositório. |
| `urls.py` | Roteamento global: admin, `core`, e `include()` de cada app. Em `DEBUG`, serve arquivos de mídia. |
| `wsgi.py` | Entrada WSGI para servidores de produção. |
| `asgi.py` | Entrada ASGI (async/WebSockets, se usado no futuro). |

## Apps registrados em `settings.py`

`core`, `helpdesk`, `chips`, `emails`, `equipment`, `discador` + apps padrão do Django (`admin`, `auth`, `sessions`, etc.).
