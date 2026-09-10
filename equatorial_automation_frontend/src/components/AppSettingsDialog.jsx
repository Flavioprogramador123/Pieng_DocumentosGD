import { useEffect, useState } from 'react'
import { Settings, Save, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.jsx'
import { apiJson } from '@/utils/api.js'

/** Aceita "5,5" / "5.5" / vazio sem forçar o default no meio da digitação. */
function parseNumInput(raw, fallback) {
  const text = String(raw ?? '').trim().replace(',', '.')
  if (text === '' || text === '.' || text === '-') return raw
  const n = Number(text)
  return Number.isFinite(n) ? n : fallback
}

function toFiniteNumber(value, fallback) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const n = Number(String(value ?? '').replace(',', '.'))
  return Number.isFinite(n) ? n : fallback
}

function normalizeGeracaoForSave(geracao = {}) {
  const hspMap = { ...(geracao.hsp_por_uf || {}) }
  const hspGo = toFiniteNumber(hspMap.GO ?? hspMap.DEFAULT, 5.3)
  hspMap.GO = hspGo
  hspMap.DEFAULT = toFiniteNumber(hspMap.DEFAULT, hspGo)
  return {
    ...geracao,
    hsp_por_uf: hspMap,
    eficiencia_sistema: toFiniteNumber(geracao.eficiencia_sistema, 0.8),
    dias_por_mes: toFiniteNumber(geracao.dias_por_mes, 30.4),
    tarifa_kwh: toFiniteNumber(geracao.tarifa_kwh, 1.1),
  }
}

