import { ExternalLink, Eye, FolderOpen } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { apiJson } from '@/utils/api.js'

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileRow({ label, file, folderName, onError }) {
  if (!file) return null

  const openInApp = async () => {
    try {
      const { response, data } = await apiJson('/output/open-file', {
        method: 'POST',
        body: JSON.stringify({ folder_name: folderName, file_name: file.name }),
      })
      if (!response.ok || !data.success) {
        onError?.(data.error || 'Não foi possível abrir o arquivo.')
      }
    } catch {
      onError?.('Erro ao contactar o servidor.')
    }
  }

  const viewWeb = () => {
    if (file.view_url) {
      window.open(file.view_url, '_blank', 'noopener,noreferrer')
      return
    }
    window.open(file.download_url, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 bg-white rounded border border-green-300">
      <div className="min-w-0">
        <span className="text-sm text-foreground block truncate">{label}{file.name}</span>
        {file.size != null && (
          <span className="text-xs text-muted-foreground">{formatSize(file.size)}</span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5 shrink-0">
        {file.can_view_web && (
          <Button type="button" variant="outline" size="sm" onClick={viewWeb}>
            <Eye className="h-3.5 w-3.5 mr-1" />
            Ver na web
          </Button>
        )}
        <Button type="button" variant="default" size="sm" onClick={openInApp}>
          <ExternalLink className="h-3.5 w-3.5 mr-1" />
          Abrir
        </Button>
      </div>
    </div>
  )
}

export function GeneratedFilesPanel({
  generatedFiles,
  outputDirectory,
  outputFolderName,
  outputWarning,
  onOpenFolderError,
}) {
  if (!generatedFiles) return null

  const openFolder = async () => {
    try {
      const { response, data } = await apiJson('/output/open-folder', {
        method: 'POST',
        body: JSON.stringify({ folder_name: outputFolderName || '' }),
      })
      if (!response.ok || !data.success) {
        onOpenFolderError?.(data.error || 'Não foi possível abrir a pasta.')
      }
    } catch {
      onOpenFolderError?.('Erro ao contactar o servidor.')
    }
  }

  return (
    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
      <p className="font-semibold text-green-800 mb-3">✅ Documentos Gerados com Sucesso!</p>

      {outputDirectory && (
        <div className="mb-3 p-3 bg-white rounded border border-green-200 text-xs text-foreground break-all space-y-2">
          <div>
            <span className="font-medium">Pasta no Google Drive / disco:</span>
            <br />
            {outputDirectory}
          </div>
          <p className="text-muted-foreground">
            Os arquivos já estão salvos nesta pasta. Use Abrir para o Word, Excel ou AutoCAD.
          </p>
          <p className="text-muted-foreground">Dados pessoais (LGPD) — não compartilhe nem suba ao GitHub.</p>
          <Button type="button" variant="outline" size="sm" onClick={openFolder}>
            <FolderOpen className="h-4 w-4 mr-2" />
            Abrir pasta no Explorer
          </Button>
        </div>
      )}

      {outputWarning && (
        <p className="mb-3 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2">
          {outputWarning}
        </p>
      )}

      <div className="space-y-2">
        <FileRow label="📊 Excel: " file={generatedFiles.excel} folderName={outputFolderName} onError={onOpenFolderError} />
        <FileRow label="📄 Memorial: " file={generatedFiles.memorial} folderName={outputFolderName} onError={onOpenFolderError} />
        <FileRow label="📝 Procuração: " file={generatedFiles.procuracao} folderName={outputFolderName} onError={onOpenFolderError} />
        <FileRow label="📋 Contrato: " file={generatedFiles.contrato} folderName={outputFolderName} onError={onOpenFolderError} />
        <FileRow label="📐 Planta CAD: " file={generatedFiles.planta} folderName={outputFolderName} onError={onOpenFolderError} />
        {generatedFiles.outros?.map((file) => (
          <FileRow
            key={file.name}
            label="📎 "
            file={file}
            folderName={outputFolderName}
            onError={onOpenFolderError}
          />
        ))}
      </div>
    </div>
  )
}
