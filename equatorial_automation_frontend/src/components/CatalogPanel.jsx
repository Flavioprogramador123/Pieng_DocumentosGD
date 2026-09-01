import { useCallback, useEffect, useState } from 'react'
import { FileUp, Plus, RefreshCw, Save, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'

import { apiFetch } from '@/utils/api.js'

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
      'fabricante', 'modelo', 'potencia_kw', 'tipo_inversor', 'num_mppt',
      'mppt_min', 'mppt_max', 'tensao_nominal', 'corrente_nominal', 'eficiencia',
      'corrente_max_cc', 'tensao_max_cc', 'potencia_max_cc_kw',
      'potencia_max_saida_ca_kw', 'corrente_max_saida_ca',
      'tensao_min_ca', 'tensao_max_ca', 'thd_pct', 'fator_potencia',
      'frequencia_hz', 'tensao_partida_cc', 'qtd_strings_max', 'notas',
    ],
    empty: {
      fabricante: '', modelo: '', potencia_kw: '', tipo_inversor: 'STRING', num_mppt: '2',
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
  const [error, setError] = useState('')

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
    try {
      const res = await apiFetch(`/catalog/${tableKey}`, {
        method: 'POST',
        body: JSON.stringify(draft),
      })
      const data = await res.json()
      if (data.success) {
        setDraft({ ...config.empty })
        load()
      } else {
        alert(data.error || 'Erro ao salvar')
      }
    } catch {
      alert('Erro ao salvar registro')
    }
  }

  const saveRow = async (row) => {
    const { id, updated_at, ...payload } = row
    const res = await apiFetch(`/catalog/${tableKey}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    if (!data.success) alert(data.error || 'Erro ao salvar linha')
    else load()
  }

  const removeRow = async (id) => {
    if (!confirm('Excluir este registro do catálogo?')) return
    await apiFetch(`/catalog/${tableKey}/${id}`, { method: 'DELETE' })
    load()
  }

  const updateCell = (rowId, field, value) => {
    setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, [field]: value } : r)))
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button type="button" variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-1" /> Atualizar
        </Button>
        <p className="text-xs text-muted-foreground self-center">
          Banco SQLite local — reutilizado antes da IA em projetos semelhantes.
        </p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto border rounded-lg max-h-[min(70vh,720px)] overflow-y-auto">
        <table className="w-full text-xs border-separate border-spacing-0">
          <thead>
            <tr>
              {config.fields.map((f) => {
                const stickyLeft = isStickyLeft(tableKey, f)
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
                    {f}
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
            {rows.map((row) => (
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
                  <Button type="button" size="sm" variant="ghost" onClick={() => saveRow(row)}>
                    <Save className="h-4 w-4" />
                  </Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => removeRow(row.id)}>
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </td>
              </tr>
            ))}
            <tr className="group border-t bg-green-50/40">
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
                    placeholder="novo"
                    value={draft[f] ?? ''}
                    onChange={(e) => setDraft({ ...draft, [f]: e.target.value })}
                  />
                </td>
              ))}
              <td className="p-1" style={stickyActionsStyle('#f0fdf4', 11)}>
                <Button type="button" size="sm" onClick={saveDraft}>
                  <Plus className="h-4 w-4" />
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
  const [yamlInfo, setYamlInfo] = useState(null)
  const [invYamlInfo, setInvYamlInfo] = useState(null)
  const [yamlImporting, setYamlImporting] = useState(false)
  const [invYamlImporting, setInvYamlImporting] = useState(false)
  const [modulesReloadKey, setModulesReloadKey] = useState(0)
  const [invertersReloadKey, setInvertersReloadKey] = useState(0)

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

  const importModulosYaml = async () => {
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
  }

  const importInversoresYaml = async () => {
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Catálogo técnico (SQLite)</CardTitle>
        <CardDescription>
          Edite como planilha: módulos, inversores e padrões de entrada por UF/ligação.
          Módulos (RENE PV / TSUN) e inversores (DEYE / SAJ) vêm dos YAML em <code className="text-xs">dados/</code>.
        </CardDescription>
        <div className="flex gap-2 flex-wrap pt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={importModulosYaml}
            disabled={yamlImporting}
          >
            <FileUp className="h-4 w-4 mr-1" />
            {yamlImporting ? 'Importando...' : 'YAML módulos'}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={importInversoresYaml}
            disabled={invYamlImporting}
          >
            <FileUp className="h-4 w-4 mr-1" />
            {invYamlImporting ? 'Importando...' : 'YAML inversores'}
          </Button>
          {yamlInfo && (
            <span className="text-xs text-muted-foreground self-center">
              {yamlInfo.count} módulos · {invYamlInfo?.count ?? '?'} inversores
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="modules">
          <TabsList>
            <TabsTrigger value="modules">Módulos</TabsTrigger>
            <TabsTrigger value="inverters">Inversores</TabsTrigger>
            <TabsTrigger value="padrao">Padrão entrada</TabsTrigger>
          </TabsList>
          <TabsContent value="modules" className="mt-4">
            <CatalogTable tableKey="modules" reloadKey={modulesReloadKey} />
          </TabsContent>
          <TabsContent value="inverters" className="mt-4">
            <CatalogTable tableKey="inverters" reloadKey={invertersReloadKey} />
          </TabsContent>
          <TabsContent value="padrao" className="mt-4"><CatalogTable tableKey="padrao" /></TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
