import { useCallback, useEffect, useState } from 'react'
import { Plus, RefreshCw, Save, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'

const API_BASE = '/api'

const TABLES = {
  modules: {
    label: 'Módulos',
    fields: [
      'fabricante', 'modelo', 'potencia_wp', 'voc', 'isc', 'vmpp', 'impp', 'eficiencia', 'notas',
    ],
    empty: {
      fabricante: '', modelo: '', potencia_wp: '', voc: '', isc: '', vmpp: '', impp: '', eficiencia: '', notas: '',
    },
  },
  inverters: {
    label: 'Inversores',
    fields: [
      'fabricante', 'modelo', 'potencia_kw', 'tipo_inversor', 'num_mppt',
      'mppt_min', 'mppt_max', 'tensao_nominal', 'corrente_nominal', 'eficiencia', 'notas',
    ],
    empty: {
      fabricante: '', modelo: '', potencia_kw: '', tipo_inversor: 'STRING', num_mppt: '2',
      mppt_min: '', mppt_max: '', tensao_nominal: '220', corrente_nominal: '', eficiencia: '', notas: '',
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

function CatalogTable({ tableKey }) {
  const config = TABLES[tableKey]
  const [rows, setRows] = useState([])
  const [draft, setDraft] = useState({ ...config.empty })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/catalog/${tableKey}`)
      const data = await res.json()
      if (data.success) setRows(data.rows || [])
      else setError(data.error || 'Erro ao carregar')
    } catch {
      setError('Backend offline — reinicie start_backend.bat')
    } finally {
      setLoading(false)
    }
  }, [tableKey])

  useEffect(() => { load() }, [load])

  const saveDraft = async () => {
    try {
      const res = await fetch(`${API_BASE}/catalog/${tableKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    const res = await fetch(`${API_BASE}/catalog/${tableKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    if (!data.success) alert(data.error || 'Erro ao salvar linha')
    else load()
  }

  const removeRow = async (id) => {
    if (!confirm('Excluir este registro do catálogo?')) return
    await fetch(`${API_BASE}/catalog/${tableKey}/${id}`, { method: 'DELETE' })
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

      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-xs">
          <thead className="bg-gray-100">
            <tr>
              {config.fields.map((f) => (
                <th key={f} className="p-2 text-left whitespace-nowrap">{f}</th>
              ))}
              <th className="p-2">Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t hover:bg-blue-50/20">
                {config.fields.map((f) => (
                  <td key={f} className="p-1">
                    <Input
                      className="h-8 text-xs min-w-[80px]"
                      value={row[f] ?? ''}
                      onChange={(e) => updateCell(row.id, f, e.target.value)}
                    />
                  </td>
                ))}
                <td className="p-1 whitespace-nowrap">
                  <Button type="button" size="sm" variant="ghost" onClick={() => saveRow(row)}>
                    <Save className="h-4 w-4" />
                  </Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => removeRow(row.id)}>
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </td>
              </tr>
            ))}
            <tr className="border-t bg-green-50/40">
              {config.fields.map((f) => (
                <td key={f} className="p-1">
                  <Input
                    className="h-8 text-xs"
                    placeholder="novo"
                    value={draft[f] ?? ''}
                    onChange={(e) => setDraft({ ...draft, [f]: e.target.value })}
                  />
                </td>
              ))}
              <td className="p-1">
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
  return (
    <Card>
      <CardHeader>
        <CardTitle>Catálogo técnico (SQLite)</CardTitle>
        <CardDescription>
          Edite como planilha: módulos, inversores e padrões de entrada por UF/ligação.
          Dados da IA podem ser salvos aqui para reutilizar sem custo de API.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="modules">
          <TabsList>
            <TabsTrigger value="modules">Módulos</TabsTrigger>
            <TabsTrigger value="inverters">Inversores</TabsTrigger>
            <TabsTrigger value="padrao">Padrão entrada</TabsTrigger>
          </TabsList>
          <TabsContent value="modules" className="mt-4"><CatalogTable tableKey="modules" /></TabsContent>
          <TabsContent value="inverters" className="mt-4"><CatalogTable tableKey="inverters" /></TabsContent>
          <TabsContent value="padrao" className="mt-4"><CatalogTable tableKey="padrao" /></TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
