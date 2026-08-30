# Logo PIENG — tamanhos para UI e ícone

Mestre: `logopieng-removebg-preview.png` (500×500, RGBA)

## Gerar tamanhos

```bat
backend\logo\gerar_tamanhos.bat
```

Ou: `python backend/logo/gerar_tamanhos.py`

## Arquivos gerados

| Arquivo | Uso |
|---------|-----|
| `logo-app-48.png` | Cabeçalho do app (48×48) |
| `logo-app-96.png` | Retina / `srcSet` 2× |
| `icon-32.png` | Favicon aba do navegador |
| `icon-180.png` | Apple touch icon |
| `icon-192.png` | PWA / Android |
| `icon-512.png` | PWA splash / ícone futuro |

Cópias vão para `equatorial_automation_frontend/public/brand/` (servidas em `/brand/...`).

## Alterar tamanho no app

Em `App.jsx`, ajuste `h-12 w-12` (48px) ou troque por `logo-app-96.png` com `h-16`.

Depois de trocar o PNG mestre, rode `gerar_tamanhos.bat` de novo.
