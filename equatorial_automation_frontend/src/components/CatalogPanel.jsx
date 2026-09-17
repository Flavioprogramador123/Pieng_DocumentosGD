import { useCallback, useEffect, useState } from 'react'
import { ChevronDown, FileUp, Plus, RefreshCw, Save, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'

import { apiFetch } from '@/utils/api.js'

const EXEMPLO_YAML_MODULO = `# Template completo p/ IA externa → dados/modulos_solares.yaml
# Preencha todos os campos a partir do datasheet.

modulos_solares:
  - marca: FABRICANTE
    modelo_comercial: MODELO-555W
    fabricante_real: FABRICANTE
    potencia_w: 555
    bifacial: false
    eficiencia_pct: 21.5
    tecnologia: TOPCon
    voc_v: 49.5
    isc_a: 14.0
    vmp_v: 41.0
    imp_a: 13.5
    coef_temp_voc_pct_c: -0.27
    coef_temp_isc_pct_c: 0.05
    coef_temp_pmax_pct_c: -0.35
    dimensoes_mm: 2278x1134x30
    peso_kg: 27.5
    fusivel_serie_a: 25
    notas: "Datasheet"
    fonte_datasheet: ""
`

const EXEMPLO_YAML_INVERSOR = `# Template completo p/ IA externa → dados/inversores.yaml
# Preencha todos os campos a partir do datasheet.
# Exemplo: microinversor com 6 MPPT (ajuste tipo/numero_mppts).

inversores:
  - fabricante: FABRICANTE
    modelo: MICRO 2kW-6MPPT
    modelo_comercial_datasheet: MICRO-2K-6T
    tipo: Microinversor
    fase_ca: MONOFASICO
    entrada_cc:
      potencia_max_arranjo_wp: 2400
      tensao_rastreamento_mppt_v: 16 - 60
      faixa_tensao_operacao_v: 16 - 60
      tensao_entrada_max_v: 60
      corrente_entrada_cc_max_a: 78
      corrente_entrada_cc_max_a_por_mppt: [13, 13, 13, 13, 13, 13]
      numero_mppts: 6
      strings_por_mppt: [1, 1, 1, 1, 1, 1]
      topologia_tipica: "6 MPPT; 1 string por MPPT"
      micros_max_por_disjuntor_ca: 3
    saida_ca:
      potencia_max_saida_w: 2000
      corrente_saida_max_a: 9.1
      tensao_ca_nominal_faixa_v: 220 / 187 - 253
      frequencia_nominal_faixa_hz: 60/55-65
      fator_potencia: 0.99
      thd_corrente_pct: 3
    performance:
      eficiencia_pico_pct: 96.5
      eficiencia_ponderada_cec_pct: 96.0
      grau_protecao: IP67
      faixa_temperatura_c: -40 a +65
      garantia_anos: 12
    fonte_datasheet: ""
`

const TABLES = {
  modules: {
    label: 'Módulos',
    fields: [
      'fabricante', 'modelo', 'potencia_wp', 'voc', 'isc', 'vmpp', 'impp',
      'eficiencia', 'comprimento_m', 'largura_m', 'peso_kg', 'notas',
    ],
    empty: {
      fabricante: '', modelo: '', potencia_wp: '', voc: '', isc: '', vmpp: '', impp: '',
      eficiencia: '', comprimento_m: '', largura_m: '', peso_kg: '', notas: '',
    },
  },
  inverters: {
    label: 'Inversores',
    fields: [
      'fabricante', 'modelo', 'potencia_kw', 'tipo_inversor', 'fase_ca', 'num_mppt',
      'mppt_min', 'mppt_max', 'tensao_nominal', 'corrente_nominal', 'eficiencia',
      'corrente_max_cc', 'tensao_max_cc', 'potencia_max_cc_kw',
      'potencia_max_saida_ca_kw', 'corrente_max_saida_ca',
      'tensao_min_ca', 'tensao_max_ca', 'thd_pct', 'fator_potencia',
      'frequencia_hz', 'tensao_partida_cc', 'qtd_strings_max', 'notas',
    ],
    empty: {
      fabricante: '', modelo: '', potencia_kw: '', tipo_inversor: 'MICRO', fase_ca: 'MONOFASICO',
      num_mppt: '6',
      mppt_min: '', mppt_max: '', tensao_nominal: '220', corrente_nominal: '', eficiencia: '',
      corrente_max_cc: '', tensao_max_cc: '', potencia_max_cc_kw: '',
      potencia_max_saida_ca_kw: '', corrente_max_saida_ca: '',
      tensao_min_ca: '', tensao_max_ca: '', thd_pct: '', fator_potencia: '0.99',
      frequencia_hz: '60', tensao_partida_cc: '', qtd_strings_max: '', notas: '',
    },
  },
  padrao: {
    label: 'Padrão de entrada',
    fields: [
      'uf', 'tipo_ligacao', 'tensao_v', 'disjuntor_a', 'bitola_cabo_mm2',
      'dps_tipo', 'curva_disjuntor', 'dr_ma', 'notas',
    ],
    empty: {
      uf: 'GO', tipo_ligacao: 'MONOFASICO', tensao_v: '220V', disjuntor_a: '40',
      bitola_cabo_mm2: '10 mm²', dps_tipo: 'DPS Classe II', curva_disjuntor: 'C', dr_ma: '30', notas: '',
    },
  },
}

const STICKY_LEFT_FIELDS = {
  modules: ['fabricante', 'modelo'],
  inverters: ['fabricante', 'modelo'],
  padrao: ['uf', 'tipo_ligacao'],
}

/** Larguras fixas para colunas sticky à esquerda (px). */
const STICKY_COL_WIDTH = {
  fabricante: 112,
  modelo: 128,
  uf: 64,
  tipo_ligacao: 120,
}

function stickyLeftPx(tableKey, field) {
  const fields = STICKY_LEFT_FIELDS[tableKey] || []
  const idx = fields.indexOf(field)
  if (idx < 0) return null
  let left = 0
  for (let i = 0; i < idx; i += 1) {
    left += STICKY_COL_WIDTH[fields[i]] || 100
  }
  return left
}

function isStickyLeft(tableKey, field) {
  return (STICKY_LEFT_FIELDS[tableKey] || []).includes(field)
}

function stickyLeftStyle(tableKey, field, bg, zIndex = 10) {
  const left = stickyLeftPx(tableKey, field)
  if (left == null) return undefined
  const fields = STICKY_LEFT_FIELDS[tableKey] || []
  const idx = fields.indexOf(field)
  return {
    position: 'sticky',
    left: `${left}px`,
    zIndex,
    minWidth: STICKY_COL_WIDTH[field] || 100,
    maxWidth: STICKY_COL_WIDTH[field] || 100,
    backgroundColor: bg,
    boxShadow: idx > 0 ? '-3px 0 6px -4px rgba(0,0,0,0.12)' : '2px 0 6px -4px rgba(0,0,0,0.08)',
  }
}

const stickyActionsStyle = (bg, zIndex = 10) => ({
  position: 'sticky',
  right: 0,
  zIndex,
  backgroundColor: bg,
  boxShadow: '-4px 0 8px -4px rgba(0,0,0,0.12)',
})

function CatalogTable({ tableKey, reloadKey = 0 }) {
  const config = TABLES[tableKey]
  const [rows, setRows] = useState([])
  const [draft, setDraft] = useState({ ...config.empty })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const potenciaField = config.fields.includes('potencia_wp')
    ? 'potencia_wp'
    : (config.fields.includes('potencia_kw') ? 'potencia_kw' : null)
  const [sortPotencia, setSortPotencia] = useState(null) // null | 'asc' | 'desc'

  const requiredKeys = STICKY_LEFT_FIELDS[tableKey] || ['fabricante', 'modelo']

  const sortedRows = (() => {
    if (!potenciaField || !sortPotencia) return rows
    const dir = sortPotencia === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const na = Number(String(a[potenciaField] ?? '').replace(',', '.')) || 0
      const nb = Number(String(b[potenciaField] ?? '').replace(',', '.')) || 0
      return (na - nb) * dir
    })
  })()

  const toggleSortPotencia = () => {
    setSortPotencia((prev) => (prev === 'asc' ? 'desc' : 'asc'))
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch(`/catalog/${tableKey}`)
      const data = await res.json()
      if (data.success) setRows(data.rows || [])
      else setError(data.error || 'Erro ao carregar')
    } catch {
      setError('Backend offline — reinicie start_backend.bat')
    } finally {
      setLoading(false)
    }
  }, [tableKey])

  useEffect(() => { load() }, [load, reloadKey])

  const saveDraft = async () => {
    const missing = requiredKeys.filter((k) => !String(draft[k] ?? '').trim())
    if (missing.length) {
      alert(`Preencha na linha verde: ${missing.join(', ')}`)
      return
    }
    setSaving(true)
    setError('')
    try {
      const res = await apiFetch(`/catalog/${tableKey}`, {
        method: 'POST',
        body: JSON.stringify(draft),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.success) {
        alert(data.error || `Erro ao salvar (${res.status})`)
        return
      }
      const saved = data.row
      if (saved?.id != null) {
        setRows((prev) => {
          const without = prev.filter((r) => r.id !== saved.id)
          return [...without, saved]
        })
      } else {
        await load()
      }
      setDraft({ ...config.empty })
    } catch (err) {
      alert(err?.message || 'Erro ao salvar registro no SQLite')
    } finally {
      setSaving(false)
    }
  }

  const saveRow = async (row) => {
    const { id, updated_at, ...payload } = row
    const missing = requiredKeys.filter((k) => !String(payload[k] ?? '').trim())
    if (missing.length) {
      alert(`Campos obrigatórios: ${missing.join(', ')}`)
      return
    }
    try {
      const res = await apiFetch(`/catalog/${tableKey}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.success) {
        alert(data.error || `Erro ao salvar linha (${res.status})`)
        return
      }
      if (data.row?.id != null) {
        setRows((prev) => prev.map((r) => (r.id === data.row.id || (id && r.id === id) ? data.row : r)))
      } else {
        await load()
      }
    } catch (err) {
      alert(err?.message || 'Erro ao salvar linha')
    }
  }

  const removeRow = async (id) => {
    if (!confirm('Excluir este registro do catálogo?')) return
    const res = await apiFetch(`/catalog/${tableKey}/${id}`, { method: 'DELETE' })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || !data.success) {
      alert(data.error || 'Erro ao excluir')
      return
    }
    setRows((prev) => prev.filter((r) => r.id !== id))
  }

  const updateCell = (rowId, field, value) => {
    setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, [field]: value } : r)))
  }

  const updateDraft = (field, value) => {
    setDraft((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap items-center">
        <Button type="button" variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-1" /> Atualizar
        </Button>
        <Button type="button" size="sm" onClick={saveDraft} disabled={saving}>
          <Plus className="h-4 w-4 mr-1" />
          {saving ? 'Gravando…' : 'Inserir linha no SQLite'}
        </Button>
        <p className="text-xs text-muted-foreground self-center">
          Preencha a <strong>linha verde</strong> (pelo menos {requiredKeys.join(' + ')}) e clique em Inserir.
        </p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && rows.length === 0 && !error && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 space-y-1">
          <p className="font-medium">Catálogo vazio</p>
          <p>
            1) Clique em <strong>YAML módulos</strong> / <strong>YAML inversores</strong> no topo para importar
            {' '}<code className="text-xs">dados/modulos_solares.yaml</code> e <code className="text-xs">dados/inversores.yaml</code>.
          </p>
          <p>
            2) Ou cadastre agora na linha verde abaixo ({requiredKeys.join(', ')}) e pressione <strong>Inserir linha no SQLite</strong>.
          </p>
          <p>
            3) Exemplos em <code className="text-xs">dados/exemplos/</code>.
          </p>
        </div>
      )}

      <div className="overflow-x-auto border rounded-lg max-h-[min(70vh,720px)] overflow-y-auto">
        <table className="w-full text-xs border-separate border-spacing-0">
          <thead>
            <tr>
              {config.fields.map((f) => {
                const stickyLeft = isStickyLeft(tableKey, f)
                const isPotencia = f === potenciaField
                return (
                  <th
                    key={f}
                    className={`p-2 text-left whitespace-nowrap sticky top-0 bg-gray-100 ${stickyLeft ? '' : 'z-20'}`}
                    style={
                      stickyLeft
                        ? stickyLeftStyle(tableKey, f, '#f3f4f6', f === STICKY_LEFT_FIELDS[tableKey]?.[0] ? 40 : 35)
                        : undefined
                    }
                  >
                    <span className="inline-flex items-center gap-1">
                      {f}{requiredKeys.includes(f) ? ' *' : ''}
                      {isPotencia && (
                        <button
                          type="button"
                          className="text-[10px] leading-none text-muted-foreground hover:text-foreground"
                          onClick={toggleSortPotencia}
                        >
                          {sortPotencia === 'asc' ? '▲' : '▼'}
                        </button>
                      )}
                    </span>
                  </th>
                )
              })}
              <th
                className="p-2 whitespace-nowrap sticky top-0 bg-gray-100"
                style={stickyActionsStyle('#f3f4f6', 40)}
              >
                Ações
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={row.id} className="group border-t hover:bg-blue-50/20">
                {config.fields.map((f) => (
                  <td
                    key={f}
                    className="p-1"
                    style={
                      isStickyLeft(tableKey, f)
                        ? stickyLeftStyle(tableKey, f, '#ffffff', 11)
                        : undefined
                    }
                  >
                    <Input
                      className="h-8 text-xs min-w-[80px]"
                      value={row[f] ?? ''}
                      onChange={(e) => updateCell(row.id, f, e.target.value)}
                    />
                  </td>
                ))}
                <td className="p-1 whitespace-nowrap" style={stickyActionsStyle('#ffffff', 11)}>
                  <Button type="button" size="sm" variant="ghost" onClick={() => saveRow(row)} title="Salvar alterações">
                    <Save className="h-4 w-4" />
                  </Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => removeRow(row.id)} title="Excluir">
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </td>
              </tr>
            ))}
            <tr className="group border-t-2 border-green-400 bg-green-50/60">
              {config.fields.map((f) => (
                <td
                  key={f}
                  className="p-1"
                  style={
                    isStickyLeft(tableKey, f)
                      ? stickyLeftStyle(tableKey, f, '#f0fdf4', 11)
                      : undefined
                  }
                >
                  <Input
                    className="h-8 text-xs"
                    placeholder={requiredKeys.includes(f) ? `${f} *` : f}
                    value={draft[f] ?? ''}
                    onChange={(e) => updateDraft(f, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        saveDraft()
                      }
                    }}
                  />
                </td>
              ))}
              <td className="p-1" style={stickyActionsStyle('#f0fdf4', 11)}>
                <Button
                  type="button"
                  size="sm"
                  onClick={saveDraft}
                  disabled={saving}
                  title="Inserir no SQLite e na tabela"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  {saving ? '…' : 'Novo'}
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function CatalogPanel() {
  const [section, setSection] = useState('modules') // modules | inverters | padrao
  const [yamlInfo, setYamlInfo] = useState(null)
  const [invYamlInfo, setInvYamlInfo] = useState(null)
  const [yamlImporting, setYamlImporting] = useState(false)
  const [invYamlImporting, setInvYamlImporting] = useState(false)
  const [modulesReloadKey, setModulesReloadKey] = useState(0)
  const [invertersReloadKey, setInvertersReloadKey] = useState(0)
  const [modPasteYaml, setModPasteYaml] = useState(EXEMPLO_YAML_MODULO)
  const [invPasteYaml, setInvPasteYaml] = useState(EXEMPLO_YAML_INVERSOR)
  const [pasteSaving, setPasteSaving] = useState(false)
  const [saveToFile, setSaveToFile] = useState(true)
  const [yamlOpen, setYamlOpen] = useState(false)

  const isModules = section === 'modules'
  const isInverters = section === 'inverters'
  const showYaml = isModules || isInverters
  const pasteYaml = isModules ? modPasteYaml : invPasteYaml
  const setPasteYaml = isModules ? setModPasteYaml : setInvPasteYaml
  const yamlLabel = isModules ? 'módulos' : 'inversores'
  const yamlFile = isModules ? 'dados/modulos_solares.yaml' : 'dados/inversores.yaml'
  const yamlCount = isModules ? yamlInfo?.count : invYamlInfo?.count
  const importing = isModules ? yamlImporting : invYamlImporting
  const exemplo = isModules ? EXEMPLO_YAML_MODULO : EXEMPLO_YAML_INVERSOR

  const fetchYamlInfo = useCallback(async () => {
    try {
      const [modRes, invRes] = await Promise.all([
        apiFetch('/catalog/modulos-yaml-info'),
        apiFetch('/catalog/inversores-yaml-info'),
      ])
      const modData = await modRes.json()
      const invData = await invRes.json()
      if (modData.success) setYamlInfo(modData)
      if (invData.success) setInvYamlInfo(invData)
    } catch {
      setYamlInfo(null)
      setInvYamlInfo(null)
    }
  }, [])

  useEffect(() => { fetchYamlInfo() }, [fetchYamlInfo])

  const importYamlFile = async () => {
    if (isModules) {
      setYamlImporting(true)
      try {
        const res = await apiFetch('/catalog/import-modulos-yaml', { method: 'POST' })
        const data = await res.json()
        if (data.success) {
          alert(`Importados ${data.imported} módulos de:\n${data.source || data.yaml_path}`)
          setModulesReloadKey((k) => k + 1)
          fetchYamlInfo()
        } else {
          alert(data.error || 'Erro ao importar YAML')
        }
      } catch {
        alert('Backend offline — reinicie start_backend.bat')
      } finally {
        setYamlImporting(false)
      }
      return
    }
    setInvYamlImporting(true)
    try {
      const res = await apiFetch('/catalog/import-inversores-yaml', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        alert(`Importados ${data.imported} inversores de:\n${data.source || data.yaml_path}`)
        setInvertersReloadKey((k) => k + 1)
        fetchYamlInfo()
      } else {
        alert(data.error || 'Erro ao importar YAML')
      }
    } catch {
      alert('Backend offline — reinicie start_backend.bat')
    } finally {
      setInvYamlImporting(false)
    }
  }

  const savePastedYaml = async () => {
    if (!pasteYaml.trim()) {
      alert(`Cole o YAML de ${yamlLabel} antes de gravar.`)
      return
    }
    setPasteSaving(true)
    try {
      const endpoint = isModules
        ? '/catalog/import-modulos-yaml'
        : '/catalog/import-inversores-yaml'
      const res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ yaml: pasteYaml, save_file: saveToFile }),
      })
      const data = await res.json()
      setPasteSaving(false)
      if (!res.ok || data.success === false) {
        alert(data.error || 'Erro ao gravar YAML')
        return
      }
      const where = data.saved_path || data.yaml_path || data.source || 'SQLite'
      if (isModules) setModulesReloadKey((k) => k + 1)
      else setInvertersReloadKey((k) => k + 1)
      fetchYamlInfo()
      alert(
        `Gravado com sucesso: ${data.imported} ${yamlLabel} no catálogo.`
        + (saveToFile ? `\nArquivo: ${where}` : '\nSomente SQLite (arquivo não alterado).')
        + (data.errors?.length ? `\nAvisos:\n• ${data.errors.join('\n• ')}` : ''),
      )
    } catch {
      setPasteSaving(false)
      alert('Backend offline — reinicie start_backend.bat')
    }
  }

  const navBtn = (id, label) => (
    <button
      key={id}
      type="button"
      onClick={() => setSection(id)}
      className={`rounded-md px-4 py-2 text-sm whitespace-nowrap transition-colors ${
        section === id
          ? 'bg-primary text-primary-foreground'
          : 'hover:bg-muted text-foreground'
      }`}
    >
      {label}
    </button>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Catálogo técnico (SQLite)</CardTitle>
        <CardDescription>
          Escolha Módulos ou Inversores no topo — YAML e tabela acompanham a escolha.
          Template completo para IA externa em <code className="text-xs">dados/exemplos/</code>.
        </CardDescription>
        <div className="flex flex-wrap gap-1 border rounded-lg p-1 bg-muted/20 w-fit mt-2">
          {navBtn('modules', 'Módulos')}
          {navBtn('inverters', 'Inversores')}
          {navBtn('padrao', 'Padrão entrada')}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {showYaml && (
            <div className="space-y-2 rounded-lg border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className="inline-flex items-center gap-1 text-sm font-medium capitalize"
                  onClick={() => setYamlOpen((o) => !o)}
                >
                  <ChevronDown className={`h-4 w-4 transition-transform ${yamlOpen ? '' : '-rotate-90'}`} />
                  YAML — {yamlLabel}
                </button>
                <span className="text-xs text-muted-foreground">
                  {yamlFile}{yamlCount != null ? ` · ${yamlCount} no arquivo` : ''}
                </span>
                <Button type="button" variant="outline" size="sm" className="ml-auto" onClick={importYamlFile} disabled={importing}>
                  <FileUp className="h-4 w-4 mr-1" />
                  {importing ? 'Importando…' : 'Importar arquivo'}
                </Button>
              </div>
              {yamlOpen && (
                <>
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={saveToFile}
                      onChange={(e) => setSaveToFile(e.target.checked)}
                    />
                    Gravar também no arquivo
                  </label>
                  <Textarea
                    className="font-mono text-xs min-h-[220px]"
                    placeholder={`Cole YAML de ${yamlLabel} (template completo para IA)…`}
                    value={pasteYaml}
                    onChange={(e) => setPasteYaml(e.target.value)}
                  />
                  <div className="flex gap-2 flex-wrap">
                    <Button type="button" size="sm" onClick={savePastedYaml} disabled={pasteSaving}>
                      <Save className="h-4 w-4 mr-1" />
                      {pasteSaving ? 'Gravando…' : `Gravar ${yamlLabel}`}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setPasteYaml(exemplo)}
                    >
                      Restaurar template
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}

          {section === 'modules' && (
            <CatalogTable tableKey="modules" reloadKey={modulesReloadKey} />
          )}
          {section === 'inverters' && (
            <CatalogTable tableKey="inverters" reloadKey={invertersReloadKey} />
          )}
          {section === 'padrao' && (
            <CatalogTable tableKey="padrao" />
          )}
        </div>
      </CardContent>
    </Card>
  )
}
