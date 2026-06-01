import { buildAcceptAttr, getMaxSizeBytes } from '@/config/upload'

import type { UploadLimits } from '@/config/upload'

export function validateUploadFile(
  file: File,
  limits: Pick<UploadLimits, 'allowed_extensions' | 'max_size_bytes' | 'max_size_mb'>,
): string | null {
  const name = file.name || ''
  const ext = name.includes('.') ? name.split('.').pop()!.toLowerCase() : ''

  if (!ext || !limits.allowed_extensions.includes(ext)) {
    return `不支持的文件类型，仅允许: ${limits.allowed_extensions.join(', ')}`
  }

  if (file.size <= 0) {
    return '文件不能为空'
  }

  if (file.size > limits.max_size_bytes) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1)
    return `文件大小 ${sizeMb}MB 超过上限 ${limits.max_size_mb}MB`
  }

  return null
}

export { buildAcceptAttr, getMaxSizeBytes }