export function AppSettingsDialog({ open, onClose, isMaster, onSaved }) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    setLoading(true)
    setError('')
    apiJson('/app-settings')
      .then(({ response, data }) => {
        if (cancelled) return
        if (!response.ok || !data.success) {
          setError(data.error || 'Não foi possível carregar configurações.')
          return
        }
        setSettings(data.settings)
      })
      .catch(() => {
        if (!cancelled) setError('Erro ao contactar o servidor.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [open])

  const patchGeracao = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      geracao: { ...(prev?.geracao || {}), [field]: value },
    }))
  }

  const patchHspGo = (value) => {
    setSettings((prev) => ({
      ...prev,
      geracao: {
        ...(prev?.geracao || {}),
        hsp_por_uf: { ...(prev?.geracao?.hsp_por_uf || {}), GO: value, DEFAULT: value },
      },
    }))
  }

  const patchFigura = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      figura_localizacao: { ...(prev?.figura_localizacao || {}), [field]: value },
    }))
  }

  const save = async () => {
    if (!settings) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const payload = {
        ...settings,
        geracao: normalizeGeracaoForSave(settings.geracao || {}),
      }
      const { response, data } = await apiJson('/app-settings', {
        method: 'POST',
        body: JSON.stringify({ settings: payload }),
      })
      if (!response.ok || !data.success) {
        setError(data.error || 'Não foi possível salvar.')
        return
      }
      setSettings(data.settings)
      setMessage(data.message || 'Configurações salvas. Recalcule o sistema para atualizar a aba Cálculos.')
      onSaved?.(data.settings)
    } catch {
      setError('Erro ao salvar.')
    } finally {
      setSaving(false)
    }
  }

  const resetDefaults = async () => {
    if (!isMaster) return
    setSaving(true)
    setError('')
    try {
      const { response, data } = await apiJson('/app-settings', {
        method: 'POST',
        body: JSON.stringify({ reset: true }),
      })
      if (!response.ok || !data.success) {
        setError(data.error || 'Não foi possível restaurar.')
        return
      }
      setSettings(data.settings)
      setMessage('Padrões do repositório restaurados.')
      onSaved?.(data.settings)
    } catch {
      setError('Erro ao restaurar.')
    } finally {
      setSaving(false)
    }
  }

  const g = settings?.geracao || {}
  const f = settings?.figura_localizacao || {}
  const hspGo = g.hsp_por_uf?.GO ?? g.hsp_por_uf?.DEFAULT ?? 5.3

  const exemploKwp = 5.5
  const eta = toFiniteNumber(g.eficiencia_sistema, 0.8)
  const dias = toFiniteNumber(g.dias_por_mes, 30.4)
  const hsp = toFiniteNumber(hspGo, 5.3)
  const exemploMes = exemploKwp * hsp * eta * dias

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose?.() }}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-primary" />
            Configurações do sistema
          </DialogTitle>
          <DialogDescription>
            Padrões de geração, mapa e HSP — salvos em
            {' '}
            <code className="text-xs">app_settings.local.json</code>
            {' '}
          </DialogDescription>
        </DialogHeader>

        {loading && <p className="text-sm text-muted-foreground">Carregando…</p>}

        {settings && (
          <div className="space-y-6 text-sm">
            <section className="space-y-3 rounded-md border p-3">
              <h4 className="font-semibold">Geração estimada</h4>
              <p className="text-xs text-muted-foreground">
                {g.formula_descricao || 'E_mês (kWh) = P_kWp × HSP × η × dias/mês'}
              </p>
              <p className="text-xs bg-muted/50 p-2 rounded font-mono">
                Exemplo {exemploKwp} kWp → {exemploMes.toFixed(0)} kWh/mês
                {' '}
                ({exemploKwp} × {hsp} × {eta} × {dias})
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>HSP Goiás (h/dia)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="4"
                    max="7"
                    disabled={!isMaster}
                    value={hspGo ?? ''}
                    onChange={(e) => patchHspGo(parseNumInput(e.target.value, 5.3))}
                  />
                </div>
                <div>
                  <Label>Eficiência η (0–1)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0.5"
                    max="1"
                    disabled={!isMaster}
                    value={g.eficiencia_sistema ?? ''}
                    onChange={(e) => patchGeracao('eficiencia_sistema', parseNumInput(e.target.value, 0.8))}
                  />
                </div>
                <div>
                  <Label>Dias/mês</Label>
                  <Input
                    type="number"
                    step="0.1"
                    disabled={!isMaster}
                    value={g.dias_por_mes ?? ''}
                    onChange={(e) => patchGeracao('dias_por_mes', parseNumInput(e.target.value, 30.4))}
                  />
                </div>
                <div>
                  <Label>Tarifa (R$/kWh)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    disabled={!isMaster}
                    value={g.tarifa_kwh ?? ''}
                    onChange={(e) => patchGeracao('tarifa_kwh', parseNumInput(e.target.value, 1.1))}
                  />
                </div>
              </div>
            </section>

            <section className="space-y-3 rounded-md border p-3">
              <h4 className="font-semibold">Figura de localização (mapa)</h4>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Zoom padrão</Label>
                  <Select
                    disabled={!isMaster}
                    value={String(f.zoom_padrao ?? 18)}
                    onValueChange={(v) => patchFigura('zoom_padrao', parseInt(v, 10))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {['16', '17', '18', '19'].map((z) => (
                        <SelectItem key={z} value={z}>{z}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Modo zoom</Label>
                  <Select
                    disabled={!isMaster}
                    value={f.zoom_modo || 'fixo'}
                    onValueChange={(v) => patchFigura('zoom_modo', v)}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fixo">Fixo (sempre o zoom acima)</SelectItem>
                      <SelectItem value="auto">Automático (16 rural / 18 urbano)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2">
                  <Label>Provedor de tiles</Label>
                  <Select
                    disabled={!isMaster}
                    value={f.tile_provider || 'osmde'}
                    onValueChange={(v) => patchFigura('tile_provider', v)}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="osmde">OpenStreetMap.de (padrão)</SelectItem>
                      <SelectItem value="osm">OpenStreetMap.org</SelectItem>
                      <SelectItem value="esri">Esri World Street</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </section>

            {!isMaster && (
              <p className="text-xs text-muted-foreground">
                Somente o administrador pode alterar. Você pode visualizar os valores atuais.
              </p>
            )}

            {message && <p className="text-sm text-primary">{message}</p>}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {isMaster && (
            <>
              <Button type="button" variant="outline" onClick={resetDefaults} disabled={saving || loading}>
                <RotateCcw className="h-4 w-4 mr-2" />
                Restaurar padrões
              </Button>
              <Button type="button" onClick={save} disabled={saving || loading}>
                <Save className="h-4 w-4 mr-2" />
                Salvar
              </Button>
            </>
          )}
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
