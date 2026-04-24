export const apiClient = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const res = await fetch(url, options)
  if (!res.ok) throw new Error('API Error')
  return res.json()
}
