import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Maximize2,
  Minimize2,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Search,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'

const STORAGE_KEY = 'deParaPanelWidth'
const DEFAULT_WIDTH = 460
const MIN_WIDTH = 300
const NARROW_WIDTH = 360
const WIDE_WIDTH = 620
const MAX_WIDTH_RATIO = 0.92

function clampWidth(value) {
  const max = Math.min(window.innerWidth * MAX_WIDTH_RATIO, 960)
  return Math.min(max, Math.max(MIN_WIDTH, value))
}

function readStoredWidth() {
  try {
    const saved = Number(localStorage.getItem(STORAGE_KEY))
    if (saved > 0) return clampWidth(saved)
  } catch {
    /* ignore */
  }
  return DEFAULT_WIDTH
}

function StatusBadge({ filled, pendingInTemplate }) {
  if (filled) {
    return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">OK</Badge>
  }
  if (pendingInTemplate) {
    return <Badge className="bg-amber-100 text-amber-900 hover:bg-amber-100">Pendente</Badge>
  }
  return <Badge variant="destructive">Vazio</Badge>
}

function MappingTable({ rows, pendingTokens, filter, showLabel = true }) {
  const q = filter.trim().toLowerCase()
  const filtered = (rows || []).filter((row) => {
    if (!q) return true
    return (
      row.label?.toLowerCase().includes(q) ||
      row.token?.toLowerCase().includes(q) ||
      row.placeholder?.toLowerCase().includes(q) ||
      String(row.value || '').toLowerCase().includes(q)
    )
  })

  if (filtered.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-6 text-center">
        Nenhum placeholder mapeado ainda. Preencha o formulário ou importe o TXT.
      </p>
    )
  }

  return (
    <div className="overflow-y-auto h-full min-h-0">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0 bg-gray-50 z-10 shadow-sm">
          <tr className="border-b text-left text-gray-600">
            {showLabel && <th className="p-2 font-medium">Campo</th>}
            <th className="p-2 font-medium">Placeholder</th>
            <th className="p-2 font-medium">Valor</th>
            <th className="p-2 font-medium w-16">Status</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((row, idx) => {
            const pending = pendingTokens?.has?.(row.token)
            return (
              <tr key={`${row.token}-${idx}`} className="border-b border-gray-100 align-top hover:bg-blue-50/40">
                {showLabel && (
                  <td className="p-2 text-gray-800 max-w-[100px] break-words">{row.label || '—'}</td>
                )}
                <td className="p-2 font-mono text-blue-700 whitespace-nowrap">{row.placeholder}</td>
                <td className="p-2 text-gray-700 break-all">
                  {row.value ? (
                    <span title={row.value}>{row.value}</span>
                  ) : (
                    <span className="text-gray-400 italic">vazio</span>
                  )}
                </td>
                <td className="p-2">
                  <StatusBadge filled={row.filled} pendingInTemplate={pending && !row.filled} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function DeParaPanel({
  open,
  onToggle,
  preview,
  loading,
  onRefresh,
  filter,
  onFilterChange,
  error,
  onWidthChange,
}) {
  const [width, setWidth] = useState(readStoredWidth)
  const [expanded, setExpanded] = useState(false)
  const [resizing, setResizing] = useState(false)
  const widthBeforeExpand = useRef(DEFAULT_WIDTH)
  const dragStartX = useRef(0)
  const dragStartWidth = useRef(DEFAULT_WIDTH)

  const applyWidth = useCallback((next) => {
    const clamped = clampWidth(next)
    setWidth(clamped)
    setExpanded(false)
    onWidthChange?.(clamped)
    try {
      localStorage.setItem(STORAGE_KEY, String(clamped))
    } catch {
      /* ignore */
    }
  }, [onWidthChange])

  useEffect(() => {
    onWidthChange?.(width)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onResize = () => {
      setWidth((prev) => clampWidth(prev))
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    if (!resizing) return undefined

    const onMove = (e) => {
      const delta = dragStartX.current - e.clientX
      applyWidth(dragStartWidth.current + delta)
    }
    const onUp = () => setResizing(false)

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [resizing, applyWidth])

  const startResize = (e) => {
    e.preventDefault()
    dragStartX.current = e.clientX
    dragStartWidth.current = width
    setResizing(true)
  }

  const toggleExpanded = () => {
    if (expanded) {
      applyWidth(widthBeforeExpand.current)
      setExpanded(false)
    } else {
      widthBeforeExpand.current = width
      const max = clampWidth(window.innerWidth * MAX_WIDTH_RATIO)
      setExpanded(true)
      setWidth(max)
      onWidthChange?.(max)
      try {
        localStorage.setItem(STORAGE_KEY, String(max))
      } catch {
        /* ignore */
      }
    }
  }

  const stats = preview?.stats
  const pendingSet = new Set()
  if (preview?.unresolved_by_template) {
    Object.values(preview.unresolved_by_template).forEach((tokens) => {
      tokens.forEach((t) => pendingSet.add(t))
    })
  }

  const formRows = preview?.mappings || []
  const templateRows = (preview?.template_placeholders || formRows).map((row) => ({
    ...row,
    label: row.label || row.token,
  }))

  const derivedRows = (preview?.derived_tokens || []).map((row) => ({
    label: row.source === 'default' ? 'Padrão (config)' : 'Calculado',
    token: row.token,
    placeholder: row.placeholder,
    value: row.value,
    filled: row.filled,
  }))

  if (!open) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-40 bg-blue-600 text-white px-2 py-4 rounded-l-lg shadow-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
        style={{ writingMode: 'vertical-rl' }}
        title="Abrir painel DE/PARA"
      >
        DE/PARA
      </button>
    )
  }

  return (
    <aside
      className="fixed right-0 top-0 z-40 h-screen bg-white border-l border-gray-200 shadow-2xl flex flex-col"
      style={{ width: `${width}px`, maxWidth: '100vw' }}
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Redimensionar painel DE/PARA"
        title="Arraste para ampliar ou reduzir · duplo clique restaura"
        onMouseDown={startResize}
        onDoubleClick={() => applyWidth(DEFAULT_WIDTH)}
        className={`absolute left-0 top-0 bottom-0 w-2 -ml-1 z-50 cursor-col-resize group ${
          resizing ? 'bg-blue-500/30' : 'hover:bg-blue-400/25'
        }`}
      >
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-12 rounded-full bg-gray-300 group-hover:bg-blue-500 transition-colors" />
      </div>

      <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50 shrink-0">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h2 className="font-bold text-gray-900">Conferência DE/PARA</h2>
            <p className="text-xs text-gray-600 mt-1">
              Placeholders {'{{TOKEN}}'} e valores que serão encaixados nos templates.
            </p>
            <p className="text-[10px] text-gray-500 mt-1">
              Largura: {Math.round(width)}px — arraste a borda esquerda ou use os botões abaixo.
            </p>
            {preview?.source === 'local' && (
              <p className="text-xs text-amber-700 mt-1">Preview local (reinicie o backend para dados completos).</p>
            )}
          </div>
          <div className="flex shrink-0 gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleExpanded}
              title={expanded ? 'Reduzir painel' : 'Ampliar painel'}
            >
              {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={onToggle} title="Fechar painel">
              <PanelRightClose className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex gap-1 mb-3">
          <Button type="button" variant="outline" size="sm" className="text-xs h-7 px-2" onClick={() => applyWidth(NARROW_WIDTH)}>
            Estreito
          </Button>
          <Button type="button" variant="outline" size="sm" className="text-xs h-7 px-2" onClick={() => applyWidth(DEFAULT_WIDTH)}>
            Padrão
          </Button>
          <Button type="button" variant="outline" size="sm" className="text-xs h-7 px-2" onClick={() => applyWidth(WIDE_WIDTH)}>
            Largo
          </Button>
        </div>

        {error && (
          <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2 mb-2">{error}</p>
        )}

        {stats && (
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <div className="bg-white rounded p-2 border">
              <span className="text-gray-500">Formulário</span>
              <p className="font-semibold text-green-700">
                {stats.form_filled}/{stats.form_fields} preenchidos
              </p>
            </div>
            <div className="bg-white rounded p-2 border">
              <span className="text-gray-500">Templates</span>
              <p className="font-semibold text-amber-700">
                {stats.template_pending ?? 0} pendente(s)
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-3.5 w-3.5 text-gray-400" />
            <Input
              className="pl-8 h-9 text-sm"
              placeholder="Filtrar placeholder ou valor..."
              value={filter}
              onChange={(e) => onFilterChange(e.target.value)}
            />
          </div>
          <Button variant="outline" size="icon" onClick={onRefresh} disabled={loading} title="Atualizar">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Tabs defaultValue="templates" className="flex-1 flex flex-col overflow-hidden min-h-0 px-0">
        <TabsList className="mx-4 mt-2 grid grid-cols-3 shrink-0">
          <TabsTrigger value="templates" className="text-xs">Placeholders</TabsTrigger>
          <TabsTrigger value="form" className="text-xs">Formulário</TabsTrigger>
          <TabsTrigger value="pending" className="text-xs">Pendentes</TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="flex-1 flex flex-col min-h-0 px-4 pb-4 mt-2 overflow-hidden data-[state=inactive]:hidden">
          <MappingTable
            rows={templateRows}
            pendingTokens={pendingSet}
            filter={filter}
            showLabel={false}
          />
        </TabsContent>

        <TabsContent value="form" className="flex-1 flex flex-col min-h-0 px-4 pb-4 mt-2 overflow-hidden data-[state=inactive]:hidden">
          <MappingTable rows={formRows} pendingTokens={pendingSet} filter={filter} />
        </TabsContent>

        <TabsContent value="pending" className="flex-1 min-h-0 px-4 pb-4 mt-2 overflow-y-auto data-[state=inactive]:hidden">
          {!preview?.unresolved_by_template || Object.keys(preview.unresolved_by_template).length === 0 ? (
            <div>
              <p className="text-sm text-green-700 py-4 text-center">
                {preview?.source === 'local'
                  ? 'Lista de pendentes nos templates disponível após conectar ao backend.'
                  : 'Todos os placeholders dos templates têm valor.'}
              </p>
              {derivedRows.length > 0 && (
                <>
                  <p className="text-xs font-semibold text-gray-700 mb-2">Valores derivados / padrão</p>
                  <MappingTable rows={derivedRows} pendingTokens={pendingSet} filter={filter} />
                </>
              )}
            </div>
          ) : (
            Object.entries(preview.unresolved_by_template).map(([file, tokens]) => (
              <div key={file} className="mb-4">
                <p className="text-xs font-semibold text-gray-800 mb-2 truncate" title={file}>
                  {file}
                </p>
                <div className="flex flex-wrap gap-1">
                  {tokens.map((token) => (
                    <code
                      key={token}
                      className="text-[10px] bg-red-50 text-red-800 px-1.5 py-0.5 rounded border border-red-100"
                    >
                      {`{{${token}}}`}
                    </code>
                  ))}
                </div>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </aside>
  )
}

export function DeParaPanelToggle({ onToggle }) {
  return (
    <Button variant="outline" onClick={onToggle}>
      <PanelRightOpen className="mr-2 h-4 w-4" />
      DE/PARA
    </Button>
  )
}
