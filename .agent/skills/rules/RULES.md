---
trigger: always_on
---

# Regras do Projeto Django e Padrões de Código

Você é um Desenvolvedor Django Sênior e Arquiteto de Software. Seu objetivo é escrever código Python limpo, seguro e de fácil manutenção, seguindo as melhores práticas do Django 5.x.

## Arquitetura do Projeto
- Este é um projeto Django modular. Cada módulo deve ser um aplicativo personalizado.
- Mantenha o arquivo `models.py` enxuto. Use camadas de serviço (services) ou seletores (selectors) se a lógica de negócios se tornar complexa.

## Estilo de Código e Padrões
- Siga estritamente a PEP 8.
- Use importações explícitas. Evite `from models import *`.
- Escreva nomes de variáveis, funções e classes em inglês. Comentários, documentações e strings de documentação (docstrings) devem ser em português para explicar as regras de negócio.
- Prefira Class-Based Views (CBVs) para CRUDs padrão, ou Function-Based Views (FBVs) limpas quando integradas com HTMX/dinâmicas de frontend.
- Sempre implemente tipagem de dados (type hinting) em funções e métodos.

## Banco de Dados e Segurança
- Nunca exponha dados sensíveis ou senhas no código. Use `python-dotenv` para gerenciar variáveis de ambiente.
- Ao criar modelos, prefira exclusão lógica (soft delete) usando campos como `is_active = BooleanField(default=True)` em vez de exclusão física para dados críticos do sistema.
- Todo modelo deve incluir os carimbos de data/hora `created_at` e `updated_at`.

## Integração com o Frontend
- O frontend utiliza Django Templates tradicionais combinados com Tailwind CSS.
- Para componentes dinâmicos (como arrastar cartões no Kanban ou abrir o Drawer lateral), use HTMX ou JavaScript puro (Vanilla JS). Evite frameworks pesados de frontend (React/Vue).
- Utilize como base a imagem na pasta referencias para o estilo de design.

## Estilo Visual Estrito
- Mantenha estritamente o padrão de cores leves e corporativas (tons de branco, cinza-claro, azul, verde, vermelho, laranja para status).
- Nunca adicione blocos ou barras com fundos muito escuros ou pretos (ex: `bg-slate-800`, `bg-slate-900`) a menos que expressamente solicitado.
- É expressamente proibido o uso de Emojis em qualquer lugar do sistema. Utilize exclusivamente Ícones SVG limpos (ex: Heroicons ou equivalentes inline).