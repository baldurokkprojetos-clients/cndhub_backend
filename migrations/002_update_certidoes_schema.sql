-- Migration 002: Atualizar tabela certidoes para ter criado_em, atualizado_em e unicidade

-- Renomear colunas existentes
ALTER TABLE certidoes RENAME COLUMN created_at TO criado_em;
ALTER TABLE certidoes RENAME COLUMN updated_at TO atualizado_em;

-- Adicionar constraint de unicidade para cliente_id e tipo_certidao_id
-- Somente será mantido 1 certidão por tipo por cliente
ALTER TABLE certidoes ADD CONSTRAINT uq_cliente_tipo_certidao UNIQUE (cliente_id, tipo_certidao_id);
