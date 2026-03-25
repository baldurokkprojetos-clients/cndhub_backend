# Fluxo do Automador - Prefeitura Goiânia

## Arquivo
`worker/automators/prefeitura_goiania.py`

## Objetivo
Emitir a Certidão de Débitos do Município de Goiânia.

## Etapas do Fluxo

1. **Acesso ao Site**
   - Acessa a URL: `https://www.goiania.go.gov.br/sistemas/sccer/asp/sccer00300f0.asp`.

2. **Preenchimento do Formulário**
   - Seleciona o tipo de documento como **CNPJ**.
   - Insere o **CNPJ** no campo apropriado (apenas números).

3. **Resolução de Captcha**
   - Captura a imagem do captcha via screenshot.
   - Envia a imagem para `solve_captcha_with_gemini`.
   - Insere o texto retornado no campo de confirmação.

4. **Emissão**
   - Clica no botão de emissão.
   - Verifica mensagens de erro de CNPJ inválido e confirma a geração pela presença de "Prazo de Validade".

5. **Download via CDP**
   - A página é salva em PDF usando `Page.printToPDF` (Chrome DevTools Protocol).

6. **Padrão de Renomeação**
   - O arquivo PDF é salvo e renomeado para: `[CNPJ]_prefeitura_goiania_[DATA].pdf`.
   - Arquivos PDF antigos de mesmo tipo e CNPJ são removidos.
   - Retorna o caminho do arquivo para o Worker.
