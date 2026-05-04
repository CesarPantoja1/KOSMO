# Guía de Despliegue en Vercel - KOSMO Frontend

## Estado Actual ✓

- ✅ Proyecto linked con Vercel (`vercel link` ejecutado)
- ✅ `vercel.json` correctamente configurado con Bun
- ✅ `next.config.ts` expandido para optimizaciones
- ✅ Variables de entorno organizadas (`.env.example`, `.env.production`)

## Pasos para Despliegue en Vercel

### 1. Configurar Variables de Entorno en Vercel

Ve al **Vercel Dashboard** → Tu proyecto KOSMO → **Settings** → **Environment Variables**

Añade las siguientes variables **para cada environment** (Production, Preview, Development):

```plaintext
# Production Environment
NEXT_PUBLIC_API_URL = https://api.kosmo.dev
NEXT_PUBLIC_APP_NAME = KOSMO
NEXT_PUBLIC_APP_ENV = production

# Preview & Development (opcional, heredarán de Production si no están definidas)
NEXT_PUBLIC_API_URL = https://api-preview.kosmo.dev
```

**Nota:** Las variables `NEXT_PUBLIC_*` son públicas y se envían al navegador. Las variables sin prefijo son privadas (solo servidor).

### 2. Verificar Configuración de Build

En **Vercel Dashboard** → **Settings** → **Build & Development Settings**:

- **Framework:** Next.js ✓ (detectado automáticamente)
- **Build Command:** `bun run build` (ya configurado en vercel.json)
- **Install Command:** `bun install` (ya configurado en vercel.json)
- **Output Directory:** `.next` (default, correcto)

**No sobrescribir** - Vercel usa `vercel.json` automáticamente.

### 3. Desplegar desde Git (GitHub Actions)

El despliegue ocurre automáticamente cuando haces push a:

- **main** → Producción
- **develop** → Preview (optional, configurable)

**Comando manual en tu terminal:**

```bash
cd frontend
vercel --prod  # Desplegar a producción
# o
vercel         # Desplegar a preview/staging
```

### 4. Verificar Deployment

Después de push a `main`:

1. Ve a **Vercel Dashboard** → Tu proyecto → **Deployments**
2. Espera a que el status sea **✓ Ready**
3. Haz clic en la URL de preview o el dominio personalizado
4. Verifica:
   - Página carga sin errores
   - API URL está correcta: `console.log(process.env.NEXT_PUBLIC_API_URL)`
   - MSW funciona en desarrollo (deshabilitado en producción)

### 5. Configurar Dominio Personalizado (Opcional)

En **Settings** → **Domains**:

1. Haz clic "Add Domain"
2. Ingresa tu dominio (ej: `kosmo.dev`)
3. Sigue las instrucciones DNS de Vercel

### 6. Logs y Debugging

**Ver logs del deployment:**

```bash
vercel logs --prod
# o desde dashboard: Deployments → {deployment} → Logs
```

**Logs en tiempo real (local):**

```bash
# Monitorear desde terminal mientras ocurre el build
vercel --prod --logs
```

## Configuración del Backend API

**Problema:** Frontend en Vercel no puede acceder a `localhost:8000`.

**Soluciones:**

### Opción A: Backend también en Vercel (Recomendado para MVP)

1. Crea una carpeta `api/` en Vercel o usa [Vercel Functions](https://vercel.com/docs/functions)
2. Despliega backend en Vercel o Railway
3. Actualiza `NEXT_PUBLIC_API_URL` al endpoint deployado

### Opción B: Backend en Host Separado

1. Despliega backend (ej: Railway, Render, tu servidor)
2. Backend URL: `https://api.kosmo.dev` o similar
3. **CORS:** Asegúrate que backend permite requests desde tu dominio Vercel

Ejemplo (FastAPI):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kosmo.vercel.app", "https://kosmo.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Opción C: Proxy a través de Vercel (Next.js API Routes)

Crea `frontend/src/pages/api/proxy/[...path].ts`:

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { path } = req.query;
  const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
  
  const response = await fetch(`${backendUrl}/${path}`, {
    method: req.method,
    headers: req.headers,
    body: req.body,
  });
  
  res.status(response.status);
  res.send(await response.text());
}
```

Luego actualiza `NEXT_PUBLIC_API_URL = /api/proxy`.

## Dockerfile Frontend en Vercel

**Nota:** Vercel NOT necesita Dockerfile. El `vercel.json` es suficiente.

El `frontend/Dockerfile` es solo para desarrollo local con `docker-compose`.

## Checklist Pre-Deployment

- [ ] `next.config.ts` expandido ✓
- [ ] `vercel.json` con Bun ✓
- [ ] `.env.production` creado ✓
- [ ] Variables de entorno en Vercel Dashboard (PENDIENTE)
- [ ] Backend API URL definida (PENDIENTE - depende de dónde deployar backend)
- [ ] CORS configurado en backend (SI APLICA)
- [ ] `bun run build` exitoso localmente
- [ ] Git push a `main` triggea deployment
- [ ] URL preview de Vercel accesible sin errores

## Monitoreo Post-Deployment

1. **Speed Insights:** Vercel Dashboard → Analytics
2. **Web Vitals:** Next.js reporta Core Web Vitals
3. **Logs:** `vercel logs --prod` para errors

## Rollback

Si algo sale mal:

```bash
vercel rollback --prod
```

O manualmente en dashboard: Deployments → Despliegue anterior → "Promote to Production".

---

**Próximos pasos:**
1. Configura variables de entorno en Vercel Dashboard
2. Decide dónde deployar el backend
3. Actualiza `.env.production` con la URL real del backend
4. Haz push a `main` para triggear deployment en Vercel
