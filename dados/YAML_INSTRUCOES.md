# Instruções — preencher YAML com IA externa

Use este texto como prompt no Gemini, Claude ou ChatGPT. Cole o YAML preenchido na aba **Entrada → YAML** do sistema.

---

## Prompt sugerido

```
Você é assistente de engenharia solar no Brasil (PRODIST 3 / Equatorial Energia).

Tarefa: preencher o YAML abaixo com dados técnicos REAIS do equipamento.
Regras:
1. Busque datasheets oficiais para Voc, Isc, Vmpp, Impp, eficiência dos módulos e MPPT do inversor.
2. Potência do módulo em Wp (watt-pico). Potência do inversor em kW.
3. Use formato de data AAAA-MM-DD.
4. UF em 2 letras (ex.: GO). tipo_ligacao: MONOFASICO, BIFASICO ou TRIFASICO.
5. Deixe vazio ("") o que não souber — não invente CPF, RG ou UC.
6. Mantenha a estrutura YAML; não remova chaves.
7. Responda APENAS com o YAML completo, sem markdown.

Dados do cliente que tenho:
- Nome: [NOME]
- Cidade/UF: [CIDADE/UF]
- Módulos: [QTD] x [FABRICANTE] [MODELO]
- Inversor(es): [QTD] x [FABRICANTE] [MODELO]
- Ligação: [MONO/TRI]
- UC: [se souber]

[Cole aqui o conteúdo de dados/projeto_padrao.yaml]
```

---

## Fluxo recomendado

1. Copie `dados/projeto_padrao.yaml` (botão **Carregar modelo** na UI).
2. Preencha manualmente nome, endereço, UC e quantidades.
3. Envie o YAML parcial + prompt acima para a IA externa.
4. Cole o YAML retornado na aba Entrada → YAML → **Importar**.
5. Revise no painel DE/PARA e nas abas Cliente / Equipamentos / Técnicos.
6. Use **Catálogo SQL** para gravar equipamentos novos e reutilizar depois.

---

## O que o sistema preenche automaticamente

- Defaults residenciais (DPS, cabos, aterramento) se vazios.
- Specs de módulo/inversor do **catálogo SQLite** quando fabricante+modelo batem.
- Padrão de entrada (disjuntor, bitola) por **UF + tipo de ligação**.
- Data do documento = hoje, se não informada.
