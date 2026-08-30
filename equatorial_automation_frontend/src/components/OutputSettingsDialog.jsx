import { useEffect, useState } from 'react'
import { FolderOpen, Save } from 'lucide-react'
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
import { apiJson } from '@/utils/api.js'

const SOURCE_LABELS = {
  local: 'Configuração do menu (local)',
  env: 'Arquivo .env (CLIENT_OUTPUT_DIR)',
  default: 'Pasta padrão do projeto',
}

export function OutputSettingsDialog({ open, onClose, isMaster, onSaved }) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [config, setConfig] = useState(null)
  const [inputPath, setInputPath] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    setLoading(true)
    setError('')
    setMessage('')
    apiJson('/output-config')
      .then(({ response, data }) => {
        if (cancelled) return
        if (!response.ok || !data.success) {
          setError(data.error || 'Não foi possível carregar a configuração.')
          return
        }
        setConfig(data)
        setInputPath(data.local_path || data.env_path || '')
      })
      .catch(() => {
        if (!cancelled) setError('Erro ao contactar o servidor.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [open])

  const save = async () => {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const { response, data } = await apiJson('/output-config', {
        method: 'POST',
        body: JSON.stringify({ client_output_dir: inputPath.trim() }),
      })
      if (!response.ok || !data.success) {
        setError(data.error || 'Não foi possível salvar.')
        return
      }
      setConfig(data)
      setMessage(data.message || 'Pasta de saída atualizada.')
      onSaved?.(data)
    } catch {
      setError('Erro ao salvar configuração.')
    } finally {
      setSaving(false)
    }
  }

  const useDefault = async () => {
    setInputPath('')
    if (!isMaster) return
    setSaving(true)
    setError('')
    try {
      const { response, data } = await apiJson('/output-config', {
        method: 'POST',
        body: JSON.stringify({ client_output_dir: '' }),
      })
      if (!response.ok || !data.success) {
        setError(data.error || 'Não foi possível restaurar o padrão.')
        return
      }
      setConfig(data)
      setMessage('Usando pasta padrão ou .env.')
      onSaved?.(data)
    } catch {
      setError('Erro ao restaurar padrão.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose?.() }}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-primary" />
            Pasta de saída dos documentos
          </DialogTitle>
          <DialogDescription>
            Onde salvar as pastas dos clientes (mesma regra: número do contrato + 1º e 2º nome).
            Se o Google Drive estiver offline, use uma pasta local temporária.
          </DialogDescription>
        </DialogHeader>

        {loading && <p className="text-sm text-muted-foreground">Carregando…</p>}

        {config && (
          <div className="space-y-4 text-sm">
            <div className="rounded-md border bg-muted/40 p-3 space-y-1">
              <p>
                <span className="font-medium">Em uso agora:</span>
                <br />
                <code className="text-xs break-all">{config.effective_path || config.path}</code>
              </p>
              <p className="text-xs text-muted-foreground">
                Origem: {SOURCE_LABELS[config.source] || config.source}
              </p>
              {config.using_fallback && config.warning && (
                <p className="text-xs text-amber-700">{config.warning}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Padrão se nada configurado: <code>{config.default_path}</code>
              </p>
            </div>

            {isMaster ? (
              <div className="space-y-2">
                <Label htmlFor="output-dir">Pasta base (override local)</Label>
                <Input
                  id="output-dir"
                  value={inputPath}
                  onChange={(e) => setInputPath(e.target.value)}
                  placeholder="Ex.: I:\Meu Drive\Pieng\...\80 a 100"
                />
                <p className="text-xs text-muted-foreground">
                  Deixe vazio para usar CLIENT_OUTPUT_DIR do .env ou a pasta padrão
                  {' '}
                  <code>saida/web_generated</code>.
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Somente o administrador pode alterar a pasta base. Peça ao master se precisar mudar o destino.
              </p>
            )}

            {message && <p className="text-sm text-primary">{message}</p>}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {isMaster && (
            <>
              <Button type="button" variant="outline" onClick={useDefault} disabled={saving || loading}>
                Usar padrão / .env
              </Button>
              <Button type="button" onClick={save} disabled={saving || loading}>
                <Save className="h-4 w-4 mr-2" />
                Salvar pasta
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
