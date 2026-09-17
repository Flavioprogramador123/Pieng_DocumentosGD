import { Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'

function _fmt(n) {
  if (n == null || n === '') return '—'
  return String(n).replace('.', ',')
}

function demandToTsv(demand) {
  const lines = [demand.headers.join('\t')]
  for (const row of demand.rows) {
    lines.push([
      row.item,
      row.descricao,
      row.pot_unit_w,
      row.qtd,
      _fmt(row.ci_kw),
      _fmt(row.fp),
      _fmt(row.ci_kva),
      `${Math.round(row.fd * 100)}%`,
      _fmt(row.d_kw),
      _fmt(row.d_kva),
    ].join('\t'))
  }
  lines.push([
    'TOTAL',
    'Demanda de projeto — conferir no local',
    '—',
    '—',
    _fmt(demand.totals.ci_kw),
    '—',
    _fmt(demand.totals.ci_kva),
    '—',
    _fmt(demand.totals.d_kw),
    _fmt(demand.totals.d_kva),
  ].join('\t'))
  return lines.join('\n')
}

function CopyButton({ text, label = 'Copiar' }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      alert('Não foi possível copiar.')
    }
  }
  return (
    <Button type="button" variant="outline" size="sm" onClick={handleCopy}>
      {copied ? <Check className="h-4 w-4 mr-1" /> : <Copy className="h-4 w-4 mr-1" />}
      {copied ? 'Copiado!' : label}
    </Button>
  )
}

function MetricCard({ label, value, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    yellow: 'bg-yellow-50 text-yellow-800',
    purple: 'bg-purple-50 text-purple-700',
    orange: 'bg-orange-50 text-orange-700',
  }
  return (
    <div className={`p-4 rounded-lg ${colors[color] || colors.blue}`}>
      <p className="text-sm opacity-80">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  )
}

function displayValor(item, overrides) {
  const token = item?.token
  if (token && overrides && Object.prototype.hasOwnProperty.call(overrides, token)) {
    return overrides[token]
  }
  return item?.valor ?? ''
}

