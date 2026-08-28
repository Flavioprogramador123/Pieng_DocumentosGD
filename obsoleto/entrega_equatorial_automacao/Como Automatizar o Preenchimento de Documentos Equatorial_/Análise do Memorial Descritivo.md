# Análise do Memorial Descritivo

## Classificação de dados para automação

| Grupo | Exemplos identificados | Origem prevista |
| --- | --- | --- |
| Dados da unidade consumidora | Conta contrato, titular, endereço, classe, poste/transformador, coordenadas UTM | TXT e levantamento local |
| Entrada do padrão | Tipo de ligação, tensão, número de fases, bitola dos cabos, disjuntor de entrada, curva, capacidade de interrupção | Técnico de campo |
| Cálculos elétricos | PD em kVA/kW, corrente dos inversores, margem de proteção, compatibilidade de tensão | Calculados pelo programa a partir dos dados confirmados |
| Gerador fotovoltaico | Fabricante, modelo, potência unitária, quantidade, arranjo, potência total, Voc, Isc, Vmp/Vpmp, Imp/Ipmp, eficiência, bifacialidade | Modelo/arranjo pelo técnico; demais dados por ficha técnica/OCR |
| Inversor | Fabricante, modelo, quantidade, potência por unidade, potência total, MPPT, tensões, correntes, frequência, fator de potência, THD, eficiência | Modelo, quantidade e potência pelo técnico; demais dados por ficha técnica/OCR |
| Proteções | Disjuntor CA, DPS, fusíveis, seccionamento visível | Técnico de campo e técnico responsável |
| Cabos e aterramento | Cabo CC, cabo CA, cabo do padrão, bitolas, capacidades de condução, haste e condutor de aterramento | Técnico de campo |
| Dados do responsável técnico | Nome, título, registro profissional e local/data | Configuração padrão do Iury, editável |

## Campos importantes encontrados

O documento possui seções de objetivo, dados da unidade consumidora, levantamento de carga, padrão de entrada, cálculo da potência disponibilizada, estimativa de geração, dimensionamento do gerador, dimensionamento do inversor, proteção, cabos, DPS, caixa de medição, aterramento, placa de advertência e anexos.

O modelo preenchido contém tabelas com os dados do disjuntor de entrada, cálculo de PD, módulo fotovoltaico RENE PV de 690 Wp bifacial, oito módulos, microinversor SAJ M2-2.25K-S4, dois equipamentos, DPS CA classe II e cabos de 4 mm² para CC/CA. Esses valores pertencem ao exemplo recebido e não devem ser transformados automaticamente em padrão para outros clientes.

## Estratégia recomendada

O Memorial deve ser transformado em template com marcadores explícitos, mantendo o texto técnico fixo e substituindo apenas valores variáveis. Para evitar preencher informação de forma indevida, os marcadores serão agrupados em três classes:

1. `CAMPO_*`: informações de campo, que ficam pendentes até o técnico informar.
2. `TECNICO_*`: decisões e dimensionamento do técnico responsável.
3. `CATALOGO_*`: dados de placa/ficha técnica, que podem ser preenchidos por OCR ou consulta confirmada.

Os cálculos derivados, como potência instalada, potência total de inversores, PD e corrente, poderão ser calculados a partir dos valores confirmados, mas o relatório continuará sinalizando os dados de origem que precisam ser conferidos.

## Observação de qualidade

O documento de exemplo apresenta alguns trechos com redação e valores que precisam ser conferidos antes de virar regra automática, como a descrição do circuito trifásico, a identificação de caixa monofásica em contexto trifásico e a diferença entre disjuntor de entrada de 63 A e proteção CA de 32 A/25 A em trechos distintos. Esses itens devem permanecer configuráveis e não devem ser inferidos silenciosamente pelo programa.
