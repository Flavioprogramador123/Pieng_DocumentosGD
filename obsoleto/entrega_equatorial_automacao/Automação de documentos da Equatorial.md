# Automação de documentos da Equatorial

Este projeto preenche documentos `.docx` e `.xlsx` da Equatorial a partir de um arquivo `.txt` com dados do cliente, da unidade consumidora e dos equipamentos. A procuração foi preparada como um template com marcadores e mantém o logotipo, cabeçalho, rodapé, margens, estilos e áreas de assinatura do modelo original.

## Estrutura do projeto

| Arquivo ou pasta | Finalidade |
| --- | --- |
| `gerar_documentos.py` | Lê o TXT, aplica os dados padrão e preenche os templates. |
| `criar_template_procuracao.py` | Recria a procuração parametrizada a partir do DOCX original. |
| `config_padrao.json` | Mantém os dados fixos do procurador e responsável técnico Iury. |
| `dados_modelo.txt` | Modelo de TXT com os campos que podem ser informados. |
| `templates/` | Deve conter os documentos parametrizados que serão preenchidos. |
| `saida/` | Pasta criada pelo programa com os documentos finais e o relatório. |
| `planilha_chaves_para_templates.xltx` | Catálogo auxiliar de marcadores e campos técnicos. |

## Preparação no VS Code

Abra esta pasta no VS Code. No terminal integrado, crie um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
```

No Windows:

```powershell
.venv\Scripts\activate
pip install lxml openpyxl
```

No Linux ou macOS:

```bash
source .venv/bin/activate
pip install lxml openpyxl
```

O projeto foi escrito para Python 3.10 ou superior.

## Preencher um cliente

Coloque o TXT do cliente na pasta do projeto e execute:

```bash
python gerar_documentos.py --input dados.txt --templates-dir templates --output-dir saida --config config_padrao.json
```

O programa cria uma cópia de cada `.docx` e `.xltx` encontrado na pasta `templates`. Arquivos `.xltx` são gerados como `.xlsx` na pasta de saída, sem modificar o modelo original. Também é criado o arquivo `saida/relatorio_preenchimento.txt`, que mostra os dados interpretados e todos os marcadores que ainda ficaram pendentes.

A ausência de dados técnicos no TXT não interrompe a geração. Nesse caso, os campos ficam no modelo e aparecem no relatório como pendentes para serem completados antes do protocolo.

## Dados padrão do Iury

Os dados do Iury estão no arquivo `config_padrao.json`. O programa os aplica automaticamente nos campos de procurador e responsável técnico quando eles não são informados no TXT. Para alterar algum dado fixo, edite esse arquivo uma única vez.

A procuração usa os seguintes marcadores principais:

| Marcador | Origem |
| --- | --- |
| `{{NOME_CLIENTE}}`, `{{CPF}}`, `{{RG}}` | Dados do cliente no TXT. |
| `{{ENDERECO}}`, `{{BAIRRO}}`, `{{CEP}}`, `{{CIDADE}}`, `{{UF}}` | Dados de endereço no TXT. |
| `{{NOME_PROCURADOR}}`, `{{CPF_PROCURADOR}}`, `{{RG_PROCURADOR}}` | `config_padrao.json`, salvo substituição explícita. |
| `{{ENDERECO_PROCURADOR}}`, `{{TELEFONE_PROCURADOR}}` | `config_padrao.json`. |
| `{{CONCESSIONARIA}}`, `{{OBJETO_PROCURACAO}}` | Seção `procuracao` de `config_padrao.json`. |
| `{{CIDADE_DOCUMENTO}}`, `{{DATA_DOCUMENTO_EXTENSO}}` | Cidade e data do documento. |

## Formato do TXT

O leitor reconhece linhas no formato `Campo: valor`. Os nomes dos campos podem ser escritos com ou sem acentos em diversos casos. O arquivo `dados_modelo.txt` contém a lista completa de campos, incluindo módulos, inversores, disjuntor e DPS.

Exemplo mínimo:

```text
Nome: LAESTE MENDES FERREIRA
CPF: 319.257.231-00
RG: 1898967 SSP GO
Data de Nascimento: 25/05/1962
Endereço: FAZENDA BOA VISTA, N. 0, - ROTA 961
Bairro: ZONA RURAL
Cidade/UF: ANAPOLIS GO
CEP: 75149899
Telefone: 62 9314-0893
E-mail: cirilomendesferreiraneto@gmail.com
Unidade Consumidora (UC): 704.212.012-65
Data do Documento: 22/08/2026
Cidade do Documento: Anápolis
```

## Inclusão dos demais templates

Os três documentos Word e a planilha final devem conter os mesmos marcadores do catálogo `planilha_chaves_para_templates.xltx`. Depois de receber ou preparar os outros modelos, copie-os para `templates/`. O programa percorre automaticamente todos os arquivos `.docx`, `.xlsx` e `.xltx` dessa pasta.

Para a procuração, use o arquivo já criado `modelo_procuracao_marcadores.docx`. A versão original preenchida não precisa ficar na pasta de execução.

## Observações de segurança e conferência

O programa não envia dados do cliente para a internet. A consulta de dados técnicos de módulos e inversores deve ser feita manualmente ou por uma integração autorizada e, depois, os valores podem ser inseridos no TXT. Isso evita completar um documento oficial com especificações não confirmadas.

Antes de protocolar, abra os arquivos gerados no Word e no Excel, confira os campos listados no relatório e valide especialmente tensão, disjuntor, coordenadas UTM, potência, modelo dos equipamentos e data. O preenchimento automático não substitui a conferência técnica nem a assinatura exigida.
