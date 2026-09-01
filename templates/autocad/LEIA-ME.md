# AutoCAD — `projeto_Modelo.dwg`

Template de prancha com tokens `{{NOME_DO_TOKEN}}` em TEXT/MTEXT.

## Arquivos gerados na pasta do cliente

| Arquivo | Uso |
|---------|-----|
| **`planta.dwg`** | Prancha com textos preenchidos (~2 MB) — abrir no AutoCAD |
| `planta.dxf` | *Fallback* se ODA File Converter não estiver instalado |
| `figura_localizacao.png` | Mapa (referência para colar na prancha) |
| `tokens_autocad.txt` | Backup dos valores (opcional) |

Quando editar o DWG, **reexporte** `projeto_Modelo.dxf` para o preenchimento automático continuar correto.

## Fluxo (retoques finais)

1. Gere documentos na web → pasta `80 - Nome Cliente\`
2. Abra **`planta.dwg`** no AutoCAD (ou `planta.dxf` se ODA não converteu)
3. **Mapa de localização:** abra `figura_localizacao.png` (ou o mapa na tela), **Win+Shift+S**, recorte e **Ctrl+V** no AutoCAD na área da prancha
4. Ajuste escala/posição do mapa e demais detalhes
5. Apague o marcador `{{FIGURA_LOCALIZACAO}}` se ainda existir
6. Salve o DWG após colar o mapa (já é `.dwg` quando ODA está instalado)

## ODA File Converter (conversão automática DXF→DWG)

Instale no Windows para entregar `planta.dwg` compacto (~2 MB em vez de ~25 MB DXF):

https://www.opendesign.com/guestfiles/oda_file_converter

Caminho padrão: `C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe`  
Opcional no `.env`: `ODA_FILE_CONVERTER=caminho\para\ODAFileConverter.exe`

Teste: `python backend/test_dxf_to_dwg.py`

## LISP (opcional — só se não usar `planta.dxf`)

`pieng_tokens.lsp` → comando **`PIENG_TOKENS`** reaplica tokens a partir de `tokens_autocad.txt`.  
Não é necessário no fluxo normal (a web já gera o `planta.dxf` preenchido).

## Tokens (carimbo + bloco técnico)

```
{{CIDADE}}  {{UF}}  {{BAIRRO}}  {{ENDERECO_COMPLETO}}
{{POTENCIA_PAINEL_KWP}}  {{POTENCIA_INVERSOR_KWP}}  {{POTENCIA_GERACAO}}
{{QTD_MODULOS}}  {{POTENCIA_MODULO}}  {{FABRICANTE_MODULO}}
{{QTD_INVERSORES}}  {{FABRICANTE_INVERSOR}}  {{POTENCIA_INVERSOR_UNITARIO}}
{{POTENCIA_INVERSOR_TOTAL}}  {{CONTA_CONTRATO_DIGITOS}}  {{NOME_CLIENTE}}  {{CPF}}
{{DATA}}  (dd/mm/aaaa — dia da geração ou campo Data do Documento; alias: {{DATA_DOCUMENTO}})

Diagrama de bloco (texto pronto ou monte com tokens granulares):
{{TEXTO_DIAGRAMA_MODULOS}}
{{TEXTO_DIAGRAMA_INVERSOR}}
{{TEXTO_DISJUNTOR_CA_INVERSOR}}   — disjuntor CA do inversor (QDCA)
{{TEXTO_DISJUNTOR_CA_PADRAO}}     — disjuntor CA do padrão de entrada

Granular (alternativa):
{{QTD_MODULOS_2D}} x Módulos Fotovoltaicos de {{POTENCIA_MODULO}} Wp, marca {{FABRICANTE_MODULO}} POT UNIT: {{POTENCIA_MODULO_KWP}} {{POTENCIA_PAINEL_KWP}} KWp;
{{QTD_INVERSORES_2D}} - {{TIPO_EQUIPAMENTO_INVERSOR}} {{FABRICANTE_INVERSOR}} {{MODELO_INVERSOR}} X {{POTENCIA_INVERSOR_UNITARIO}} KW
Disjuntor {{DISJUNTOR_CA_INVERSOR_A}}A
Disjuntor {{DISJUNTOR_CA_PADRAO_A}}A
```

**Diagrama unifilar** (MTEXT — use `\{\{TOKEN\}\}` se tiver formatação Arial):

```
\{\{TEXTO_UNIFILAR_STRING_1\}\}
\{\{TEXTO_UNIFILAR_STRING_2\}\}
\{\{TEXTO_UNIFILAR_STRING_3\}\}
\{\{TEXTO_UNIFILAR_STRING_4\}\}
\{\{TEXTO_UNIFILAR_INVERSOR\}\}      — inversor string
\{\{TEXTO_UNIFILAR_MICRO\}\}         — micro-inversor (topologia micro)
\{\{TEXTO_UNIFILAR_MPPT_1\}\}        — rótulo MPPT colorido
\{\{TEXTO_UNIFILAR_ARRANJO_1\}\}     — arranjo CC (micro, todos os módulos)
```

**UC / conta contrato:** use `{{CONTA_CONTRATO_DIGITOS}}` no DXF (só números, ex.: `000068889901235`).
`{{CONTA_CONTRATO}}` também é normalizado para dígitos no CAD.
Para formato com pontos (`4.275.682.012-90`), use `{{CONTA_CONTRATO_FORMATADA}}` no memorial.

O marcador `{{FIGURA_LOCALIZACAO}}` no desenho é só referência visual — a figura entra manualmente (recorte + colar).
