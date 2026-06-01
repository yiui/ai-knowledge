export const formatToCNTime = (utcString: string) => {
    if (!utcString) return ''
  
    const date = new Date(utcString)
  
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }