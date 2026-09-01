import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  parseTxtData,
  toIsoDate,
  formatCpf,
  formatTelefone,
  parseAddress,
} from './txtParser.js'

const SAMPLE = `
**Dados da CNH**

* Nome: ROSEMBERGUE LEAO E SILVA
* CPF: 426.985.961-04 / 42698596104
* RG: 2372249 SSP GO
* Data de Nascimento: 18/02/1970
* Pai: EDIO JOSE DA SILVA
* Mãe: ANA ROSA LEAO DA SILVA
* Validade CNH: 23/01/2030

**Dados da Fatura / Documento de Energia**

* Endereço: Rua Pernambuco, Q. F, L. 5/6, Anexo Itamaraty
* Cidade/UF: Anápolis/GO
* Unidade Consumidora (UC): 000068889901235
CEP  75050-270
**Dados de Contato**

* Telefone: 62 9274-3040
* E-mail: doceslu@uol.com.br
-16.291613, -48.973249
**Equipamentos do Sistema e Instalação Elétrica**

* Módulos Fotovoltaicos: 32 unidades de MÓDULO 680W RENEPV BIFACIAL 30MM
* Inversores: 8 unidades de MICRO INVERSOR DEYE-S2.25K-G4 220V
* Padrão de Conexão: Trifásico 220/380V
* Cabeamento AC: 3x Fase 10mm² + 1x Neutro 10mm²
* Disjuntor de Proteção AC: 40A
`

test('toIsoDate converte brasileiro para input date', () => {
  assert.equal(toIsoDate('18/02/1970'), '1970-02-18')
  assert.equal(toIsoDate('23/01/2030'), '2030-01-23')
})

test('formatCpf pega o primeiro CPF da linha dupla', () => {
  assert.equal(formatCpf('426.985.961-04 / 42698596104'), '426.985.961-04')
})

test('parseAddress separa rua e complemento (quadra/lote/anexo)', () => {
  const addr = parseAddress('Rua Pernambuco, Q. F, L. 5/6, Anexo Itamaraty')
  assert.equal(addr.logradouro, 'Rua Pernambuco')
  assert.match(addr.complemento, /Q\. F/)
  assert.match(addr.complemento, /Anexo Itamaraty/)
})

test('formatTelefone normaliza DDD 62 com e sem zero à esquerda', () => {
  assert.equal(formatTelefone('062991827090'), '(62) 99182-7090')
  assert.equal(formatTelefone('62991827090'), '(62) 99182-7090')
  assert.equal(formatTelefone('(62) 99182-7090'), '(62) 99182-7090')
})

test('parseTxtData — rótulo fone e formatos numéricos', () => {
  for (const line of [
    'fone: 062991827090',
    'Fone: 62991827090',
    'fone 062991827090',
    'Telefone Celular: 62991827090',
  ]) {
    const { client } = parseTxtData(line)
    assert.equal(client.telefone, '(62) 99182-7090', `falhou em: ${line}`)
  }
})

test('extrai o TXT colado do Rosembergue', () => {
  const { client, technical, modules, inverters } = parseTxtData(SAMPLE)

  assert.equal(client.client_name, 'ROSEMBERGUE LEAO E SILVA')
  assert.equal(client.cpf, '426.985.961-04')
  assert.equal(client.rg, '2372249 SSP GO')
  assert.notEqual(client.rg, '23/01/2030')
  assert.equal(client.validade_cnh, '2030-01-23')
  assert.equal(client.data_nascimento, '1970-02-18')
  assert.equal(client.logradouro, 'Rua Pernambuco')
  assert.match(client.complemento, /Anexo Itamaraty/)
  assert.equal(client.cidade, 'Anápolis')
  assert.equal(client.uf, 'GO')
  assert.equal(client.cep, '75050-270')
  assert.equal(client.consumer_unit, '000068889901235')
  assert.equal(client.email, 'doceslu@uol.com.br')
  assert.equal(client.telefone, '(62) 9274-3040')
  assert.equal(client.tensao_atendimento, '220/380V')
  assert.equal(client.tipo_ligacao, 'TRIFASICO')
  assert.equal(technical.latitude, '-16.291613')
  assert.equal(technical.longitude, '-48.973249')
  assert.equal(technical.disjuntor_entrada, '40')
  assert.equal(technical.bitola_cabo_ca, '10')
  assert.equal(modules[0].quantity, '32')
  assert.equal(modules[0].power, '680')
  assert.equal(modules[0].fabricante, 'RENEPV')
  assert.equal(inverters[0].quantity, '8')
  assert.equal(inverters[0].power, '2.25')
  assert.equal(inverters[0].fabricante, 'DEYE')
})

