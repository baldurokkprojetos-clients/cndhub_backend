# Fluxo do Worker

O Worker atua como um sistema de RPA (Robotic Process Automation) que busca tarefas (jobs) pendentes na API do backend e as executa utilizando automadores específicos para cada tipo de certidão.

## Etapas do Fluxo

1. **Busca de Jobs Pendentes (`get_pending_jobs`)**
   - O Worker faz um GET na rota `/api/v1/jobs/pending` do backend conforme o `POLLING_INTERVAL` definido no `.env` (padrão 1s).
   - Retorna uma lista de jobs contendo: `job_id`, `tipo_certidao_id`, `cnpj`, `razao_social`, `automator_module`, entre outros dados.

2. **Inicialização do Automador (`process_job`)**
   - Para cada job retornado, o Worker verifica qual é o módulo automador responsável (`automator_module`).
   - Carrega o módulo através da factory `get_automator`.
   - Passa os parâmetros: `cliente_id`, `tipo_certidao_id`, `cnpj`, e `razao_social`.

3. **Execução (`automator.execute()`)**
   - A classe específica do automador executa o scraping e download.
   - O automador retorna um dicionário contendo o `status` ("completed" ou "error"), o `caminho_arquivo` (se baixado com sucesso), e a `mensagem_erro` (se houver).

4. **Atualização no Backend (`update_certidao_via_api` e `update_job_status`)**
   - O Worker envia o PDF (como `multipart/form-data`) ou o status para `/api/v1/certidoes/upsert`.
   - Em seguida, atualiza o status do job em `/api/v1/jobs/{job_id}/status`.

## Padrão de Arquivos
- Todos os PDFs baixados seguem o padrão de nomenclatura: `[CNPJ_SOMENTE_NUMEROS]_[NOME_AUTOMADOR]_[DATA_YYYYMMDD].pdf`.
- Os arquivos antigos do mesmo cliente e tipo são removidos do diretório local para evitar acúmulo de disco.
- O diretório base de download é controlado por `BASE_CERTIDOES_PATH` no `.env` (padrão `C:/CERTIDOES`).

## Configurações via .env
- `API_BASE_URL` (ou `BACKEND_URL` como fallback)
- `HUB_API_KEY`
- `WORKER_ID`
- `POLLING_INTERVAL`
- `MAX_RETRIES`
- `BASE_CERTIDOES_PATH`

## Marcadores de Logs (Tracking & Troubleshoot)
Para facilitar a identificação de falhas e melhorias futuras, o Worker utiliza marcadores nos logs:
- `[INICIO]` / `[FIM]`: Marca o início e o fim da execução de um automador para um job.
- `[FALHA]`: Indica que ocorreu um erro (exceções, timeouts) e o motivo da falha.
- `[RETRY]`: Indica que o job falhou e está sujeito a retentativas (até 3 tentativas).
- `[FATAL]`: Erro irrecuperável que esgota imediatamente as tentativas (ex: "CNPJ Inválido").
- `[SUCESSO]`: Execução finalizada com sucesso e certidão baixada.
- `[CLEANUP]`: Ações de limpeza e liberação de recursos (ex: encerramento do processo `chromedriver`, exclusão de PDFs antigos).
- `[CAPTCHA_RESOLVED]` / `[CAPTCHA_FAILED]`: Status da resolução de captchas via OCR ou API externa (Gemini).