export function CalculationsResults({
  calculations,
  onApplyToForm,
  tokenOverrides = {},
  onTokenOverrideChange,
}) {
  if (!calculations) return null

  const ps = calculations.power_summary || {}
  const gen = calculations.generation || {}
  const compat = calculations.compatibility || {}
  const demand = calculations.demand_table
  const allItems = calculations.all_items || []
  const editable = typeof onTokenOverrideChange === 'function'

  const groups = allItems.reduce((acc, item) => {
    const g = item.grupo || 'Outros'
    if (!acc[g]) acc[g] = []
    acc[g].push(item)
    return acc
  }, {})

  const overrideCount = Object.keys(tokenOverrides || {}).length

  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-lg font-semibold mb-3">Potências e geração</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <MetricCard label="Módulos" value={`${ps.total_module_power_kw ?? calculations.total_module_power_kw} kWp`} color="blue" />
          <MetricCard label="Inversores" value={`${ps.total_inverter_power_kw ?? calculations.total_inverter_power_kw} kW`} color="green" />
          <MetricCard label="Relação DC/AC" value={ps.power_ratio ?? calculations.relacao_modulo_inversor} color="purple" />
          <MetricCard label="Geração mensal" value={`${gen.monthly_generation_kwh ?? calculations.estimated_monthly_generation} kWh`} color="yellow" />
          <MetricCard label="Geração anual" value={`${gen.annual_generation_kwh ?? calculations.estimated_annual_generation} kWh`} color="orange" />
          <MetricCard label="Economia est." value={`R$ ${calculations.economia_mensal_estimada}`} color="green" />
        </div>
      </section>

      {compat && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Compatibilidade</h3>
          <div className={`p-4 rounded-lg border ${
            compat.status === 'OK' ? 'bg-green-50 border-green-200' :
            compat.status === 'ATENÇÃO' ? 'bg-yellow-50 border-yellow-200' :
            'bg-red-50 border-red-200'
          }`}>
            <p className="font-semibold">Status: {compat.status}</p>
            {compat.message && <p className="text-sm mt-1">{compat.message}</p>}
            {(compat.warnings || []).map((w, i) => <p key={i} className="text-sm text-amber-800">• {w}</p>)}
            {(compat.errors || []).map((e, i) => <p key={i} className="text-sm text-red-800">• {e}</p>)}
          </div>
        </section>
      )}

      {(calculations.cable_warnings || []).length > 0 && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Cabos — conferência</h3>
          <div className="p-4 rounded-lg border bg-amber-50 border-amber-200">
            <p className="text-sm font-medium mb-2">
              Valores do formulário mantidos. Recomendações do dimensionamento:
            </p>
            {(calculations.cable_warnings || []).map((w, i) => (
              <p key={i} className="text-sm text-amber-900">• {w}</p>
            ))}
            {calculations.cables?.recommended_cc && (
              <p className="text-xs mt-2 text-gray-600">
                Sugerido: CC {calculations.cables.recommended_cc} · CA {calculations.cables.recommended_ca}
                {calculations.cables.recommended_padrao
                  ? ` · Padrão ${calculations.cables.recommended_padrao}`
                  : ''}
              </p>
            )}
          </div>
        </section>
      )}

      <section>
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h3 className="text-lg font-semibold">Todos os cálculos do sistema</h3>
          {editable && (
            <p className="text-xs text-muted-foreground">
              Valores com token são editáveis — o que você ajustar vai para o documento final.
              {overrideCount > 0 ? ` (${overrideCount} alterado${overrideCount > 1 ? 's' : ''})` : ''}
            </p>
          )}
        </div>
        <div className="space-y-4">
          {Object.entries(groups).map(([grupo, items]) => (
            <div key={grupo} className="border rounded-lg overflow-hidden">
              <div className="bg-gray-100 px-3 py-2 text-sm font-semibold">{grupo}</div>
              <table className="w-full text-sm">
                <tbody>
                  {items.map((item, idx) => {
                    const token = item.token
                    const valor = displayValor(item, tokenOverrides)
                    const edited = token && Object.prototype.hasOwnProperty.call(tokenOverrides || {}, token)
                    return (
                      <tr key={`${token || item.rotulo}-${idx}`} className="border-t">
                        <td className="p-2 text-gray-700 w-1/2">{item.rotulo}</td>
                        <td className="p-2 font-medium">
                          {editable && token ? (
                            <Input
                              className={`h-8 text-sm ${edited ? 'border-amber-400 bg-amber-50/50' : ''}`}
                              value={valor}
                              onChange={(e) => onTokenOverrideChange(token, e.target.value, item)}
                            />
                          ) : (
                            valor
                          )}
                        </td>
                        <td className="p-2 text-xs font-mono text-blue-600 w-28 whitespace-nowrap">
                          {token ? `{{${token}}}` : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>

      {calculations.dc_strings && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Strings CC (física correta)</h3>
          <div className={`p-4 rounded-lg border ${
            calculations.dc_strings.status === 'OK' ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'
          }`}>
            <p className="text-sm"><strong>Topologia:</strong> {calculations.dc_strings.topology}</p>
            <p className="text-sm">Voc string: {calculations.dc_strings.string_voc_v} V · Isc string: {calculations.dc_strings.string_isc_a} A (não soma em série)</p>
            <p className="text-sm">Isc projeto: {calculations.dc_strings.isc_design_a} A · {calculations.dc_strings.cable_cc_note}</p>
            {calculations.dc_strings.configuracao_strings_text && (
              <p className="text-sm mt-2"><strong>Config.:</strong> {calculations.dc_strings.configuracao_strings_text}</p>
            )}
            {calculations.dc_strings.protecao_cc_text && (
              <p className="text-sm"><strong>Prot. CC:</strong> {calculations.dc_strings.protecao_cc_text}</p>
            )}
            {calculations.dc_strings.protecao_ca_text && (
              <p className="text-sm"><strong>Prot. CA:</strong> {calculations.dc_strings.protecao_ca_text}</p>
            )}
            {(calculations.dc_strings.messages || []).map((m, i) => (
              <p key={i} className="text-xs mt-1 text-gray-700">• {m}</p>
            ))}
          </div>
        </section>
      )}

      {demand && (
        <section>
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 className="text-lg font-semibold">
              Tabela 1 – Levantamento de Carga
              {demand.calculated_d_kw != null ? (
                <span className="text-base font-normal text-gray-700">
                  {' '}— calculada {_fmt(demand.calculated_d_kw)} kW
                  {demand.target_kw ? ` (alvo ${_fmt(demand.target_kw)} kW)` : ''}
                </span>
              ) : (
                <span> ({_fmt(demand.target_kw)} kW)</span>
              )}
            </h3>
            <div className="flex gap-2 flex-wrap">
              <Badge variant="outline">{demand.source}</Badge>
              <CopyButton text={demandToTsv(demand)} label="Copiar TSV (Word)" />
              <CopyButton text={demand.memorial_text} label="Copiar texto" />
              {onApplyToForm && (
                <Button type="button" variant="secondary" size="sm" onClick={() => onApplyToForm(demand)}>
                  Aplicar ao formulário
                </Button>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-600 mb-2">
            {demand.disclaimer}
            {demand.fit_note && (
              <span className="block mt-1 text-green-800 font-medium">{demand.fit_note}</span>
            )}
            {' '}Ao gerar o memorial, a tabela entra formatada no Word. Para colar manualmente:
            use &quot;Copiar TSV&quot; → colar no Word → Inserir → Tabela → Converter texto em tabela (separador: tabulação).
          </p>
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full text-xs border-collapse min-w-[720px]">
              <thead className="bg-gray-100">
                <tr>
                  {demand.headers.map((h) => (
                    <th key={h} className="p-2 border text-left whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {demand.rows.map((row) => (
                  <tr key={row.item} className="hover:bg-blue-50/30">
                    <td className="p-2 border">{row.item}</td>
                    <td className="p-2 border">{row.descricao}</td>
                    <td className="p-2 border text-right">{row.pot_unit_w}</td>
                    <td className="p-2 border text-right">{row.qtd}</td>
                    <td className="p-2 border text-right">{_fmt(row.ci_kw)}</td>
                    <td className="p-2 border text-right">{_fmt(row.fp)}</td>
                    <td className="p-2 border text-right">{_fmt(row.ci_kva)}</td>
                    <td className="p-2 border text-right">{Math.round(row.fd * 100)}%</td>
                    <td className="p-2 border text-right font-medium">{_fmt(row.d_kw)}</td>
                    <td className="p-2 border text-right">{_fmt(row.d_kva)}</td>
                  </tr>
                ))}
                <tr className="bg-gray-50 font-bold">
                  <td className="p-2 border" colSpan={2}>TOTAL</td>
                  <td className="p-2 border text-center" colSpan={2}>—</td>
                  <td className="p-2 border text-right">{_fmt(demand.totals.ci_kw)}</td>
                  <td className="p-2 border">—</td>
                  <td className="p-2 border text-right">{_fmt(demand.totals.ci_kva)}</td>
                  <td className="p-2 border">—</td>
                  <td className="p-2 border text-right text-green-700">{_fmt(demand.totals.d_kw)}</td>
                  <td className="p-2 border text-right">{_fmt(demand.totals.d_kva)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="mt-3">
            <p className="text-xs font-semibold text-gray-700 mb-1">Texto para colar no memorial descritivo</p>
            <Textarea readOnly value={demand.memorial_text} rows={12} className="font-mono text-xs" />
          </div>
        </section>
      )}

      {calculations.demand_table_error && (
        <p className="text-sm text-red-600">Erro na tabela de demanda: {calculations.demand_table_error}</p>
      )}
    </div>
  )
}
