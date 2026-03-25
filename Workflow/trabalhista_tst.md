# Fluxo do Automador - Trabalhista TST

## Arquivo
`worker/automators/trabalhista_tst.py`

## Objetivo
Emitir a Certidão Negativa de Débitos Trabalhistas (CNDT) do Tribunal Superior do Trabalho.

## Etapas do Fluxo

1. **Acesso ao Site**
   - Acessa a página oficial de emissão de CNDT do TST.
   - Aceita o banner de cookies quando presente.

2. **Preenchimento do Formulário**
   - Preenche o campo de **CNPJ** com apenas números.

3. **Resolução de Captcha (OCR)**
   - Captura a imagem do captcha em base64.
   - Envia a imagem para a rotina `solve_captcha_with_gemini`.
   - Preenche o texto retornado no input do captcha.

4. **Emissão**
   - Clica no botão **Emitir Certidão**.

5. **Download**
   - Tenta identificar download automático do PDF.
   - Se não houver download, salva a tela via `Page.printToPDF`.

6. **Padrão de Renomeação**
   - O arquivo final segue o padrão: `[CNPJ]_trabalhista_tst_[DATA].pdf`.
   - Arquivos antigos do mesmo CNPJ e tipo são removidos.
   - Retorna o caminho absoluto para envio ao backend.
