import { useCallback, useEffect, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { Label } from '@/components/ui/label.jsx'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select.jsx'
import { apiFetch } from '@/utils/api.js'

const ZOOM_OPTIONS = ['16', '17', '18']

export function FiguraLocalizacaoPreview({ technicalData, onTechnicalChange }) {
  const [previewUrl, setPreviewUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [placeLabel, setPlaceLabel] = useState('')
  const [suggestedZoom, setSuggestedZoom] = useState('')
  const zoomTouchedRef = useRef(false)

  const hasCoords = Boolean(
    (technicalData.latitude && technicalData.longitude)
    || (technicalData.coordenada_utm_x && technicalData.coordenada_utm_y)
    || (technicalData.coordenadas_raw && String(technicalData.coordenadas_raw).trim())
  )

  const currentZoom = technicalData.figura_map_zoom || suggestedZoom || '18'

  const loadPreview = useCallback(async (zoomOverride) => {
    if (!hasCoords) return

    setLoading(true)
    setError('')
    try {
      const zoomArg = zoomOverride ?? (zoomTouchedRef.current ? technicalData.figura_map_zoom : null)
      const response = await apiFetch('/figura-localizacao/preview', {
        method: 'POST',
        body: JSON.stringify({
          technical: technicalData,
          ...technicalData,
          figura_map_zoom: zoomArg || null,
        }),
      })
      const data = await response.json()
      if (!response.ok || !data.success) {
        setError(data.error || 'Não foi possível gerar o mapa.')
        setPreviewUrl('')
        return
      }

      setPreviewUrl(`data:image/png;base64,${data.image_base64}`)
      setPlaceLabel(data.place_label || '')
      setSuggestedZoom(String(data.suggested_zoom))

      if (!zoomTouchedRef.current && data.suggested_zoom) {
        onTechnicalChange({ figura_map_zoom: String(data.suggested_zoom) })
      }
    } catch (err) {
      setError(err.message || 'Erro ao carregar mapa.')
      setPreviewUrl('')
    } finally {
      setLoading(false)
    }
  }, [hasCoords, technicalData, onTechnicalChange])

  useEffect(() => {
    if (!hasCoords) {
      setPreviewUrl('')
      setError('')
      setPlaceLabel('')
      setSuggestedZoom('')
      return undefined
    }

    const timer = setTimeout(() => {
      loadPreview(zoomTouchedRef.current ? technicalData.figura_map_zoom : null)
    }, 700)

    return () => clearTimeout(timer)
  }, [
    hasCoords,
    loadPreview,
    technicalData.latitude,
    technicalData.longitude,
    technicalData.coordenada_utm_x,
    technicalData.coordenada_utm_y,
    technicalData.coordenadas_raw,
    technicalData.fuso_utm,
  ])

  const handleZoomChange = (value) => {
    zoomTouchedRef.current = true
    onTechnicalChange({ figura_map_zoom: value })
    loadPreview(value)
  }

  if (!hasCoords) {
    return (
      <p className="text-xs text-muted-foreground col-span-2">
        Informe as coordenadas acima para visualizar o mapa de localização.
      </p>
    )
  }

  return (
    <div className="col-span-2 space-y-3 rounded-lg border bg-white/70 p-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="min-w-[140px]">
          <Label>Zoom do mapa</Label>
          <Select value={currentZoom} onValueChange={handleZoomChange}>
            <SelectTrigger>
              <SelectValue placeholder="Zoom" />
            </SelectTrigger>
            <SelectContent>
              {ZOOM_OPTIONS.map((z) => (
                <SelectItem key={z} value={z}>
                  {z}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={() => loadPreview(currentZoom)}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar mapa
        </Button>

        {suggestedZoom && (
          <p className="text-xs text-muted-foreground pb-2">
            Sugestão automática: zoom {suggestedZoom}
            {Number(currentZoom) === Number(suggestedZoom) ? ' — em uso' : ''}
          </p>
        )}
      </div>

      {placeLabel && (
        <p className="text-sm text-gray-700">{placeLabel}</p>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      {loading && !previewUrl && (
        <p className="text-sm text-muted-foreground">Gerando mapa…</p>
      )}

      {previewUrl && (
        <img
          src={previewUrl}
          alt="Pré-visualização do mapa de localização"
          className="w-full max-w-3xl rounded border shadow-sm"
        />
      )}

      <p className="text-xs text-muted-foreground">
        Confira o mapa antes de gerar os documentos. Se estiver adequado, siga o fluxo normal —
        o zoom selecionado será usado no memorial. Ajuste o zoom e clique em Atualizar mapa se precisar.
      </p>
    </div>
  )
}
