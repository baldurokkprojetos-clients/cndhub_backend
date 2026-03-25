-- Migration inicial do schema do banco de dados
-- Criação das tabelas base (Hubs, Usuarios, Clientes, Tipos de Certidoes, etc)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Hubs (Tenant Principal)
CREATE TABLE IF NOT EXISTS hubs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(50),
    senha_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('master', 'admin', 'cliente')),
    hub_id UUID REFERENCES hubs(id) ON DELETE CASCADE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hub_id UUID REFERENCES hubs(id) ON DELETE CASCADE,
    cnpj VARCHAR(20) NOT NULL,
    razao_social VARCHAR(255) NOT NULL,
    telefone VARCHAR(50),
    email VARCHAR(255),
    responsavel VARCHAR(255),
    api_key VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para busca rápida de cliente por CNPJ
CREATE INDEX IF NOT EXISTS idx_clientes_cnpj ON clientes(cnpj);

-- Relacionamento N:N Usuário <-> Cliente
CREATE TABLE IF NOT EXISTS usuarios_clientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    UNIQUE(usuario_id, cliente_id)
);

-- Tipos de Certidões (Base Modular)
CREATE TABLE IF NOT EXISTS tipo_certidoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    url TEXT,
    possui_captcha BOOLEAN DEFAULT FALSE,
    tipo_captcha VARCHAR(50) DEFAULT 'none' CHECK (tipo_captcha IN ('none', 'simple', 'recaptcha', 'cloudflare')),
    scraper_module VARCHAR(255) NOT NULL, -- NOME DO MÓDULO NO WORKER (ex: 'receita_federal', 'prefeitura_goiania')
    ativo BOOLEAN DEFAULT TRUE
);

-- Vínculo Cliente <-> Tipo Certidão (Quais certidões o cliente precisa)
CREATE TABLE IF NOT EXISTS clientes_tipo_certidoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_certidao_id UUID REFERENCES tipo_certidoes(id) ON DELETE CASCADE,
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(cliente_id, tipo_certidao_id)
);

-- Certidões Geradas/Histórico
CREATE TABLE IF NOT EXISTS certidoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    tipo_certidao_id UUID REFERENCES tipo_certidoes(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'error', 'completed')),
    caminho_arquivo TEXT,
    tentativa INT DEFAULT 0,
    mensagem_erro TEXT,
    worker_id VARCHAR(255),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cliente_id, tipo_certidao_id)
);

-- Jobs Engine (Fila de Processamento)
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('criar_pasta', 'emitir_certidao')),
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    certidao_id UUID REFERENCES certidoes(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'error', 'completed')),
    tentativas INT DEFAULT 0,
    locked_by VARCHAR(255),
    locked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Logs do Worker
CREATE TABLE IF NOT EXISTS logs_worker (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id VARCHAR(255),
    mensagem TEXT,
    nivel VARCHAR(50) CHECK (nivel IN ('info', 'warning', 'error')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
