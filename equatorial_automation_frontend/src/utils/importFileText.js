/** Aceita .txt, .yaml e .yml para importação na aba Entrada. */

export function importFileKind(filename = '') {
  const name = String(filename).toLowerCase()
  if (name.endsWith('.yaml') || name.endsWith('.yml')) return 'yaml'
  if (name.endsWith('.txt')) return 'txt'
  return null
}

export function isImportableProjectFile(filename = '') {
  return importFileKind(filename) !== null
}

export async function readFileAsText(file) {
  if (!file) return ''
  return file.text()
}

export function pickImportableFile(fileList) {
  if (!fileList?.length) return null
  return Array.from(fileList).find((f) => isImportableProjectFile(f.name)) || null
}
