# Documentação — `emails/`

App de **inventário de contas de e-mail corporativas** e domínios permitidos.

## Para que serve

Cadastrar domínios (`@empresa.com.br`), contas (usuário + domínio + funcionário), alternar status ativo/bloqueado e registrar reset de senha.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app. |
| `models.py` | `EmailDomain` e `EmailAccount` (propriedade `address`). |
| `views.py` | Dashboard, CRUD completo de contas e domínios (Create, Update, Delete), reset de senha, visualizar senha com trava de segurança, e toggle de status (Inativar/Ativar). |
| `audit.py` | Registro de ações em `RegistroAcao` (core). |
| `urls.py` | Rotas sob `/emails/`. |
| `admin.py` | Administração no Django Admin. |
| `tests.py` | Testes. |
| `migrations/` | Schema. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Telas web. Ver `templates/DOCUMENTACAO.md`. |
