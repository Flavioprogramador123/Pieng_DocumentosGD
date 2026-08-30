# Assets — Caixa de Medição (memorial)

Textos e figuras usados nos tokens `{{TEXTO_CAIXA}}` e `{{FIGURA_CAIXA}}`.

## Estrutura

```
caixa_medicao/
  monofasica/
    texto.txt    ← parágrafo descritivo (NT.00030 item 4.2.3)
    figura.png
  polifasica/
    texto.txt    ← parágrafo descritivo (NT.00030 item 4.2.4)
    figura.jpg
```

## Seleção automática

| TIPO_LIGACAO (formulário / TXT) | Pasta |
|----------------------------------|-------|
| MONOFASICO | `monofasica/` |
| TRIFASICO, BIFASICO | `polifasica/` |

Código: `backend/caixa_medicao.py`

## Editar conteúdo

Altere `texto.txt` ou substitua `figura.png` / `figura.jpg` e regenere o memorial.
Não é necessário reiniciar o backend.
