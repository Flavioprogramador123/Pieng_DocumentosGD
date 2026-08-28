# Manual do Usuário - Sistema de Automação Equatorial Energia

## Visão Geral

O Sistema de Automação para Documentos da Equatorial Energia foi desenvolvido para facilitar o preenchimento de documentos relacionados ao PRODIST 3 e à Resolução ANEEL sobre Geração Distribuída. O sistema automatiza cálculos técnicos e gera documentos padronizados, reduzindo significativamente o tempo de preparação de projetos.

## Funcionalidades Principais

### 1. Entrada de Dados do Cliente
- **Nome do Cliente**: Campo obrigatório para identificação
- **CPF**: Documento de identificação (opcional)
- **Endereço Completo**: Campo obrigatório com endereço completo
- **Unidade Consumidora**: Campo obrigatório com número da UC

### 2. Configuração do Sistema
- **Tensão da Rede**: Seleção entre 220V, 380V, etc.
- **Tipo de Consumo**: Autoconsumo Local, Remoto, Geração Compartilhada ou EMUC

### 3. Especificação de Equipamentos
- **Módulos Fotovoltaicos**: Quantidade, modelo e potência
- **Inversores**: Quantidade, modelo e potência
- Possibilidade de adicionar múltiplos tipos de equipamentos

### 4. Cálculos Técnicos Automatizados
- **Dimensionamento de Cabos**: Baseado na NR5410
- **Dispositivos de Proteção**: Disjuntores, DPS, DR
- **Estimativa de Geração**: Baseada na irradiação solar local
- **Análise Econômica**: VPL, TIR, Payback
- **Compatibilidade do Sistema**: Verificação automática

### 5. Geração de Documentos
- **Formulário Excel**: NT.00020-05 preenchido automaticamente
- **Memorial Técnico Descritivo**: Documento Word personalizado
- **Procuração**: Documento de representação legal

## Como Usar o Sistema

### Passo 1: Inicialização
1. Execute o arquivo `iniciar.bat` (Windows) ou `iniciar.sh` (Linux/Mac)
2. Aguarde a inicialização dos serviços
3. Acesse http://localhost:5173 no navegador

### Passo 2: Preenchimento dos Dados
1. **Dados do Cliente**: Preencha os campos obrigatórios
2. **Dados Técnicos**: Configure tensão e tipo de consumo
3. **Equipamentos**: Adicione módulos e inversores com suas especificações

### Passo 3: Cálculos
1. Clique em "Calcular Sistema"
2. Aguarde o processamento dos cálculos técnicos
3. Revise os resultados apresentados

### Passo 4: Geração de Documentos
1. Clique em "Gerar Documentos"
2. Aguarde a criação dos arquivos
3. Baixe os documentos gerados

## Cálculos Técnicos Implementados

### Dimensionamento de Cabos (NR5410)
- Cálculo da corrente nominal e corrigida
- Consideração de fatores de temperatura e agrupamento
- Verificação de queda de tensão (máximo 3%)
- Seleção de seção padronizada

### Dispositivos de Proteção
- **Disjuntores DC/AC**: 125% da corrente nominal
- **Fusíveis de String**: 150% da corrente de curto-circuito
- **DPS**: Classe II ou I conforme tensão
- **DR**: Sensibilidade conforme potência do sistema

### Estimativa de Geração
- Irradiação solar para o Maranhão: 5,2 kWh/m²/dia
- Fator de performance: 85%
- Degradação anual: 0,5%
- Projeção para 25 anos

### Análise Econômica
- **VPL**: Valor Presente Líquido
- **TIR**: Taxa Interna de Retorno
- **Payback**: Simples e descontado
- Consideração de inflação da tarifa elétrica

## Arquivos de Saída

### 1. Formulário Excel (NT.00020-05)
- Dados do cliente preenchidos
- Especificações dos equipamentos
- Cálculos técnicos integrados

### 2. Memorial Técnico Descritivo
- Descrição técnica do sistema
- Especificações dos equipamentos
- Cálculos de dimensionamento

### 3. Procuração
- Documento de representação legal
- Dados do cliente preenchidos
- Pronto para assinatura

## Solução de Problemas

### Problemas Comuns

