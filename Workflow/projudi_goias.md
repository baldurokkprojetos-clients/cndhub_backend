# Fluxo do Automador - Projudi Goiás

## Arquivo
`worker/automators/projudi_goias.py`

## Objetivo
Emitir a Certidão de Distribuição (Nada Consta) de Segundo Grau, Cível, no Tribunal de Justiça de Goiás.

## Etapas do Fluxo

1. **Acesso ao Site**
   - O automador abre a URL `https://projudi.tjgo.jus.br/CertidaoSegundoGrauNegativaPositivaPublicaPJ?PaginaAtual=1`.
   - Aguarda **10 segundos** para burlar proteções anti-bot (Cloudflare).

2. **Preenchimento do Formulário**
   - Insere a **Razão Social** no campo (`//*[@id="divEditar"]/fieldset[1]/div[1]//input`).
   - Insere o **CNPJ** (apenas números) no campo (`//*[@id="divEditar"]/fieldset[1]/div[2]//input`).

3. **Seleção de Opções**
   - Marca a opção de Área **Cível** no rádio button (`//*[@id="divEditar"]/fieldset[1]/div[4]/input[1]`).

4. **Emissão e Verificação de Erros**
   - Clica no botão **Gerar Certidão** (`//*[@id="divBotoesCentralizados"]/input[1]`).
   - Verifica se aparece a mensagem de **"CNPJ inválido"** no diálogo.
   - Se aparecer, retorna erro imediatamente.

5. **Aguardando Download**
   - Monitora o diretório de downloads por até 45 segundos.
   - Considera apenas arquivos que não terminem com `.crdownload` ou `.tmp`.

6. **Padrão de Renomeação**
   - O arquivo PDF baixado é renomeado para: `[CNPJ]_projudi_goias_[DATA].pdf`.
   - Arquivos antigos do tipo `projudi_goias` e deste CNPJ específico são removidos.
   - Retorna o caminho do arquivo para o Worker.
