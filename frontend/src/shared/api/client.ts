import { API_BASE_URL } from './config'

export const apiClient = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const res = await fetch(`${API_BASE_URL}${url}`, options)
  if (!res.ok) throw new Error('API Error')
  return res.json()
}
