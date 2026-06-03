# Documentação — `emails/migrations/`

Migrações Django do app **emails**.

## Para que serve

Evolui o modelo de domínios e contas de e-mail no banco.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `0001_initial.py` | Estrutura inicial (incluía `MailLog`, posteriormente removido). |
| `0002_emaildomain_delete_maillog_emailaccount_username_and_more.py` | Introduz `EmailDomain`, ajusta `EmailAccount` com `username` e domínio FK; remove `MailLog`. |
