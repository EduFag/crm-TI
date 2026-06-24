-- =============================================================================
-- PostgreSQL — CRM TI
-- Executar como superusuário:  psql -U postgres -f postgres-setup.sql
-- Altere a senha antes de usar em produção.
-- =============================================================================

CREATE USER crm_ti WITH PASSWORD 'altere_esta_senha';

CREATE DATABASE crm_ti
    OWNER crm_ti
    ENCODING 'UTF8'
    TEMPLATE template0;

GRANT ALL PRIVILEGES ON DATABASE crm_ti TO crm_ti;

-- Após criar o banco, conecte em crm_ti e rode as migrações Django no projeto.
