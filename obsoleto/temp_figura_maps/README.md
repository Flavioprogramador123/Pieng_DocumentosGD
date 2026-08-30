# Protótipo integrado ao backend — ver backend/figura_localizacao.py

Este diretório foi usado para validar a geração automática da figura de localização.
A funcionalidade oficial está em **`backend/figura_localizacao.py`**, acionada ao gerar o memorial.

Para testes manuais isolados, `testar.bat` e `gerar_figura_maps.py` continuam disponíveis.


## Requisitos

- Python 3.10+
- Internet (download de tiles OpenStreetMap)

## Instalação (venv local desta pasta)

```bat
cd .temp\figura_maps
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Para testar inserção no DOCX (opcional):

```bat
.venv\Scripts\pip install python-docx
```

## Uso rápido — coordenadas do último cliente (Cleidimar)

```bat
testar.bat
```

Ou manualmente:

```bat
.venv\Scripts\python gerar_figura_maps.py --lat -16.326990 --lon -48.915934
```

A PNG sai em `.temp/figura_maps/saida/`.

## A partir do TXT do cliente

```bat
.venv\Scripts\python gerar_figura_maps.py --txt ..\..\saida\web_generated\NOME_CLIENTE\dados_cliente.txt
```

Aceita linhas `Latitude:`, `Longitude:`, `Coordenadas:`, ou par `-16.32, -48.91` no texto.

## Parâmetros úteis

| Parâmetro | Efeito |
|-----------|--------|
| `--zoom 17` | Mostra mais ruas ao redor |
| `--zoom 18` | Padrão — nível de lotes (como o exemplo) |
| `--raio 3` | Grade 7×7 de tiles (mais contexto) |
| `--largura 900 --altura 650` | Tamanho final recortado |

## Vista satélite (opcional, mais parecida com o print Google)

Defina a variável de ambiente `GOOGLE_MAPS_API_KEY` (Static Maps API) e use:

```bat
set GOOGLE_MAPS_API_KEY=sua_chave
.venv\Scripts\python gerar_figura_maps.py --lat -16.326990 --lon -48.915934 --google
```

Sem chave, usa **OpenStreetMap** (ruas e nomes — suficiente para validar o fluxo).

## Inserir no memorial (experimento)

Gera cópia `*_com_figura.docx` — **não altera** o template oficial:

```bat
.venv\Scripts\python inserir_figura_memorial.py ^
  --memorial ..\..\templates\MEMORIAL_DESCRITIVO_marcadores.docx ^
  --figura saida\figura_localizacao_m16_326990_m48_915934.png
```

## AutoCAD

Inserção automática em DWG/DXF **não está neste protótipo** (formato binário + layout variável). Por ora:

1. Gere a PNG
2. No AutoCAD: `IMAGEATTACH` ou colar manualmente como no fluxo atual

## Próximo passo (se aprovar)

- Integrar em `gerar_documentos.py` no token `{{FIGURA_LOCALIZACAO}}` como imagem inline
- Disparar após `resolve_coordinates()` no `fill-documents`
- Avaliar licença/atribuição OSM no rodapé do memorial

## Descartar

Se não der certo, apague a pasta `.temp/figura_maps/` inteira — o projeto principal não é afetado.
