# Variables de Entorno - Guía Completa

## Frontend (.env.* en `frontend/`)

### .env.example (Plantilla para desarrollo local)

```plaintext
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=KOSMO
NEXT_PUBLIC_APP_ENV=development
```

### .env.local (Tu máquina - gitignored)

Copia `.env.example` a `.env.local` y personaliza si es necesario.

```bash
cp .env.example .env.local
```

### .env.production (Staging para producción)

```plaintext
NEXT_PUBLIC_API_URL=https://api.kosmo.dev    # Reemplazar con URL real del backend
NEXT_PUBLIC_APP_NAME=KOSMO
NEXT_PUBLIC_APP_ENV=production
```

**Esta archivo define defaults pero será overrideado por Vercel Dashboard.**

## Variables en Vercel Dashboard

Para cada proyecto en Vercel: **Settings** → **Environment Variables**

### Production Environment

| Variable | Value | Type |
|----------|-------|------|
| `NEXT_PUBLIC_API_URL` | `https://api.kosmo.dev` | Public |
| `NEXT_PUBLIC_APP_NAME` | `KOSMO` | Public |
| `NEXT_PUBLIC_APP_ENV` | `production` | Public |

### Preview & Development Environment (Optional)

| Variable | Value | Type |
|----------|-------|------|
| `NEXT_PUBLIC_API_URL` | `https://api-staging.kosmo.dev` | Public |
| `NEXT_PUBLIC_APP_NAME` | `KOSMO (Preview)` | Public |
| `NEXT_PUBLIC_APP_ENV` | `preview` | Public |

## Backend (variables en Docker/Vercel/ENV)

Definidas en `backend/.env` o `docker-compose.yml`:

```plaintext
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/kosmo
MONGO_URL=mongodb://mongo:27017/kosmo
REDIS_URL=redis://redis:6379

# LLM Integration
LLM_PROVIDER=openai          # o tu proveedor
LLM_API_KEY=sk-xxxxxxxxxxxx  # Secret

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# App config
ENV=production
DEBUG=false
CORS_ORIGINS=https://kosmo.vercel.app,https://kosmo.dev
```

## GitHub Actions Secrets

Para CI/CD automático en Vercel: **Settings** → **Secrets and variables** → **Actions**

```plaintext
VERCEL_TOKEN          # Generado en Vercel Dashboard → Settings → Tokens
VERCEL_ORG_ID         # Desde .vercel/project.json → orgId
VERCEL_PROJECT_ID     # Desde .vercel/project.json → projectId
```

## Cómo Obtener VERCEL_TOKEN

1. Ve a https://vercel.com/account/tokens
2. Haz clic "Create Token"
3. Nombre: "GitHub Actions KOSMO"
4. Expiration: 90 days (renovar periódicamente)
5. Copia el token
6. En GitHub Repo → Settings → Secrets → "New repository secret"
   - Name: `VERCEL_TOKEN`
   - Value: `[tu token copiado]`

## Cómo Obtener VERCEL_ORG_ID y VERCEL_PROJECT_ID

Ejecuta localmente:

```bash
cd frontend
cat .vercel/project.json
```

Output:

```json
{
  "projectId": "prj_PcjUtWDbpRHr0hCH2Zr7by2qLl90",
  "orgId": "team_xxxxxxxxxx"
}
```

- `VERCEL_PROJECT_ID` = `prj_PcjUtWDbpRHr0hCH2Zr7by2qLl90`
- `VERCEL_ORG_ID` = `team_xxxxxxxxxx`

## Flujo Completo

```
1. Haces push a 'main'
   ↓
2. GitHub Actions dispara .github/workflows/cd.yml
   ↓
3. cd.yml usa VERCEL_TOKEN para conectarse a Vercel
   ↓
4. Vercel lee variables de entorno desde Dashboard
   ↓
5. Vercel ejecuta 'bun install' + 'bun run build'
   ↓
6. Si todo OK, deploy a producción con URL final
```

## Testing Local con .env.production

Para testear cómo se vería en producción:

```bash
cd frontend
rm -rf .next  # Limpiar build anterior
NEXT_PUBLIC_API_URL=https://api.kosmo.dev \
NEXT_PUBLIC_APP_ENV=production \
bun run build

# Verificar archivo compilado
cat .next/BUILD_ID
```

---

**Checklist:**
- [ ] `.env.production` creado con URLs correctas
- [ ] VERCEL_TOKEN configurado en GitHub Secrets
- [ ] VERCEL_ORG_ID y VERCEL_PROJECT_ID en GitHub Secrets
- [ ] Vercel Dashboard tiene variables de entorno (NEXT_PUBLIC_*)
- [ ] Backend URL definida (local o remota según despliegue)
- [ ] CORS configurado en backend para Vercel domain
- [ ] `bun run build` exitoso localmente
- [ ] Push a `main` triggea deployment automático
