---
name: kosmo-testing
description: Metodología TDD con Vitest, patrón AAA y cobertura obligatoria de happy path y error path. Trigger: test, tests, testing, vitest, TDD, spec.
---

# Testing & TDD con Vitest en KOSMO

Esta skill define el contrato ejecutable de pruebas unitarias y de integración que todo código generado debe cumplir.

---

## 1. Principio Fundacional: Red-Green-Refactor

El orden es innegociable. Nunca generes código de implementación sin su prueba correspondiente:

```
1. RED      — Escribe el test que falla (comportamiento esperado).
2. GREEN    — Escribe la implementación mínima para hacer pasar el test.
3. REFACTOR — Limpia y optimiza manteniendo el test en verde.
```

---

## 2. Estructura AAA Obligatoria (Arrange, Act, Assert)

Todo test unitario sin excepción debe estar delimitado explícitamente con comentarios `// Arrange`, `// Act`, `// Assert`:

```typescript
import { describe, expect, it } from "vitest";
import { calculateDiscount } from "@/lib/discount";

describe("calculateDiscount", () => {
  it("applies 10 percent discount for premium members", () => {
    // Arrange
    const amount = 100;
    const isPremium = true;

    // Act
    const result = calculateDiscount(amount, isPremium);

    // Assert
    expect(result).toBe(90);
  });

  it("throws ValidationError when amount is negative", () => {
    // Arrange
    const negativeAmount = -50;

    // Act & Assert
    expect(() => calculateDiscount(negativeAmount, false)).toThrow("Amount cannot be negative");
  });
});
```

---

## 3. Regla Innegociable de Cobertura de Casos

Para cada función, método o ruta pública, es **obligatorio** escribir como mínimo:
1. **Happy Path (Camino Feliz)**: Caso estándar con entradas válidas donde todo funciona correctamente.
2. **Error Path (Camino de Error)**: Entradas inválidas, valores fuera de rango, datos inexistentes o excepciones esperadas.
3. **Edge Case (Caso Borde)**: Valores cero, arrays vacíos, strings vacíos o límites numéricos.

---

## 4. Pruebas Parametrizadas con `it.each`

Cuando pruebes la misma lógica con diferentes combinaciones de datos, usa `it.each` para evitar duplicación:

```typescript
it.each([
  [100, true, 90],
  [100, false, 100],
  [0, true, 0],
])("calculateDiscount(%i, %s) => %i", (amount, isPremium, expected) => {
  // Arrange & Act
  const result = calculateDiscount(amount, isPremium);

  // Assert
  expect(result).toBe(expected);
});
```

---

## 5. Test Data Builders / Factories

Crea helpers de datos en `tests/factories.ts` para mantener los tests concisos y legibles:

```typescript
export function aUser(overrides: Partial<User> = {}): User {
  return {
    id: "usr_01",
    name: "Juan Pérez",
    email: "juan@example.com",
    role: "member",
    createdAt: new Date("2026-01-01"),
    ...overrides,
  };
}
```

---

## 6. Anti-patrones de Testing Prohibidos

| Anti-patrón | Síntoma | Corrección |
|-------------|---------|------------|
| **Assertion Roulette** | Múltiples asertos sin claridad de qué falló | Un aserto por comportamiento; asertos precisos |
| **Test de Relleno** | `expect(true).toBe(true)` solo para subir métricas | Probar comportamiento real y asertos sobre valores calculados |
| **Mystery Guest** | Dependencia de base de datos externa o red real | Todo en memoria o con SQLite local aislado para tests |
| **Sin Caso de Error** | Solo probar entradas correctas | Escribir tests explícitos para errores y excepciones |
