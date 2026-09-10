import { useCallback, useState } from 'react'
import { Upload } from 'lucide-react'
import { pickImportableFile, readFileAsText, importFileKind } from '@/utils/importFileText.js'

/**
 * Envolve o painel de importação — arrastar, soltar ou colar arquivo .txt / .yaml.
 */
export function ImportFileDropZone({ onTxt, onYaml, children, className = '' }) {
  const [dragOver, setDragOver] = useState(false)

  const ingestFile = useCallback(async (file) => {
    if (!file) return false
    const kind = importFileKind(file.name)
    if (!kind) {
      alert('Use um arquivo .txt ou .yaml/.yml')
      return false
    }
    try {
      const text = await readFileAsText(file)
      if (!text.trim()) {
        alert('O arquivo está vazio.')
        return false
      }
      if (kind === 'yaml') {
        onYaml?.(text, file.name)
      } else {
        onTxt?.(text, file.name)
      }
      return true
    } catch {
      alert('Não foi possível ler o arquivo.')
      return false
    }
  }, [onTxt, onYaml])

  const handleFiles = useCallback(async (fileList) => {
    const file = pickImportableFile(fileList)
    if (!file) {
      if (fileList?.length) {
        alert('Use um arquivo .txt ou .yaml/.yml')
      }
      return
    }
    await ingestFile(file)
  }, [ingestFile])

  const onDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }

  const onDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOver(false)
    }
  }

  const onDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    await handleFiles(e.dataTransfer?.files)
  }

  const onPaste = async (e) => {
    const files = e.clipboardData?.files
    if (!files?.length) return
    const file = pickImportableFile(files)
    if (!file) return
    e.preventDefault()
    await ingestFile(file)
  }

  return (
    <div
      className={`relative ${className}`}
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onPasteCapture={onPaste}
    >
      {children}
      {dragOver && (
        <div
          className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-primary bg-primary/10 backdrop-blur-[1px] pointer-events-none"
          aria-hidden
        >
          <Upload className="h-10 w-10 text-primary" />
          <p className="text-sm font-medium text-primary">Solte o arquivo .txt ou .yaml</p>
        </div>
      )}
    </div>
  )
}
