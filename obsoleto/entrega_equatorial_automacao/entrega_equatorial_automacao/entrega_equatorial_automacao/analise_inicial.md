# Análise inicial dos arquivos recebidos

## Arquivos enviados

1. `dados.txt`: contém dados cadastrais básicos do cliente.
2. `cliente_procuracao.docx`: modelo preenchido de procuração com logotipo da Equatorial.
3. `planilha_chaves_para_templates.xltx`: planilha de mapeamento de campos e marcadores.
4. `NT.00020-05-Anexo-I-Formulario-de-Solicitacao-Grupo-B-templates.xltx`: template principal da planilha da Equatorial.

## Conclusões principais

### 1. Estrutura de automação recomendada

A melhor abordagem é trabalhar com **marcadores (`{{CHAVE}}`) dentro dos templates** e um arquivo de entrada estruturado a partir do `.txt` do cliente. O script deve:

- extrair dados básicos do `.txt`;
- complementar campos técnicos a partir de um dicionário local ou pesquisa manual assistida;
- preencher `.docx` preservando cabeçalhos, rodapés, imagens e logotipos;
- preencher `.xlsx/.xltx` preservando fórmulas, formatação e objetos do arquivo original.

### 2. Situação do DOCX enviado

O arquivo `cliente_procuracao.docx` **não contém marcadores**; ele já está preenchido com dados reais.

Mesmo assim, a inspeção do pacote DOCX mostrou que o logotipo está embutido como mídia (`word/media/image1.png`) e que há cabeçalhos e rodapés próprios. Portanto, a automação do Word deve usar substituição de texto sem recriar o documento do zero, para preservar a estrutura visual.

### 3. Situação da planilha principal da Equatorial

O template principal contém vários marcadores `{{...}}` diretamente nas células, por exemplo:

| Área | Exemplos de marcadores |
| --- | --- |
| Dados cadastrais | `{{NOME_CLIENTE}}`, `{{CPF}}`, `{{RG}}`, `{{EMAIL}}` |
| Endereço | `{{ENDERECO}}`, `{{NUMERO}}`, `{{BAIRRO}}`, `{{CIDADE}}`, `{{UF}}`, `{{CEP}}` |
| Dados técnicos da UC | `{{TIPO_LIGACAO}}`, `{{TENSAO_ATENDIMENTO}}`, `{{DISJUNTOR_ENTRADA}}`, `{{POTENCIA_DISPONIBILIZADA}}` |
| Coordenadas | `{{COORDENADA_UTM_X}}`, `{{COORDENADA_UTM_Y}}` |
| Módulos | `{{FABRICANTE_MODULO}}`, `{{MODELO_MODULO}}`, `{{POTENCIA_MODULO}}`, `{{QTD_MODULOS}}` |
| Inversores | `{{FABRICANTE_INVERSOR}}`, `{{MODELO_INVERSOR}}`, `{{POTENCIA_INVERSOR}}`, `{{CORRENTE_INVERSOR}}` |
| Procuração | `{{NOME_PROCURADOR}}`, `{{CPF_PROCURADOR}}`, `{{RG_PROCURADOR}}` |

### 4. Planilha de chaves auxiliares

A planilha `planilha_chaves_para_templates.xltx` funciona como um **catálogo de campos** e amplia os dados necessários, inclusive para:

- inversor;
- módulo;
- disjuntor;
- disjuntor de entrada;
- potência disponibilizada;
- DPS.

Ela será útil para montar o formato final do arquivo de entrada e o mapeamento de preenchimento.

### 5. Dados já presentes no TXT de exemplo

O `dados.txt` já fornece:

| Campo | Valor encontrado |
| --- | --- |
| Nome | LAESTE MENDES FERREIRA |
| CPF | 319.257.231-00 |
| RG | 1898967 SSP GO |
| Data de nascimento | 25/05/1962 |
| Endereço | FAZENDA BOA VISTA, N. 0, - ROTA 961 |
| Bairro | ZONA RURAL |
| Cidade/UF | ANAPOLIS GO |
| CEP | 75149899 |
| UC | 704.212.012-65 |
| Telefone | 62 9314-0893 |
| E-mail | cirilomendesferreiraneto@gmail.com |

### 6. Lacunas identificadas

Ainda faltam, pelo menos neste exemplo:

- os outros **3 templates finais** que serão preenchidos;
- confirmação de como você quer representar os **dados técnicos** no `.txt`;
- definição de quais campos serão buscados localmente e quais poderão ser buscados externamente;
- um modelo Word com **marcadores explícitos**, caso a procuração final também vá ser automatizada com substituição estruturada.

## Risco técnico observado

Como o DOCX enviado está preenchido com conteúdo real e não com marcadores, a automação da procuração exigirá uma das duas abordagens:

1. criar uma cópia do modelo e substituir trechos fixos por novos valores com regras específicas; ou
2. converter o template definitivo para um modelo com marcadores explícitos, o que é mais robusto e mais fácil de manter.

A segunda abordagem é preferível.

## Próximo passo

Mapear formalmente os campos obrigatórios, separar os que vêm do `.txt`, os que vêm de tabelas locais e os que dependem de catálogo técnico de módulos/inversores, e então gerar o script local para uso no VS Code.
