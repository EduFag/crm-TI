"""Documentação da API externa CRM-TI (download para integração em Python)."""

from __future__ import annotations


def montar_documentacao_api_python(*, base_url: str, username: str = 'seu.usuario') -> str:
    """Gera Markdown passo a passo com exemplos em Python (requests)."""
    base = (base_url or '').rstrip('/')
    user = (username or 'seu.usuario').strip() or 'seu.usuario'

    return f"""# CRM-TI — Documentação da API externa (Python)

Guia passo a passo para integrar outro sistema em **Python** à API do CRM-TI (`/api/v1/`).

---

## 1. Pré-requisitos

1. Conta no CRM-TI com perfil **TI** (`IT_USER`), **staff** ou **superuser**.
2. Acesse **Integrações → Tokens API** e clique em **Gerar token**.
3. Copie o token **na hora** (ele só aparece uma vez). Guarde em variável de ambiente — nunca no código-fonte.
4. Anote seu **username** de login no CRM-TI.

Dependência Python:

```bash
pip install requests
```

---

## 2. Configuração sugerida

```python
import os
import requests

# URL base do CRM-TI (sem barra no final)
BASE_URL = os.environ.get("CRM_TI_BASE_URL", "{base}")

# Credenciais (NÃO versionar no git)
USERNAME = os.environ.get("CRM_TI_USERNAME", "{user}")
TOKEN = os.environ.get("CRM_TI_TOKEN", "cole_aqui_o_token_gerado")

session = requests.Session()
session.headers.update({{
    "Accept": "application/json",
    "Content-Type": "application/json",
}})
```

---

## 3. Passo 1 — Validar usuário + token

Endpoint: `POST {{BASE_URL}}/api/v1/auth/`

Corpo JSON: `username` + `token`.

```python
def autenticar() -> dict:
    url = f"{{BASE_URL}}/api/v1/auth/"
    resp = session.post(url, json={{
        "username": USERNAME,
        "token": TOKEN,
    }}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Falha na autenticação")
    print("Autenticado:", data["user"]["nome"], f"({{data['user']['username']}})")
    return data


# Exemplo de resposta:
# {{
#   "ok": true,
#   "user": {{"id": 1, "username": "{user}", "nome": "Nome Completo"}},
#   "token": {{"id": 1, "nome": "Integração X", "prefixo": "0bdd85f5"}}
# }}
```

---

## 4. Passo 2 — Chamar as demais APIs com Bearer

Nas rotas seguintes, envie o header:

`Authorization: Bearer <seu_token>`

O token identifica o usuário; não é necessário enviar username de novo.

```python
def headers_bearer() -> dict:
    return {{"Authorization": f"Bearer {{TOKEN}}"}}
```

---

## 5. Passo 3 — Listar ramais em uso (Discador)

Endpoint: `GET {{BASE_URL}}/api/v1/discador/ramais/`

Query params opcionais:

| Param   | Default  | Descrição                                      |
|---------|----------|------------------------------------------------|
| status  | IN_USE   | `IN_USE`, `FREE` ou `NOT_CONFIGURED`           |
| slug    | joytec   | Discador (ex.: joytec)                         |
| limit   | 200      | Máximo de itens (até 500)                      |

```python
def listar_ramais_em_uso(slug: str = "joytec", limit: int = 200) -> dict:
    url = f"{{BASE_URL}}/api/v1/discador/ramais/"
    resp = session.get(
        url,
        headers=headers_bearer(),
        params={{
            "status": "IN_USE",
            "slug": slug,
            "limit": limit,
        }},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Erro ao listar ramais")
    return data


resultado = listar_ramais_em_uso()
print(f"Discador: {{resultado['discador']}} — {{resultado['count']}} ramais")
for ramal in resultado["results"]:
    print(
        f"  Ramal {{ramal['numero']}} | "
        f"{{ramal.get('titular') or '—'}} | "
        f"login={{ramal.get('login_discador') or '—'}}"
    )
```

Campos principais de cada item em `results`:

- `numero` — número do ramal  
- `status` / `status_display` — situação  
- `titular` — nome de quem está usando  
- `login_discador` — login no discador  

---

## 6. Script completo (copiar e adaptar)

```python
#!/usr/bin/env python3
\"\"\"Exemplo de integração Python → CRM-TI API v1.\"\"\"

import os
import sys
import requests

BASE_URL = os.environ["CRM_TI_BASE_URL"].rstrip("/")
USERNAME = os.environ["CRM_TI_USERNAME"]
TOKEN = os.environ["CRM_TI_TOKEN"]


def main() -> int:
    # 1) Validar credenciais
    auth = requests.post(
        f"{{BASE_URL}}/api/v1/auth/",
        json={{"username": USERNAME, "token": TOKEN}},
        timeout=30,
    )
    auth.raise_for_status()
    auth_data = auth.json()
    if not auth_data.get("ok"):
        print("Auth falhou:", auth_data.get("error"), file=sys.stderr)
        return 1
    print("OK auth:", auth_data["user"]["nome"])

    # 2) Consultar ramais em uso
    ramais = requests.get(
        f"{{BASE_URL}}/api/v1/discador/ramais/",
        headers={{"Authorization": f"Bearer {{TOKEN}}"}},
        params={{"status": "IN_USE", "slug": "joytec"}},
        timeout=30,
    )
    ramais.raise_for_status()
    payload = ramais.json()
    if not payload.get("ok"):
        print("Ramais falhou:", payload.get("error"), file=sys.stderr)
        return 1

    print(f"Ramais em uso: {{payload['count']}}")
    for item in payload["results"]:
        print(f"- {{item['numero']}}: {{item.get('titular')}} / {{item.get('login_discador')}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Executar:

```bash
export CRM_TI_BASE_URL="{base}"
export CRM_TI_USERNAME="{user}"
export CRM_TI_TOKEN="seu_token_aqui"
python integrar_crm_ti.py
```

(No Windows PowerShell use `$env:CRM_TI_BASE_URL="..."` etc.)

---

## 7. Códigos de erro comuns

| HTTP | Significado                                      |
|------|--------------------------------------------------|
| 401  | Token ausente, inválido ou revogado              |
| 403  | Usuário sem permissão para API externa           |
| 404  | Discador (`slug`) não encontrado                 |
| 400  | Parâmetro inválido (ex.: `status` desconhecido)  |

Respostas de erro seguem o formato: `{{"ok": false, "error": "mensagem"}}`.

---

## 8. Segurança

- Revogue tokens em **Integrações → Tokens API** se vazarem.
- Prefira um token por sistema integrado (fácil de revogar isoladamente).
- Use HTTPS em produção.
- Não compartilhe o token em tickets, prints ou repositórios.

---

*Documento gerado pelo CRM-TI — Integrações → Tokens API.*
"""


def nome_arquivo_docs() -> str:
    return "crm-ti-api-python.md"
