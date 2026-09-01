import { useEffect, useRef, useState } from 'react'
import { FileText } from 'lucide-react'
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

export function ContractNumberDialog({
  open,
  onClose,
  initialValue = '',
  clientName = '',
  loading = false,
  onConfirm,
}) {
  const [value, setValue] = useState(initialValue)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    setValue(initialValue || '')
    setError('')
    const t = setTimeout(() => inputRef.current?.focus(), 50)
    return () => clearTimeout(t)
  }, [open, initialValue])

  const submit = () => {
    const trimmed = value.trim()
    if (!trimmed) {
      setError('Informe o número do contrato para continuar.')
      inputRef.current?.focus()
      return
    }
    onConfirm(trimmed)
  }

  const folderHint = clientName
    ? `Pasta de saída: ${value.trim() || '…'} - ${clientName.split(/\s+/).slice(0, 2).join(' ')}`
    : 'A pasta de saída usa o número do contrato + 1º e 2º nome do cliente.'

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next && !loading) onClose() }}>
      <DialogContent className="sm:max-w-md" onPointerDownOutside={(e) => loading && e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Número do contrato
          </DialogTitle>
          <DialogDescription>
            Obrigatório para gerar os documentos e nomear a pasta do cliente (ex.: 80, 122/2026).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-1">
          <Label htmlFor="dialog_numero_contrato">Número do contrato *</Label>
          <Input
            ref={inputRef}
            id="dialog_numero_contrato"
            value={value}
            onChange={(e) => {
              setValue(e.target.value)
              if (error) setError('')
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                submit()
              }
            }}
            placeholder="Ex.: 122/2026 ou 80"
            disabled={loading}
            aria-invalid={Boolean(error)}
          />
          {error ? (
            <p className="text-sm text-destructive" role="alert">{error}</p>
          ) : (
            <p className="text-xs text-muted-foreground">{folderHint}</p>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button type="button" onClick={submit} disabled={loading}>
            {loading ? 'Gerando...' : 'Gerar documentos'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
