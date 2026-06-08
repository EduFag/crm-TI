# Documentação — `core/migrations/`

Migrações Django do app **core**.

## Para que serve

Versiona alterações do modelo `CustomUser` no banco de dados. Não edite manualmente após aplicadas em produção; use novas migrações geradas pelo framework.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `0001_initial.py` | Criação inicial da tabela de usuário customizado (`CustomUser`) com campos de role e auditoria. |
| `0002_equipe.py` | Modelo `Equipe` e FK `equipe` em `CustomUser`. |
