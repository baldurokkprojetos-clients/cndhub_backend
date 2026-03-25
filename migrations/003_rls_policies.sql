-- 003_rls_policies.sql
-- Habilitar Row Level Security (RLS) nas tabelas principais para isolamento de dados de usuários clientes

-- 1. Habilitar RLS nas tabelas
ALTER TABLE hubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE certidoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- 2. Criar políticas para 'clientes'
-- Um usuário master/admin do hub vê todos os clientes do hub.
-- Um usuário com role 'cliente' só vê o cliente ao qual está vinculado via usuarios_clientes.

-- Política: Usuários podem ver clientes do seu hub (se for admin) ou clientes específicos (se for cliente)
-- Como o Supabase injeta o user_id no auth.uid(), podemos usar isso se estivermos usando Supabase Auth.
-- Se for uma API customizada (FastAPI com JWT), as políticas RLS podem depender de current_setting('request.jwt.claims', true).

-- Nota: Como o backend atual usa FastAPI sem integração nativa com Supabase Auth (ainda não implementado o auth.py),
-- deixamos as políticas RLS preparadas para o JWT do Supabase ou uma role de banco de dados (service_role ignora RLS).

-- Permitir tudo para a role de serviço (backend FastAPI rodando com a service key)
-- O backend atua como "admin" do banco, e o RLS será aplicado se as requisições frontend
-- forem feitas diretamente ao Supabase, ou se o backend usar o JWT do usuário logado (impersonation).

CREATE POLICY "Service role tem acesso total a clientes" ON clientes
FOR ALL USING (current_user = 'postgres' OR current_setting('request.jwt.claim.role', true) = 'service_role');

CREATE POLICY "Service role tem acesso total a certidoes" ON certidoes
FOR ALL USING (current_user = 'postgres' OR current_setting('request.jwt.claim.role', true) = 'service_role');

CREATE POLICY "Service role tem acesso total a jobs" ON jobs
FOR ALL USING (current_user = 'postgres' OR current_setting('request.jwt.claim.role', true) = 'service_role');

-- Exemplo de política para usuário final (cliente):
-- CREATE POLICY "Cliente vê suas próprias certidões" ON certidoes
-- FOR SELECT USING (cliente_id IN (
--    SELECT cliente_id FROM usuarios_clientes WHERE usuario_id = auth.uid()
-- ));
