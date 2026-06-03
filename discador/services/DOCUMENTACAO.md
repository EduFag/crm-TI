# Documentação — `discador/services/`

Camada de **serviços** (lógica de negócio fora das views) do módulo discador.

## Para que serve

Encapsula chamadas à API 3C Plus, aplicação de regras de blacklist e processamento de arquivos CSV de campanha.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `api_3cplus.py` | `Api3CPlusService` — teste de conexão e busca de ligações por período/campanha (integração em evolução/TODOs). |
| `blacklist.py` | Regras para bloquear, ignorar ou monitorar qualificações; grava/atualiza registros em `Blacklist`. |
| `csv_processor.py` | Lê CSV de base de discagem, normaliza telefones, remove bloqueados/duplicados e gera arquivos reciclado/bloqueados. |
