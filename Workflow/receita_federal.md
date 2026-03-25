# Fluxo do Automador - Receita Federal

## Arquivo
`worker/automators/receita_federal.py`

## Objetivo
Emitir a Certidão de Débitos Relativos a Créditos Tributários Federais e à Dívida Ativa da União (Receita Federal do Brasil).

## Etapas do Fluxo

1. **Acesso ao Site**
   - Utiliza **Undetected Chromedriver** com perfil isolado (`user_data_dir`).
   - Acessa a URL de emissão da Receita Federal.

2. **Preenchimento do Formulário**
   - Aceita cookies quando necessário.
   - Preenche o **CNPJ** no input apropriado.

3. **Emissão**
   - Clica no botão de emitir.
   - Trata mensagens de erro do site e modais de "Emitir nova".

4. **Aguardando Download**
   - Aguarda o download do PDF gerado.
   - Remove `.crdownload` antigos e identifica o novo arquivo no diretório.

5. **Padrão de Renomeação**
   - O arquivo final segue: `[CNPJ]_receita_federal_[DATA].pdf`.
   - Remove arquivos antigos do mesmo CNPJ e tipo.
   - Retorna o caminho do arquivo para o Worker.
