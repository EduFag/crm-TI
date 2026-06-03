# Documentação — `equipment/`

App de **patrimônio e ciclo de vida de equipamentos de TI** (notebooks, desktops, monitores, etc.).

## Para que serve

Cadastro de ativos com tag de patrimônio, série, garantia, valor de compra, status (disponível, em uso, manutenção, sucata) e log imutável de movimentações (RF02, RF04, RF05).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `apps.py` | Configuração do app. |
| `models.py` | `Equipment` e `EquipmentLog` (ações: atribuição, devolução, manutenção, sucateamento, criação). |
| `views.py` | `DashboardView`, `EquipmentCreateView`, `EquipmentUpdateView`. |
| `urls.py` | Rotas sob `/equipment/`. |
| `admin.py` | Administração no Django Admin. |
| `tests.py` | Testes. |
| `migrations/` | Schema. Ver `migrations/DOCUMENTACAO.md`. |
| `templates/` | Interface. Ver `templates/DOCUMENTACAO.md`. |