#### Sistema não inicia
1. Execute `diagnostico.bat` ou `diagnostico.sh`
2. Verifique se Python e Node.js estão instalados
3. Verifique se as portas 5000 e 5173 estão livres

#### Cálculos não funcionam
1. Verifique se todos os campos obrigatórios estão preenchidos
2. Confirme se os valores de potência são numéricos
3. Verifique a conexão com o backend

#### Documentos não são gerados
1. Verifique se os templates estão no diretório correto
2. Confirme se há espaço em disco suficiente
3. Verifique permissões de escrita no diretório de saída

### Scripts de Diagnóstico

#### Windows (diagnostico.bat)
```batch
@echo off
echo === Diagnóstico do Sistema ===
echo Verificando Python...
python --version
echo Verificando Node.js...
node --version
echo Verificando portas...
netstat -an | findstr :5000
netstat -an | findstr :5173
echo Verificando arquivos...
dir templates
dir output
pause
```

#### Linux/Mac (diagnostico.sh)
```bash
#!/bin/bash
echo "=== Diagnóstico do Sistema ==="
echo "Verificando Python..."
python3 --version
echo "Verificando Node.js..."
node --version
echo "Verificando portas..."
netstat -tlnp | grep :5000
netstat -tlnp | grep :5173
echo "Verificando arquivos..."
ls -la templates/
ls -la output/
```

## Requisitos do Sistema

### Software Necessário
- Python 3.11 ou superior
- Node.js 20.18 ou superior
- Navegador web moderno (Chrome, Firefox, Edge)

### Dependências Python
- Flask
- Flask-CORS
- pandas
- openpyxl
- python-docx

### Dependências Node.js
- React
- Vite
- Axios

## Estrutura de Diretórios

```
equatorial_automation/
├── equatorial_automation_backend/    # Backend Flask
│   ├── src/
│   │   ├── main.py                  # Aplicação principal
│   │   └── routes/
│   │       └── automation.py        # Rotas da API
│   └── venv/                        # Ambiente virtual Python
├── equatorial_automation_frontend/   # Frontend React
│   ├── src/
│   │   └── App.jsx                  # Componente principal
│   └── dist/                        # Build de produção
├── templates/                       # Templates dos documentos
│   ├── NT.00020-05-Anexo-I-*.xlsx  # Formulário Excel
│   ├── MODELODEMEMORIAL*.docx       # Memorial técnico
│   └── ExemploProcuracao*.docx      # Procuração
├── output/                          # Documentos gerados
├── scripts/                         # Scripts auxiliares
│   └── advanced_calculations.py     # Cálculos técnicos
├── iniciar.bat / iniciar.sh         # Scripts de inicialização
├── diagnostico.bat / diagnostico.sh # Scripts de diagnóstico
└── README.md                        # Documentação
```

## Suporte Técnico

Para suporte técnico ou dúvidas sobre o sistema:

1. **Documentação**: Consulte este manual primeiro
2. **Diagnóstico**: Execute os scripts de diagnóstico
3. **Logs**: Verifique os logs do sistema nos terminais
4. **Contato**: Entre em contato com o desenvolvedor

## Atualizações e Melhorias

### Versão Atual: 1.0
- Sistema básico de automação
- Cálculos técnicos conforme NR5410
- Geração de documentos padrão

### Próximas Versões
- Integração com APIs de TRT técnico
- Geração automática de projetos AutoCAD
- Banco de dados de equipamentos
- Relatórios de comissionamento
- Interface para múltiplos projetos

## Considerações Importantes

### Responsabilidade Técnica
- Os cálculos são baseados em normas técnicas vigentes
- Sempre revise os resultados antes de submeter à concessionária
- Mantenha-se atualizado com mudanças nas normas

### Backup e Segurança
- Faça backup regular dos templates personalizados
- Mantenha cópias dos projetos importantes
- Proteja dados sensíveis dos clientes

### Conformidade
- Sistema desenvolvido conforme PRODIST Módulo 3
- Atende às exigências da Resolução ANEEL
- Compatível com normas técnicas da Equatorial Energia

---

**Desenvolvido para otimizar o processo de documentação de projetos de geração distribuída, garantindo conformidade técnica e agilidade operacional.**

