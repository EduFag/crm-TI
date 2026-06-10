---
name: ler-documentacao-pasta
description: Carrega DOCUMENTACAO.md da pasta do arquivo e da pasta pai antes de editar código no repositório branch-v2 (Django CRM TI). Use ao criar, alterar ou remover arquivos dentro do BASE_DIR ou subpastas, ou quando o usuário pedir contexto de módulo/pasta.
disable-model-invocation: false
---

# Ler documentação da pasta antes de editar

## Quando aplicar

**Antes** de criar, alterar ou excluir qualquer arquivo sob o `BASE_DIR` do projeto (raiz do repositório `branch-v2`), leia a documentação local. Não pule este passo mesmo em mudanças pequenas.

## Passo obrigatório

Para o arquivo alvo `caminho/arquivo.ext`:

1. **Pasta do arquivo** = diretório que contém o arquivo (`dirname`).
2. **Pasta pai** = diretório imediatamente acima da pasta do arquivo.

Leia **nesta ordem** (se existirem):

| Ordem | Caminho |
|-------|---------|
| 1 | `{pasta_do_arquivo}/DOCUMENTACAO.md` |
| 2 | `{pasta_pai}/DOCUMENTACAO.md` |

Use a ferramenta Read. Se um arquivo não existir, siga sem ele e mencione brevemente na resposta interna que não havia doc naquele nível.

## BASE_DIR

`BASE_DIR` = raiz do repositório (onde estão `manage.py` e `DOCUMENTACAO.md` da raiz).

- Arquivo na **raiz** (ex.: `manage.py`): leia apenas `DOCUMENTACAO.md` da raiz (não há pasta pai dentro do projeto).
- Arquivo em **subpasta** (ex.: `chips/views/management.py`): leia `chips/views/DOCUMENTACAO.md` e `chips/DOCUMENTACAO.md`.

## O que extrair da leitura

Ao ler os `.md`, priorize:

- Propósito da pasta e do módulo
- Papel de cada arquivo listado (especialmente o que você vai alterar)
- Convenções (rotas, modelos, partials HTMX, serviços)
- Links para subpastas relacionadas à mudança

Alinhe nomes, rotas e responsabilidades com o que está documentado. Se a mudança contradizer a doc, atualize o(s) `DOCUMENTACAO.md` afetado(s) no mesmo trabalho.

## Múltiplos arquivos

Se a tarefa tocar **várias pastas**, repita a leitura para **cada** pasta distinta envolvida (pasta do arquivo + pai de cada uma). Não reutilize contexto de uma pasta em outra sem reler.

## Após a edição

Se você criou pasta nova ou mudou o papel de arquivos, crie ou atualize `DOCUMENTACAO.md` na pasta afetada e, se necessário, na pasta pai.

## Exemplos

| Arquivo alvo | Ler primeiro | Ler depois |
|--------------|--------------|------------|
| `helpdesk/views/kanban.py` | `helpdesk/views/DOCUMENTACAO.md` | `helpdesk/DOCUMENTACAO.md` |
| `discador/services/blacklist.py` | `discador/services/DOCUMENTACAO.md` | `discador/DOCUMENTACAO.md` |
| `setup/settings.py` | `setup/DOCUMENTACAO.md` | `DOCUMENTACAO.md` (raiz) |
| `manage.py` | `DOCUMENTACAO.md` (raiz) | — |

## Resumo do fluxo

```
Arquivo alvo identificado
    → Read {pasta}/DOCUMENTACAO.md
    → Read {pasta_pai}/DOCUMENTACAO.md (se dentro do BASE_DIR)
    → Só então editar o código
    → Atualizar .md se a estrutura ou o papel dos arquivos mudou
```
