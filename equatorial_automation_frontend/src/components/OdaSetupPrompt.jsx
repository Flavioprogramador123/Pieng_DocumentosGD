import { useState } from 'react'
import { Download, ExternalLink, RefreshCw, HardDrive } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.jsx'
import { apiJson } from '@/utils/api.js'

const SKIP_SESSION_KEY = 'pieng_oda_skip_session'

export function shouldShowOdaPrompt(odaStatus) {
  if (!odaStatus || odaStatus.installed) return false
  if (sessionStorage.getItem(SKIP_SESSION_KEY) === '1') return false
  return true
}

export function OdaSetupPrompt({ open, odaStatus, onClose, onStatusChange }) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const recheck = async () => {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const { response, data } = await apiJson('/system/requirements')
      if (!response.ok || !data.success) {
        setError('Não foi possível verificar o ODA.')
        return
      }
      onStatusChange?.(data.oda)
      if (data.oda?.installed) {
        setMessage('ODA File Converter detectado. A planta será entregue como planta.dwg (~2 MB).')
        setTimeout(() => onClose?.(), 1500)
      } else {
        setError('ODA ainda não detectado. Conclua a instalação e clique em Verificar novamente.')
      }
    } catch {
      setError('Erro ao contactar o servidor.')
    } finally {
      setLoading(false)
    }
  }

  const launchInstaller = async () => {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const { response, data } = await apiJson('/system/oda/launch-installer', { method: 'POST' })
      if (!response.ok || !data.success) {
        setError(data.error || 'Não foi possível iniciar o instalador.')
        return
      }
      setMessage(
        data.message
        || 'Instalador iniciado. Confirme o UAC (administrador), aguarde e clique em Verificar novamente.'
      )
    } catch {
      setError('Erro ao iniciar o instalador.')
    } finally {
      setLoading(false)
    }
  }

  const continueWithout = () => {
    sessionStorage.setItem(SKIP_SESSION_KEY, '1')
    onClose?.()
  }

  if (!odaStatus || odaStatus.installed) return null

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose?.() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5 text-primary" />
            Configuração recomendada — Planta CAD
          </DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-3 text-sm text-muted-foreground pt-1">
              <p>
                Na <strong>primeira execução</strong> neste computador, o PIENG verifica o
                {' '}
                <strong>ODA File Converter</strong>
                {' '}
                para gerar
                {' '}
                <code className="text-xs bg-muted px-1 rounded">planta.dwg</code>
                {' '}
                (~2 MB) em vez de
                {' '}
                <code className="text-xs bg-muted px-1 rounded">planta.dxf</code>
                {' '}
                (~25 MB).
              </p>
              <p>
                Você continuará abrindo o DWG no AutoCAD para colar o mapa e ajustar a prancha.
              </p>
              {odaStatus.install_script_available && (
                <p className="text-xs">
                  Script local:
                  {' '}
                  <code className="bg-muted px-1 rounded">{odaStatus.install_script}</code>
                </p>
              )}
            </div>
          </DialogDescription>
        </DialogHeader>

        {message && (
          <p className="text-sm text-primary bg-primary/5 border border-primary/20 rounded-md px-3 py-2">
            {message}
          </p>
        )}
        {error && (
          <p className="text-sm text-destructive bg-destructive/5 border border-destructive/20 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <DialogFooter className="flex-col sm:flex-col gap-2 sm:space-x-0">
          <Button type="button" onClick={launchInstaller} disabled={loading} className="w-full">
            <Download className="h-4 w-4 mr-2" />
            Instalar ODA File Converter (recomendado)
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={recheck}
            disabled={loading}
            className="w-full"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Verificar novamente
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => window.open(odaStatus.download_page, '_blank', 'noopener')}
            className="w-full"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Baixar manualmente no site da ODA
          </Button>
          <Button
            type="button"
            variant="link"
            onClick={continueWithout}
            className="w-full text-muted-foreground"
          >
            Continuar sem instalar (entregará planta.dxf maior)
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
