import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/user', async () => {
    await new Promise(r => setTimeout(r, 800))
    return HttpResponse.json({
      id: 1,
      name: 'Mock User',
    })
  }),
]
