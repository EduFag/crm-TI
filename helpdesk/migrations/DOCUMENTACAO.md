# Documentação — `helpdesk/migrations/`

Migrações Django do app **helpdesk**.

## Para que serve

Versiona tabelas `Ticket` e `Comment` e campos adicionais (ex.: arquivamento).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `0001_initial.py` | Criação de tickets e comentários. |
| `0002_ticket_is_archived.py` | Campo `is_archived` para ocultar chamados resolvidos antigos do Kanban ativo. |
