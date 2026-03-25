# Fluxo do Automador - Caixa FGTS

## Arquivo
`worker/automators/caixa_fgts.py`

## Objetivo
Emitir o Certificado de Regularidade do FGTS na Caixa Econômica Federal.

## Etapas do Fluxo

1. **Acesso ao Site**
   - Acessa a URL: `https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf`.

2. **Preenchimento do Formulário**
   - Insere o **CNPJ** no campo de pesquisa (limpo, apenas números).

3. **Seleção de UF e Consulta**
   - Seleciona a UF como **GO**.
   - Clica em **Consultar**.
   - Valida se o CNPJ é válido e se a empresa está regular perante o FGTS.

4. **Visualização da Certidão**
   - Navega pelos botões de resultado até a tela final da certidão.
   - Aguarda o texto **"Certificação Número:"** para confirmar emissão.

5. **Download via CDP**
   - Usa `Page.printToPDF` para salvar a tela final como PDF.

6. **Padrão de Renomeação**
   - O arquivo PDF final segue: `[CNPJ]_fgts_[DATA].pdf`.
   - Arquivos antigos do mesmo CNPJ e tipo são removidos.
   - Retorna o caminho do arquivo para o Worker.
