# Documentação — `operadores`

Módulo responsável pela gestão da estrutura física e de atendimento (Setores, Ilhas, PAs), cadastro de Operadores e suas Contas de WhatsApp Business. 
Integra-se com o módulo de `chips` para rastrear o uso das linhas vinculadas às contas de WhatsApp.

## Arquivos e Pastas

| Arquivo / Pasta | Função |
|-----------------|--------|
| `models.py` | Modelos de banco de dados: `Setor`, `Ilha`, `PA`, `Operador`, e `WhatsAppAccount`. Contém lógicas de sinais/save para sincronização com o chip. |
| `urls.py` | Rotas do módulo (`/operadores/...`). |
| `views.py` | Views (Class-Based) para dashboard, listagem e gestão dos operadores. |
| `forms.py` | Formulários para cadastro de operadores e contas WhatsApp. |
| `templates/operadores/` | Templates do módulo. |

## Regras de Negócio e Integração

1. **Conta WhatsApp e Chips**: Quando um `WhatsAppAccount` é criado ou editado, e associado a um `Operador` com um `Chip` vinculado, o status de uso desse `Chip` é automaticamente atualizado para `IN_USE` no módulo de `chips`. Ao remover o vínculo, o chip retorna para `AVAILABLE`.
2. **Estrutura de Posições**:
   - **Setores**: Agrupamentos maiores (ex: INSS, LOJA, SIAPE).
   - **Ilhas**: Subgrupos dentro de um setor.
   - **PAs**: Posições de atendimento (mesas físicas) associadas a uma Ilha.
   - **Operadores**: Pessoas que ocupam uma PA.
