# Documentação — `discador/utils/`

Utilitários compartilhados do módulo **discador**.

## Para que serve

Funções puras de normalização usadas na importação API, blacklist e processamento CSV para comparar números de forma consistente.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `phones.py` | `normalizar_telefone()` — remove máscara, DDI 55 e zeros extras; `normalizar_cpf()` — apenas dígitos do CPF. |
