# Instalar PostgreSQL na VPS (Ubuntu / Debian)

Guia do zero: instalar o servidor, criar usuário/banco `crm_ti` e conferir conexão.

> **Importante:** no `.env`, **uma variável por linha**. Errado: `DB_ENGINE=postgresqlDB_NAME=crm_ti`  
> Certo:
> ```
> DB_ENGINE=postgresql
> DB_NAME=crm_ti
> ```

---

## 1. Atualizar o sistema

```bash
sudo apt update
sudo apt upgrade -y
```

---

## 2. Instalar PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
```

Verificar se está rodando:

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl status postgresql
```

Versão instalada:

```bash
psql --version
```

---

## 3. Criar usuário e banco (CRM TI)

Substitua `SUA_SENHA_FORTE` pela mesma senha do `DB_PASSWORD` no `.env`.

**Opção A — comando direto:**

```bash
sudo -u postgres psql -c "CREATE USER crm_ti WITH PASSWORD 'SUA_SENHA_FORTE';"
sudo -u postgres psql -c "CREATE DATABASE crm_ti OWNER crm_ti ENCODING 'UTF8' TEMPLATE template0;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crm_ti TO crm_ti;"
```

**Opção B — script do projeto** (edite a senha no arquivo antes):

```bash
cd /var/www/branch-v2
sudo -u postgres psql -f .vps/postgres-setup.sql
```

Se o usuário/banco já existir, o comando falha — use só em instalação nova.

---

## 4. Permitir login com senha (localhost)

O Django na mesma VPS conecta em `127.0.0.1`. Confira `pg_hba.conf`:

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Deve existir linha parecida com (para IPv4 local):

```
host    all    all    127.0.0.1/32    scram-sha-256
```

Ou para conexões locais via socket:

```
local   all    all                    peer
host    all    all    127.0.0.1/32    scram-sha-256
```

Reinicie o Postgres:

```bash
sudo systemctl restart postgresql
```

---

## 5. Testar conexão

```bash
psql -h 127.0.0.1 -U crm_ti -d crm_ti -W
```

Digite a senha. Se entrar no prompt `crm_ti=>`, está ok. Saia com `\q`.

---

## 6. `.env` na VPS (exemplo)

Arquivo na raiz do projeto, **cada chave em uma linha**:

```env
DB_ENGINE=postgresql
DB_NAME=crm_ti
DB_USER=crm_ti
DB_PASSWORD=SUA_SENHA_FORTE
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=600
DB_SSLMODE=prefer
```

---

## 7. Firewall (opcional)

Postgres só na VPS local — **não** abra a porta 5432 na internet se o Django roda no mesmo servidor:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## 8. Próximos passos (no projeto Django)

No servidor, com venv ativo e `.env` configurado:

1. `pip install -r requirements.txt`
2. Rodar migrações Django
3. Criar superusuário
4. `collectstatic` (produção)

---

## Problemas comuns

| Erro | Solução |
|------|---------|
| `peer authentication failed` | Use `-h 127.0.0.1` ou ajuste `pg_hba.conf` para `scram-sha-256` |
| `password authentication failed` | Senha diferente entre `.env` e `CREATE USER` |
| `database "crm_ti" does not exist` | Rode os comandos CREATE DATABASE |
| Variáveis coladas no `.env` | Uma variável por linha; reinicie gunicorn após corrigir |

---

## Desinstalar (só se necessário)

```bash
sudo apt remove --purge -y postgresql postgresql-contrib
sudo apt autoremove -y
```

Isso apaga os dados — use apenas em ambiente de teste.
