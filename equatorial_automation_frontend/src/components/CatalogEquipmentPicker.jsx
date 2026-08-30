import { useCallback, useEffect, useMemo, useState } from 'react'
import { Database, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.jsx'

import { apiFetch } from '@/utils/api.js'

function mapModuleRow(row) {
  const comp = row.comprimento_m
  const larg = row.largura_m
  let area_modulo = ''
  if (comp != null && larg != null) {
    area_modulo = String(Math.round(Number(comp) * Number(larg) * 1000) / 1000)
  }
  return {
    fabricante: row.fabricante || '',
    model: row.modelo || '',
    power: row.potencia_wp != null ? String(row.potencia_wp) : '',
    voc: row.voc != null ? String(row.voc) : '',
    isc: row.isc != null ? String(row.isc) : '',
    vmpp: row.vmpp != null ? String(row.vmpp) : '',
    impp: row.impp != null ? String(row.impp) : '',
    eficiencia: row.eficiencia != null ? String(row.eficiencia) : '',
    comprimento_m: comp != null ? String(comp) : '',
    largura_m: larg != null ? String(larg) : '',
    area_modulo,
  }
}

function parseStringsPorMppt(raw) {
  if (!raw) return ''
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (Array.isArray(arr) && arr.length) {
      return String(Math.max(...arr.map((n) => Number(n) || 1)))
    }
  } catch {
    /* ignore */
  }
  return ''
}

function formatMpptLayout(raw) {
  if (!raw) return null
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (Array.isArray(arr) && arr.length) {
      return arr.join('+')
    }
  } catch {
    /* ignore */
  }
  return null
}

function mapInverterRow(row) {
  return {
    fabricante: row.fabricante || '',
    model: row.modelo || '',
    power: row.potencia_kw != null ? String(row.potencia_kw) : '',
    tensao_nominal: row.tensao_nominal != null ? String(row.tensao_nominal) : '',
    corrente_nominal: row.corrente_nominal != null ? String(row.corrente_nominal) : '',
    mppt_min: row.mppt_min != null ? String(row.mppt_min) : '',
    mppt_max: row.mppt_max != null ? String(row.mppt_max) : '',
    eficiencia: row.eficiencia != null ? String(row.eficiencia) : '',
    thd_pct: row.thd_pct != null ? String(row.thd_pct) : '',
    num_mppt: row.num_mppt != null ? String(row.num_mppt) : '',
    tipo_inversor: row.tipo_inversor || '',
    fase_ca: row.fase_ca || '',
    strings_por_mppt_json: row.strings_por_mppt_json || '',
    strings_por_mppt_suggested: parseStringsPorMppt(row.strings_por_mppt_json),
  }
}

function optionLabel(row, isModule) {
  const specs = isModule
    ? `${row.potencia_wp ?? '—'} Wp`
    : `${row.potencia_kw ?? '—'} kW`
  return `${row.fabricante || '—'} — ${row.modelo || '—'} (${specs})`
}

export function CatalogEquipmentPicker({ kind, current, onApply, label }) {
  const isModule = kind === 'module'
  const tableName = isModule ? 'modules' : 'inverters'
  const [rows, setRows] = useState([])
  const [filter, setFilter] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadCatalog = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch(`/catalog/${tableName}`)
      const data = await res.json()
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Erro ao carregar catálogo')
      }
      setRows(data.rows || [])
      if (!(data.rows || []).length) {
        setError('Catálogo SQLite vazio — importe módulos/inversores na aba Catálogo.')
      }
    } catch (err) {
      setError(err.message || 'Backend offline — reinicie o servidor.')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [tableName])

  useEffect(() => {
    loadCatalog()
  }, [loadCatalog])

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase()
    if (!q) return rows
    return rows.filter((row) => {
      const hay = `${row.fabricante || ''} ${row.modelo || ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [rows, filter])

  const handleSelect = (id) => {
    setSelectedId(id)
    const row = rows.find((r) => String(r.id) === id)
    if (!row) return
    onApply(isModule ? mapModuleRow(row) : mapInverterRow(row))
  }

  const title = label || (isModule ? 'Catálogo — módulo' : 'Catálogo — inversor')
  const selectedRow = rows.find((r) => String(r.id) === selectedId)
  const mpptLayout = !isModule && selectedRow ? formatMpptLayout(selectedRow.strings_por_mppt_json) : null

  return (
    <div className="rounded-lg border border-dashed border-blue-200 bg-blue-50/60 p-3 space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-blue-900">
        <Database className="h-4 w-4" />
        {title}
        {loading && <Loader2 className="h-4 w-4 animate-spin text-blue-600" />}
      </div>

      <div>
        <Label className="text-xs">Filtrar lista</Label>
        <Input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={isModule ? 'Ex: RENE 620' : 'Ex: DEYE micro'}
        />
      </div>

      <div>
        <Label className="text-xs">Selecionar do catálogo</Label>
        <Select value={selectedId} onValueChange={handleSelect} disabled={loading || !filtered.length}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder={loading ? 'Carregando…' : 'Escolha fabricante / modelo…'} />
          </SelectTrigger>
          <SelectContent className="max-h-72">
            {filtered.map((row) => (
              <SelectItem key={row.id} value={String(row.id)}>
                {optionLabel(row, isModule)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {current?.model && (
        <p className="text-xs text-muted-foreground">
          Atual: {current.fabricante || '—'} — {current.model}
        </p>
      )}

      {!isModule && selectedRow && (
        <div className="rounded border border-blue-300 bg-white/80 p-2 text-xs text-blue-950 space-y-1">
          <p className="font-medium">Topologia MPPT (catálogo)</p>
          <p>MPPT: {selectedRow.num_mppt ?? '—'} · Fase: {selectedRow.fase_ca || '—'} · Tipo: {selectedRow.tipo_inversor || '—'}</p>
          {mpptLayout && <p>Strings/MPPT: {mpptLayout} (máx. paralelo por entrada)</p>}
          {(selectedRow.mppt_min != null || selectedRow.mppt_max != null) && (
            <p>Faixa MPPT: {selectedRow.mppt_min ?? '—'}–{selectedRow.mppt_max ?? '—'} V</p>
          )}
        </div>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}
      {!error && !loading && filtered.length > 0 && (
        <p className="text-xs text-muted-foreground">{filtered.length} registro(s) na lista</p>
      )}
    </div>
  )
}

export function applyCatalogFieldsToItem(prev, fields) {
  return { ...prev, ...fields }
}