test('parseTxtData — ligação existente TRI 380 V e disjuntor trifásico', () => {
  const txt = `Ligação Existente: Convencional B1 / TRI - Tensão Nom.: 380 V
Disjuntor de Proteção AC: 40A Trifásico`
  const { client, technical } = parseTxtData(txt)
  assert.equal(client.tipo_ligacao, 'TRIFASICO')
  assert.equal(client.tensao_atendimento, '220/380V')
  assert.equal(client.classe, 'RESIDENCIAL')
  assert.equal(technical.disjuntor_entrada, '40')
})

test('parseTxtData — contrato e texto pagamento multilinha', () => {
  const txt = `contrato : 123/2026

texto pagamento:

O investimento objeto deste contrato é de R$ 11.500,00;

 - entrada de R$ 5.000,00 (já pagos).

restante em 18x R$ 429,03 no cartão de crédito, no início das obras.`

  const { contract } = parseTxtData(txt)
  assert.equal(contract.numero_contrato, '123/2026')
  assert.match(contract.texto_valor_pagamento_contrato, /R\$ 11\.500,00/)
  assert.match(contract.texto_valor_pagamento_contrato, /entrada de R\$ 5\.000,00/)
  assert.match(contract.texto_valor_pagamento_contrato, /18x R\$ 429,03/)
})

test('parseTxtData — coordenadas Google Earth (UTM + graus)', () => {
  const txt = `Coordenadas: 22 K 722658.18 m E 8193755.57 m S / -16.326994 -48.915886`
  const { technical } = parseTxtData(txt)
  assert.equal(technical.coordenada_utm_x, '722658.18')
  assert.equal(technical.coordenada_utm_y, '8193755.57')
  assert.equal(technical.fuso_utm, '22S')
  assert.equal(technical.latitude, '-16.326994')
  assert.equal(technical.longitude, '-48.915886')
})

test('parseTxtData — graus decimais calculam UTM (Google Earth)', () => {
  const txt = `Coordenadas georreferenciadas: -16.306664, -48.913032`
  const { technical } = parseTxtData(txt)
  assert.equal(technical.latitude, '-16.306664')
  assert.equal(technical.longitude, '-48.913032')
  assert.equal(technical.coordenada_utm_x, '722986.05')
  assert.equal(technical.coordenada_utm_y, '8196002.05')
  assert.equal(technical.fuso_utm, '22S')
})

test('parseTxtData — auditoria Google Earth faixa L (UTM + graus)', () => {
  const txt = `Coordenadas: 22 L 713364.87 m E, 8243329.38 m S / -15.879944 -49.007317`
  const { technical } = parseTxtData(txt)
  assert.equal(technical.coordenada_utm_x, '713364.87')
  assert.equal(technical.coordenada_utm_y, '8243329.38')
  assert.equal(technical.fuso_utm, '22S')
  assert.equal(technical.latitude, '-15.879944')
  assert.equal(technical.longitude, '-49.007317')
})

test('parseTxtData — auditoria faixa L: graus decimais → UTM (~1 m)', () => {
  const txt = `Coordenadas georreferenciadas: -15.879944, -49.007317`
  const { technical } = parseTxtData(txt)
  assert.equal(technical.latitude, '-15.879944')
  assert.equal(technical.longitude, '-49.007317')
  assert.equal(technical.coordenada_utm_x, '713363.95')
  assert.equal(technical.coordenada_utm_y, '8243328.96')
  assert.equal(technical.fuso_utm, '22S')
})
