# 🎨 Paleta de Cores PIENG - Tema Azul Profissional

## Cores Principais

### Azul Corporativo (Primary)
- **Azul Escuro**: `#1e3a8a` (blue-900) - Títulos, botões principais
- **Azul Médio**: `#3b82f6` (blue-500) - Links, destaque
- **Azul Claro**: `#60a5fa` (blue-400) - Hover states

### Cinza Neutro (Background)
- **Branco**: `#ffffff` - Background principal
- **Cinza Muito Claro**: `#f8fafc` (slate-50) - Background alternativo
- **Cinza Claro**: `#e2e8f0` (slate-200) - Bordas
- **Cinza Médio**: `#64748b` (slate-500) - Texto secundário
- **Cinza Escuro**: `#1e293b` (slate-800) - Texto principal

### Cores de Ação
- **Verde Sucesso**: `#10b981` (emerald-500)
- **Amarelo Aviso**: `#f59e0b` (amber-500)
- **Vermelho Erro**: `#ef4444` (red-500)

## Conversão para OKLCH

### Light Mode
```css
--primary: oklch(0.45 0.15 264)          /* Azul Escuro #1e3a8a */
--primary-hover: oklch(0.55 0.20 264)    /* Azul Médio #3b82f6 */
--background: oklch(1 0 0)                /* Branco */
--foreground: oklch(0.25 0.01 264)       /* Cinza Escuro */
--accent: oklch(0.65 0.20 264)           /* Azul Claro */
```

### Dark Mode
```css
--background: oklch(0.18 0.01 264)       /* Azul Muito Escuro */
--foreground: oklch(0.98 0 0)            /* Branco */
--primary: oklch(0.65 0.20 264)          /* Azul Claro */
```

## Aplicação

- **Header/Nav**: Azul Escuro (#1e3a8a)
- **Botões Primários**: Azul Médio (#3b82f6)
- **Links**: Azul Médio (#3b82f6)
- **Sidebar**: Cinza Muito Claro (#f8fafc)
- **Cards**: Branco (#ffffff) com borda Cinza Claro
- **Texto Principal**: Cinza Escuro (#1e293b)
- **Texto Secundário**: Cinza Médio (#64748b)
