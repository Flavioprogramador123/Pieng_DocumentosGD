# Entrega atual

Foi criada uma primeira versão funcional da automação para uso local no VS Code.

## O que já está pronto

A procuração foi convertida para um template com marcadores, sem reconstruir o documento do zero. O logotipo da Equatorial, o cabeçalho, o rodapé, a formatação, as áreas de assinatura e o posicionamento visual foram preservados. Os dados do procurador e do responsável técnico foram colocados no `config_padrao.json` como valores padrão editáveis.

O Memorial Descritivo também foi convertido para um template com marcadores. Os marcadores distinguem dados do cliente, informações de campo, decisões do técnico responsável e dados de catálogo de módulos/inversores. O modelo mantém as páginas, tabelas, listas e figuras do documento original.

O gerador `gerar_documentos.py` lê linhas no formato `Campo: valor` do arquivo `.txt`, normaliza CPF, CEP, cidade/UF e RG, preenche campos de texto e numéricos em DOCX/XLSX e cria um relatório com os marcadores que ainda dependem de conferência ou informação técnica.

A planilha principal da Equatorial já está incluída na pasta `templates/`. Os campos de módulo, inversor, disjuntor, DPS, coordenadas e potência podem ser preenchidos quando forem adicionados ao TXT. O Memorial Descritivo parametrizado está na mesma pasta.

## Como usar

1. Coloque os documentos parametrizados dentro de `templates/`.
2. Copie `dados_modelo.txt` para um novo arquivo, como `cliente_001.txt`, e preencha os valores.
3. Execute:

```bash
python gerar_documentos.py --input cliente_001.txt --templates-dir templates --output-dir saida --config config_padrao.json
```

4. Abra os documentos da pasta `saida/` e confira o `relatorio_preenchimento.txt`.

## Pendência para completar os quatro documentos

Até este momento foram recebidos dois documentos Word — a procuração e o Memorial Descritivo —, a planilha de chaves e a planilha principal da Equatorial. Para completar os quatro arquivos finais mencionados no projeto, ainda falta receber pelo menos um template Word adicional e confirmar se existe outro documento Word específico além do Memorial.

Se os outros modelos ainda estiverem sem marcadores, será necessário inserir os marcadores equivalentes antes de executar a geração. O gerador já foi preparado para preservar o conteúdo XML do DOCX, inclusive imagens, cabeçalhos e rodapés.
