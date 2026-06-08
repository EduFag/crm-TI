# Documentação — `chips/migrations/`

Migrações Django do app **chips**.

## Para que serve

Persiste no banco as tabelas de operadoras, lotes, chips, movimentações e recargas.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `0001_initial.py` | Criação das tabelas iniciais do módulo de chips. |
| `0002_chip_custody_batch_envelope.py` | Custódia (`WITH_TI`/`WITH_PERSON`), envelopes, transferências e `employee_user`. |
