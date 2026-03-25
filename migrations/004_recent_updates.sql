-- Migration 004: Atualizações Recentes (Tabelas de Associação, Certidões e Configurações)

-- 1. Criação das tabelas associativas N:N corretas (sem coluna ID própria)
CREATE TABLE IF NOT EXISTS usuario_hubs (
    usuario_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    hub_id UUID REFERENCES hubs(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, hub_id)
);

CREATE TABLE IF NOT EXISTS usuario_clientes (
    usuario_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, cliente_id)
);

-- 2. Adição da coluna cliente_id na tabela usuarios (para compatibilidade/referência direta)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cliente_id UUID REFERENCES clientes(id) ON DELETE SET NULL;

-- 3. Remoção da tabela obsoleta e duplicada (que possuía ID próprio e o nome no plural)
DROP TABLE IF EXISTS usuarios_clientes;

-- 4. Adição da coluna de conteúdo de arquivo na tabela certidoes para armazenamento direto no DB
ALTER TABLE certidoes ADD COLUMN IF NOT EXISTS arquivo_conteudo BYTEA;

-- 5. Criação da tabela de configurações (para parâmetros globais do sistema)
CREATE TABLE IF NOT EXISTS configuracoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descricao VARCHAR(255),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices de otimização para as novas colunas
CREATE INDEX IF NOT EXISTS idx_configuracoes_chave ON configuracoes(chave);
