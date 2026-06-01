const parseExtensions = (raw: string): string[] =>
  raw
    .split(',')
    .map((s) => s.trim().toLowerCase().replace(/^\./, ''))
    .filter(Boolean)

const envExtensions = import.meta.env.VITE_UPLOAD_ALLOWED_EXTENSIONS as
  | string
  | undefined
const envMaxMb = import.meta.env.VITE_UPLOAD_MAX_SIZE_MB as string | undefined

const defaultExtensions = ['pdf', 'txt', 'md', 'xlsx', 'xls']
const defaultMaxMb = 20

export const uploadConfigFromEnv = {
  maxSizeMb: envMaxMb ? Number(envMaxMb) : defaultMaxMb,
  allowedExtensions: envExtensions
    ? parseExtensions(envExtensions)
    : defaultExtensions,
}

export const getMaxSizeBytes = (maxSizeMb: number) => maxSizeMb * 1024 * 1024

export const buildAcceptAttr = (extensions: string[]) =>
  extensions.map((ext) => `.${ext}`).join(',')

export interface UploadLimits {
  max_size_mb: number
  max_size_bytes: number
  allowed_extensions: string[]
  accept: string
  hint: string
}
