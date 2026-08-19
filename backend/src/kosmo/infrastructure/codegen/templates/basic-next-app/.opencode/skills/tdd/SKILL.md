---
name: tdd
description: TDD for Vitest + TypeScript: Red-Green-Refactor, AAA, it.each, builders. Trigger: test, tests, TDD.
---

# TDD Skill — Test-Driven Development (Vitest + TypeScript)

No es una guía académica: es el contrato ejecutable que todo test debe cumplir.

---

## 1. Principio fundacional: Red-Green-Refactor

El orden es innegociable. Nunca escribas implementación antes del test.

```
RED      — escribe el test mínimo que falla (aún no existe la implementación)
GREEN    — escribe la implementación mínima que hace pasar el test
REFACTOR — mejora el código sin cambiar comportamiento (test sigue verde)
```

Con IA generativa: tú (el agente) escribes el test. La implementación se genera para
hacerlo pasar. Esto ancla la generación a expectativas concretas y previene alucinaciones.

---

## 2. Estructura AAA (Arrange, Act, Assert)

Todo test sin excepción sigue AAA, delimitado con comentarios `// Arrange`, `// Act`, `// Assert`.

```typescript
import { describe, expect, it } from "vitest";

describe("expenseCalculator.split", () => {
  it("distributes the amount evenly across participants", () => {
    // Arrange
    const calculator = new ExpenseCalculator();

    // Act
    const result = calculator.split(90, 3);

    // Assert
    expect(result).toEqual([30, 30, 30]);
  });

  it("throws when there are no participants", () => {
    // Arrange
    const calculator = new ExpenseCalculator();

    // Act & Assert
    expect(() => calculator.split(90, 0)).toThrow("participants must be greater than zero");
  });
});
```

---

## 3. Naming de tests

Formato: `describe("<subjecto>.<acción>", () => { it("<escenario>") })`.

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| Happy path | `it("returns <resultado> when <condición>")` | `it("returns the total when items exist")` |
| Error | `it("throws when <condición>")` | `it("throws when the feature is not found")` |
| Edge case | `it("handles <caso borde>")` | `it("handles zero cents without rounding drift")` |

---

## 4. Checklist de calidad (cada test responde SÍ)

1. **¿Prueba lógica o es relleno?** — Fallaría si la lógica se rompe. Si solo sube cobertura, elimínalo.
2. **¿Cubre happy path + error path + un edge case?** — Toda unidad pública tiene mínimo 3 tests.
3. **¿Los asserts son concretos?** — Prohibido `expect(result).toBeTruthy()` como único assert.
4. **¿Usa AAA?** — Las tres secciones están delimitadas y visibles.
5. **¿El nombre describe el escenario?** — Con leerlo sabes qué falló sin abrir el test.
6. **¿Sin mock innecesario?** — Solo se mockean puertos externos (red, DB, clock); la lógica pura se prueba real.

---

## 5. `it.each` (no clones)

Cuando pruebas la misma lógica con distintas entradas, usa `it.each` en vez de copiar el test.

```typescript
it.each([
  [90, 3, [30, 30, 30]],
  [100, 3, [33.34, 33.33, 33.33]], // redondeo
  [0, 2, [0, 0]],
])("split(%i, %i) => %j", (amount, participants, expected) => {
  const calculator = new ExpenseCalculator();
  expect(calculator.split(amount, participants)).toEqual(expected);
});
```

---

## 6. Test Data Builders

Construye los datos con helpers con defaults sensibles; el test solo sobrescribe lo relevante.

```typescript
// tests/factories.ts
export function anExpense(overrides: Partial<Expense> = {}): Expense {
  return { id: "exp_01", amount: 100, currency: "EUR", ...overrides };
}
```

```typescript
const expense = anExpense({ amount: 0 }); // sobrescribe solo lo relevante
```

---

## 7. Test smells prohibidos

| Smell | Síntoma | Corrección |
|-------|---------|------------|
| **Assertion Roulette** | Muchos asserts sin mensaje | Un assert por comportamiento; mensaje en asserts críticos |
| **Mystery Guest** | Depende de estado externo (DB real, red, reloj) | Todo en memoria; usa fake timers si hay fechas |
| **Erratic Test** | A veces pasa, a veces falla | Elimina dependencias de tiempo/red/orden |
| **Conditional Test Logic** | `if`/`for` dentro del test | Test lineal; si necesitas variar, usa `it.each` |
| **Slow Test** | > 200ms en unitarios | Revisa I/O real accidental |
| **Coverage-Driven Test** | Solo existe para tocar una línea | Añade asserts concretos o elimínalo |

---

## 8. Cobertura como side effect

- Cobertura alta es consecuencia de buen testing, no objetivo.
- Nunca escribas un test solo para subir el porcentaje.
- Nunca uses comentarios de exclusión para silenciar código no testeado.

---

## 9. Flujo TDD completo para una feature nueva

1. Lee los requirements de la feature (`get_requirements`) y el AGENTS.md.
2. Escribe el test del happy path (RED — no compila, falta la implementación).
3. Escribe el test del error path (RED).
4. Escribe el test del edge case (RED).
5. Implementa lo mínimo para pasar los 3 tests (GREEN).
6. Refactoriza sin romper verde (REFACTOR).
7. Ejecuta `npx vitest run && npx tsc --noEmit && npx eslint . && npx next build`.
8. Si encontraste un bug que ningún test detecta, escribe el test primero (RED) y luego corrígelo.
