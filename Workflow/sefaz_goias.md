# Fluxo do Automador - Sefaz Goiás

## Arquivo
`worker/automators/sefaz_goias.py`

## Objetivo
Emitir a Certidão de Débitos da Secretaria de Estado da Economia de Goiás (Sefaz GO).

## Etapas do Fluxo

1. **Acesso ao Site**
   - Acessa o portal público da Sefaz-GO para emissão de CND.

2. **Preenchimento do Formulário**
   - Seleciona o tipo de documento como **CNPJ**.
   - Insere o número do **CNPJ**.

3. **Emissão**
   - Clica no botão de emitir/gerar.

4. **Aguardando Download**
   - Aguarda que o arquivo seja baixado no diretório configurado.
   - Considera apenas arquivos que não terminem com `.crdownload`.

5. **Padrão de Renomeação**
   - O arquivo PDF final segue: `[CNPJ]_sefaz_goias_[DATA].pdf`.
   - Remove arquivos antigos do mesmo CNPJ e tipo.
   - Retorna o caminho do arquivo para o Worker.
