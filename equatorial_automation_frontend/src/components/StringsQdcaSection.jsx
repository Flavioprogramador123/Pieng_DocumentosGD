import { useMemo } from 'react'

import { Button } from '@/components/ui/button.jsx'

import { Input } from '@/components/ui/input.jsx'

import { Label } from '@/components/ui/label.jsx'

import { Textarea } from '@/components/ui/textarea.jsx'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'

import {

  estimateInverterProjectCurrentA,

  estimatePhaseBreakerA,

  estimatePhaseProjectCurrentA,

  inverterPowerKw,

  isSingleInverterCoupling,

  networkPhases,

  shouldOfferCouplingBreaker,

  suggestMicroPhaseCounts,

  suggestQdcaFields,

  mergeSuggestedQdcaFields,

  sumPhaseMicros,

  totalInverters,

  totalModules,

} from '@/utils/qdcaLayout.js'



const isTruthy = (v) => ['1', 'true', 'sim', 'yes', 'on'].includes(String(v || '').toLowerCase())



export default function StringsQdcaSection({

  technicalData,

  setTechnicalData,

  clientData,

  modules,

  inverters,

  calculations,

}) {

  const isMicro = String(technicalData.tipo_inversor || '').toUpperCase() === 'MICRO'

  const tipoLig = clientData?.tipo_ligacao || 'MONOFASICO'

  const isTri = String(tipoLig).toUpperCase().includes('TRIF')

  const { labels } = networkPhases(tipoLig)

  const nInv = totalInverters(inverters)

  const nMod = totalModules(modules)

  const pInv = inverterPowerKw(inverters)

  const phaseSum = sumPhaseMicros(technicalData, tipoLig)

  const dc = calculations?.dc_strings

  const defaultBitola = technicalData.bitola_cabo_ca || '6'

  const offerCoupling = shouldOfferCouplingBreaker(nInv)

  const hasCoupling = isTruthy(technicalData.qdca_tem_disj_acoplamento)

  const singleCoupling = isSingleInverterCoupling(nInv)



  const mpptTotal = useMemo(() => {

    const perInv = parseInt(technicalData.num_mppt, 10) || 0

    if (perInv > 0 && nInv > 0) return perInv * nInv

    return dc?.mppt_total || dc?.mppt_used || '—'

  }, [technicalData.num_mppt, nInv, dc])



  const applyAutoQdca = () => {
    const patch = suggestQdcaFields({ technical: technicalData, client: clientData, modules, inverters })
    setTechnicalData((prev) => ({ ...prev, ...mergeSuggestedQdcaFields(prev, patch) }))
  }

  const rebalancePhases = () => {
    const patch = suggestMicroPhaseCounts(nInv, tipoLig)
    const breakers = {}
    const correntes = {}
    labels.forEach((label) => {
      const micros = patch[`qdca_micros_fase_${label.toLowerCase()}`]
      const lb = label.toLowerCase()
      if (micros) {
        breakers[`qdca_disj_fase_${lb}`] = estimatePhaseBreakerA(micros, pInv)
        correntes[`qdca_corrente_proj_fase_${lb}`] = estimatePhaseProjectCurrentA(micros, pInv)
      }
    })
    setTechnicalData((prev) => ({
      ...prev,
      ...patch,
      ...mergeSuggestedQdcaFields(prev, breakers),
      ...correntes,
      qdca_num_dps: prev.qdca_num_dps || String(labels.length),
    }))
  }

  const updatePhaseMicros = (label, value) => {
    const lb = label.toLowerCase()
    const key = `qdca_micros_fase_${lb}`
    const disjKey = `qdca_disj_fase_${lb}`
    const iProjKey = `qdca_corrente_proj_fase_${lb}`
    setTechnicalData((prev) => {
      const next = {
        ...prev,
        [key]: value,
        [iProjKey]: value ? estimatePhaseProjectCurrentA(value, pInv) : '',
      }
      if (value && !String(prev[disjKey] || '').trim()) {
        next[disjKey] = estimatePhaseBreakerA(value, pInv)
      }
      return next
    })
  }



  const enableCoupling = () => {

    setTechnicalData((prev) => ({

      ...prev,

      qdca_tem_disj_acoplamento: '1',

      qdca_disjuntor_geral: prev.qdca_disjuntor_geral || (isTri ? '50' : '40'),

      qdca_bitola_tronco: prev.qdca_bitola_tronco || '10',

    }))

  }



  const disableCoupling = () => {

    setTechnicalData((prev) => ({

      ...prev,

      qdca_tem_disj_acoplamento: '0',

    }))

  }



  return (

    <div className="border-t pt-6 space-y-6">

      <div>

        <h3 className="text-lg font-semibold">Strings CC / MPPT — equipamento solar</h3>

        <p className="text-sm text-muted-foreground mt-1">

          Configuração da usina (independente do padrão de entrada da UC). Micro: 1 módulo/MPPT, saída mono 220 V F-N.

          String: informe módulos/string e strings/MPPT ou deixe em branco para sugestão automática.

        </p>

      </div>



      <div className="rounded-md border bg-muted/30 p-3 text-sm grid grid-cols-2 md:grid-cols-4 gap-2">

        <div><span className="text-muted-foreground">Módulos:</span> <strong>{nMod || '—'}</strong></div>

        <div><span className="text-muted-foreground">Inversores:</span> <strong>{nInv || '—'}</strong></div>

        <div><span className="text-muted-foreground">MPPT total:</span> <strong>{mpptTotal}</strong></div>

        <div><span className="text-muted-foreground">Topologia:</span> <strong>{dc?.topology || (isMicro ? 'micro' : '—')}</strong></div>

      </div>



      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

        <div>

          <Label>Tipo de inversor</Label>

          <Select

            value={technicalData.tipo_inversor || 'STRING'}

            onValueChange={(v) => {
              setTechnicalData((prev) => ({
                ...prev,
                tipo_inversor: v,
                modulos_por_string: v === 'MICRO' ? '1' : prev.modulos_por_string,
                strings_por_mppt: v === 'MICRO' ? '1' : prev.strings_por_mppt,
                ...(v === 'MICRO' && (!prev.num_mppt || prev.num_mppt === '2')
                  ? { num_mppt: '4' }
                  : {}),
              }))
            }}

          >

            <SelectTrigger><SelectValue /></SelectTrigger>

            <SelectContent>

              <SelectItem value="STRING">String / central</SelectItem>

              <SelectItem value="MICRO">Microinversor</SelectItem>

            </SelectContent>

          </Select>

        </div>

        <div>

          <Label>MPPT por inversor</Label>

          <Input

            type="number"

            min="1"

            value={technicalData.num_mppt}

            onChange={(e) => setTechnicalData({ ...technicalData, num_mppt: e.target.value })}

            placeholder="2"

          />

          <p className="text-xs text-muted-foreground mt-1">Total MPPT = {mpptTotal}</p>

        </div>

        {!isMicro && (

          <>

            <div>

              <Label>Módulos por string</Label>

              <Input

                type="number"

                min="1"

                value={technicalData.modulos_por_string}

                onChange={(e) => setTechnicalData({ ...technicalData, modulos_por_string: e.target.value })}

                placeholder={dc?.modules_per_string ? String(dc.modules_per_string) : 'Auto'}

              />

            </div>

            <div>

              <Label>Strings em paralelo / MPPT</Label>

              <Input

                type="number"

                min="1"

                value={technicalData.strings_por_mppt}

                onChange={(e) => setTechnicalData({ ...technicalData, strings_por_mppt: e.target.value })}

                placeholder={dc?.strings_per_mppt ? String(dc.strings_per_mppt) : 'Auto'}

              />

            </div>

          </>

        )}

        {isMicro && (

          <div>

            <Label>Máx. micros por disjuntor CA</Label>

            <Select

              value={String(technicalData.micros_por_grupo_ca || '3')}

              onValueChange={(v) => setTechnicalData({ ...technicalData, micros_por_grupo_ca: v })}

            >

              <SelectTrigger><SelectValue /></SelectTrigger>

              <SelectContent>

                <SelectItem value="1">1 (1 disjuntor/micro)</SelectItem>

                <SelectItem value="2">2 em paralelo</SelectItem>

                <SelectItem value="3">3 em paralelo (máx.)</SelectItem>

              </SelectContent>

            </Select>

          </div>

        )}

      </div>



      {dc?.configuracao_strings_text && (

        <p className="text-xs text-muted-foreground border-l-2 border-primary/40 pl-3">

          {dc.configuracao_strings_text}

        </p>

      )}



      <div className="border rounded-lg p-4 space-y-4 bg-card">

        <div className="flex flex-wrap items-center justify-between gap-2">

          <div>

            <h4 className="font-semibold">QDCA — proteção CA da usina</h4>

            <p className="text-xs text-muted-foreground">

              O que você definir aqui vai para o memorial e reflete o que será montado no campo.

              Não altera o disjuntor geral do padrão de entrada da UC.

            </p>

          </div>

          <div className="flex gap-2">

            <Button type="button" variant="outline" size="sm" onClick={applyAutoQdca}>

              Sugerir QDCA

            </Button>

            {isMicro && isTri && (

              <Button type="button" variant="outline" size="sm" onClick={rebalancePhases}>

                Balancear fases

              </Button>

            )}

          </div>

        </div>



        {singleCoupling && (

          <p className="text-xs rounded-md bg-muted/50 border px-3 py-2">

            <strong>1 equipamento:</strong> o disjuntor do inversor/micro já funciona como proteção de acoplamento.

            Disjuntor de acoplamento (DJG) separado não é necessário.

          </p>

        )}



        {isMicro ? (

          <>

            <p className="text-sm">

              Rede <strong>{tipoLig}</strong> — distribua os <strong>{nInv}</strong> micro-inversor(es).

              {isTri

                ? ' Pode concentrar até 3 micros no mesmo disjuntor/fase (economia de cabo).'

                : ' Monofásico: uma fase; vários micros no mesmo ramal.'}

              {phaseSum > 0 && phaseSum !== nInv && (

                <span className="text-destructive ml-1">

                  (soma {phaseSum} ≠ {nInv} inversores)

                </span>

              )}

            </p>

            <div className="overflow-x-auto">

              <table className="w-full text-sm border-collapse">

                <thead>

                  <tr className="border-b text-left text-muted-foreground">

                    <th className="py-2 pr-3">Fase</th>

                    <th className="py-2 pr-3">Qtd micros</th>

                    <th className="py-2 pr-3">Disjuntor (A)</th>

                    <th className="py-2 pr-3">Cabo (mm²)</th>

                    <th className="py-2 pr-3">I projeto (A)</th>

                    <th className="py-2">DPS</th>

                  </tr>

                </thead>

                <tbody>

                  {labels.map((label) => (

                    <tr key={label} className="border-b border-border/50">

                      <td className="py-2 pr-3 font-medium">Fase {label}</td>

                      <td className="py-2 pr-3">

                        <Input

                          type="number"

                          min="0"

                          className="w-20 h-8"

                          value={technicalData[`qdca_micros_fase_${label.toLowerCase()}`] || ''}

                          onChange={(e) => updatePhaseMicros(label, e.target.value)}

                        />

                      </td>

                      <td className="py-2 pr-3">

                        <Input

                          type="number"

                          min="1"

                          className="w-20 h-8"

                          value={technicalData[`qdca_disj_fase_${label.toLowerCase()}`] || ''}

                          onChange={(e) => setTechnicalData({

                            ...technicalData,

                            [`qdca_disj_fase_${label.toLowerCase()}`]: e.target.value,

                          })}

                          placeholder="32"

                        />

                      </td>

                      <td className="py-2 pr-3">

                        <Input

                          className="w-20 h-8"

                          value={technicalData[`qdca_bitola_fase_${label.toLowerCase()}`] || ''}

                          onChange={(e) => setTechnicalData({

                            ...technicalData,

                            [`qdca_bitola_fase_${label.toLowerCase()}`]: e.target.value,

                          })}

                          placeholder={defaultBitola}

                        />

                      </td>

                      <td className="py-2 pr-3">

                        <Input

                          className="w-24 h-8"

                          value={technicalData[`qdca_corrente_proj_fase_${label.toLowerCase()}`] || ''}

                          onChange={(e) => setTechnicalData({

                            ...technicalData,

                            [`qdca_corrente_proj_fase_${label.toLowerCase()}`]: e.target.value,

                          })}

                          placeholder="—"

                        />

                      </td>

                      <td className="py-2 text-muted-foreground text-xs">1 DPS</td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          </>

        ) : (

          <div className="space-y-3">

            <p className="text-sm text-muted-foreground">

              Inversor string — {nInv} equipamento(s) na rede <strong>{tipoLig}</strong>.

            </p>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

              <div>

                <Label>Disjuntor CA (A)</Label>

                <Input

                  type="number"

                  min="1"

                  value={technicalData.qdca_disjuntor_ca || ''}

                  onChange={(e) => setTechnicalData({ ...technicalData, qdca_disjuntor_ca: e.target.value })}

                  placeholder={
                    calculations?.disjuntor_inversor_ca_a
                      ? String(calculations.disjuntor_inversor_ca_a)
                      : '32'
                  }

                />

                {!technicalData.qdca_disjuntor_ca && calculations?.disjuntor_inversor_ca_a ? (

                  <p className="text-[10px] text-muted-foreground mt-1">

                    Calculado: {calculations.disjuntor_inversor_ca_a} A — use «Sugerir QDCA» ou recalcule

                  </p>

                ) : null}

              </div>

              <div>

                <Label>Cabo CA (mm²)</Label>

                <Input

                  value={technicalData.qdca_bitola_ca || ''}

                  onChange={(e) => setTechnicalData({ ...technicalData, qdca_bitola_ca: e.target.value })}

                  placeholder={defaultBitola}

                />

              </div>

              <div>

                <Label>I projeto (A)</Label>

                <Input

                  value={technicalData.qdca_corrente_proj || ''}

                  onChange={(e) => setTechnicalData({ ...technicalData, qdca_corrente_proj: e.target.value })}

                  placeholder={estimateInverterProjectCurrentA(pInv, 220, isTri, 380) || '—'}

                />

              </div>

              <div>

                <Label>DPS CA</Label>

                <Input

                  type="number"

                  min="1"

                  value={technicalData.qdca_num_dps || ''}

                  onChange={(e) => setTechnicalData({ ...technicalData, qdca_num_dps: e.target.value })}

                  placeholder={String(Math.max(1, nInv))}

                />

              </div>

            </div>

          </div>

        )}



        {offerCoupling && (

          <div className="border-t pt-4 space-y-3">

            <div className="flex flex-wrap items-center gap-2">

              <span className="text-sm font-medium">Disjuntor de acoplamento (DJG)</span>

              {!hasCoupling ? (

                <Button type="button" variant="secondary" size="sm" onClick={enableCoupling}>

                  + Incluir disjuntor de acoplamento

                </Button>

              ) : (

                <Button type="button" variant="ghost" size="sm" onClick={disableCoupling}>

                  Remover acoplamento

                </Button>

              )}

            </div>

            {hasCoupling && (

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 rounded-md bg-muted/30 p-3">

                <div>

                  <Label>DJG — disjuntor (A)</Label>

                  <Input

                    type="number"

                    min="1"

                    value={technicalData.qdca_disjuntor_geral || ''}

                    onChange={(e) => setTechnicalData({ ...technicalData, qdca_disjuntor_geral: e.target.value })}

                    placeholder={isTri ? '50' : '40'}

                  />

                  <p className="text-xs text-muted-foreground mt-1">Seccionamento da usina (não confundir com padrão UC)</p>

                </div>

                <div>

                  <Label>Cabo tronco QDCA → acoplamento (mm²)</Label>

                  <Input

                    value={technicalData.qdca_bitola_tronco || ''}

                    onChange={(e) => setTechnicalData({ ...technicalData, qdca_bitola_tronco: e.target.value })}

                    placeholder="10"

                  />

                </div>

                <div>

                  <Label>I projeto tronco (A)</Label>

                  <Input

                    value={technicalData.qdca_corrente_proj_tronco || ''}

                    onChange={(e) => setTechnicalData({ ...technicalData, qdca_corrente_proj_tronco: e.target.value })}

                    placeholder="opcional"

                  />

                </div>

              </div>

            )}

            {!hasCoupling && (

              <p className="text-xs text-muted-foreground">

                Com mais de um equipamento, você pode acoplar direto à rede (sem DJG) ou incluir o disjuntor de seccionamento.

              </p>

            )}

          </div>

        )}



        <div>

          <Label>Observações QDCA (memorial / unifilar)</Label>

          <Textarea

            rows={2}

            value={technicalData.qdca_observacoes || ''}

            onChange={(e) => setTechnicalData({ ...technicalData, qdca_observacoes: e.target.value })}

            placeholder="Ex.: QDCA com 3 disjuntores e 3 DPS Classe II 275 Vca…"

          />

        </div>

      </div>

    </div>

  )

}


