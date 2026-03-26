-- Migration 005: Índices de Performance

CREATE INDEX IF NOT EXISTS idx_jobs_status_created_at ON jobs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clientes_hub_id ON clientes(hub_id);
