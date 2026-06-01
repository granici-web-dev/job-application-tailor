const API_URL = import.meta.env.VITE_API_URL

if (!API_URL) {
  throw new Error('VITE_API_URL не задан. Укажите адрес бэкенда в переменной окружения VITE_API_URL.')
}

export const STATUS_SENT = 'ОТПРАВЛЕНО'
export const STATUS_NOT_SENT = 'НЕ ОТПРАВЛЕНО'

export interface FileLinks {
  cv: string
  cover_letter: string
}

export interface Application {
  id: number
  company_name: string
  employee_count: string
  job_url: string
  employment_type: string
  job_title: string
  status: string
  created_on: string
  hidden: boolean
  location: string | null
  files: FileLinks | null
}

export interface GenerateResult {
  id: number
  analysis: { company_name: string; job_title: string; [key: string]: unknown }
  company: string
  cv_pdf: string
  cover_letter_pdf: string
  files: FileLinks
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') {
      return data.detail
    }
  } catch {
    // fall through to a generic message
  }
  return `Ошибка запроса (${response.status}).`
}

export async function generateApplication(input: { url: string }): Promise<GenerateResult> {
  const response = await fetch(`${API_URL}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return response.json()
}

export async function fetchApplications(includeHidden: boolean): Promise<Application[]> {
  const response = await fetch(`${API_URL}/applications?include_hidden=${includeHidden}`)
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return response.json()
}

export async function setApplicationStatus(id: number, status: string): Promise<Application> {
  const response = await fetch(`${API_URL}/applications/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return response.json()
}

export async function setApplicationVisibility(id: number, hidden: boolean): Promise<Application> {
  const response = await fetch(`${API_URL}/applications/${id}/visibility`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hidden }),
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return response.json()
}

export async function downloadFile(relativePath: string): Promise<void> {
  const response = await fetch(`${API_URL}${relativePath}`)
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = decodeURIComponent(relativePath.split('/').pop() ?? 'document.pdf')
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}
