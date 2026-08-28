import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  parseTxtData,
  toIsoDate,
  formatCpf,
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
  assert.equal(client.telefone, '62 9274-3040')
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
