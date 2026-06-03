# Documentação — `discador/templates/discador/`

Templates HTML do módulo **discador**.

## Para que serve

Telas operacionais do integrador 3C Plus e gestão de blacklist/bases.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `base_discador.html` | Layout base específico do módulo (menu discador). |
| `dashboard.html` | Resumo e atalhos (`/discador/dashboard/`). |
| `configuracoes_api.html` | Cadastro de `ConfiguracaoAPI` (URL, token, campanhas). |
| `atualizar_blacklist.html` | Disparo de importação da API para atualizar blacklist. |
| `regras_reciclagem.html` | CRUD visual de `RegraReciclagem`. |
| `reciclar_bases.html` | Upload e processamento de CSV de campanha. |
| `blacklist.html` | Consulta da blacklist ativa. |
| `consulta_telefone.html` | Verifica se um número está bloqueado. |
| `historico_importacoes.html` | Lista de `ImportacaoAPI`. |
| `historico_processamentos.html` | Lista de `ProcessamentoBase` (CSVs processados). |
