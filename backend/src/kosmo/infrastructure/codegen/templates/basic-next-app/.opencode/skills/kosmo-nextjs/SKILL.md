---
name: kosmo-nextjs
description: Convenciones de Next.js 16 App Router, React 19, Server Components y manejo de APIs tipadas. Trigger: nextjs, next, react, component, page, layout, api route, server component.
---

# Next.js 16 App Router & React 19 en KOSMO

Esta skill define las directrices para el desarrollo de páginas, layouts, componentes interactivos y rutas de API en Next.js 16.

---

## 1. Server Components por Defecto

En Next.js 16 App Router, todos los componentes en `src/app/` son **Server Components** por defecto.

```tsx
// src/app/expenses/page.tsx (Server Component)
import { getExpensesByUser } from "@/db/queries/expenses";
import { ExpenseList } from "@/components/ExpenseList";

export default async function ExpensesPage() {
  // Obtención directa de datos en el servidor
  const expenses = await getExpensesByUser("usr_01");

  return (
    <main className="container mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Registro de Gastos</h1>
      <ExpenseList initialExpenses={expenses} />
    </main>
  );
}
```

---

## 2. Uso Restrictivo de `'use client'`

Solo se agrega la directiva `'use client'` en componentes de hoja pequeños ubicados en `src/components/` que requieran:
- Manejo de estado de cliente (`useState`, `useReducer`).
- Efectos y ciclo de vida del navegador (`useEffect`).
- Eventos de interacción del DOM (`onClick`, `onChange`, `onSubmit`).

```tsx
// src/components/ExpenseFilter.tsx (Client Component)
"use client";

import { useState } from "react";

interface ExpenseFilterProps {
  onFilterChange: (category: string) => void;
}

export function ExpenseFilter({ onFilterChange }: ExpenseFilterProps) {
  const [selected, setSelected] = useState("all");

  const handleChange = (cat: string) => {
    setSelected(cat);
    onFilterChange(cat);
  };

  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={() => handleChange("all")}
        className={selected === "all" ? "bg-primary text-white px-3 py-1 rounded" : "px-3 py-1"}
      >
        Todos
      </button>
    </div>
  );
}
```

---

## 3. Rutas de API Estructuradas (`src/app/api/.../route.ts`)

Las rutas de API deben retornar `NextResponse.json` con códigos HTTP estándar y formato de respuesta estructurado:

```typescript
// src/app/api/expenses/route.ts
import { NextResponse } from "next/server";
import { getExpensesByUser, createExpense } from "@/db/queries/expenses";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get("userId");

  if (!userId) {
    return NextResponse.json(
      { error: "Bad Request", detail: "El parámetro userId es obligatorio." },
      { status: 400 }
    );
  }

  const items = await getExpensesByUser(userId);
  return NextResponse.json({ data: items }, { status: 200 });
}
```

---

## 4. Estilos y Utilidades Tailwind CSS

1. Usa clases utilitarias de Tailwind CSS v4.
2. Para composición condicional de clases, usa `cn()` desde `@/lib/utils`:
   ```tsx
   import { cn } from "@/lib/utils";

   export function Badge({ variant, className, children }: BadgeProps) {
     return (
       <span
         className={cn(
           "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
           variant === "success" && "bg-green-100 text-green-800",
           variant === "error" && "bg-red-100 text-red-800",
           className
         )}
       >
         {children}
       </span>
     );
   }
   ```

---

## 5. Anti-patrones de Next.js Prohibidos

| Anti-patrón | Consecuencia | Corrección |
|-------------|--------------|------------|
| **Poner `'use client'` en `page.tsx` o `layout.tsx`** | Deshabilita Server-Side Rendering y optimizaciones | Mantener la página como Server Component y extraer componentes interactivos |
| **`fetch()` a tus propias rutas API dentro de Server Components** | Overhead innecesario de red HTTP | Llamar directamente a la función de base de datos o servicio |
| **Respuestas de error con strings planos en APIs** | Dificulta parseo en frontend | Retornar JSON `{ error: string, detail?: string }` con status HTTP |
