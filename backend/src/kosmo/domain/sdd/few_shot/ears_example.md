### REQ-1.1 Presentación de montos con dos decimales

**Ubicuo**

El sistema debe formatear todos los montos monetarios con exactamente dos decimales y el símbolo de la moneda del grupo en cada pantalla donde se muestren valores de gastos o saldos.

**Origen:** Garantiza consistencia en la presentación de valores. Se deriva de C01 y Reglas de negocio.

**Criterios de Aceptación**

**Escenario: Consulta de balance con montos formateados**

- **Dado** que el miembro del hogar se encuentra en la pantalla de balance del grupo con al menos un gasto registrado
- **Cuando** hace clic en la pestaña Balance
- **Entonces** todos los montos de saldo aparecen con dos decimales y el símbolo de la moneda del grupo

**Escenario: Detalle de gasto con cuotas correctas**

- **Dado** que el miembro del hogar está en el historial de gastos del grupo
- **Cuando** hace clic en un gasto registrado para ver su detalle
- **Entonces** la cuota de cada participante aparece con dos decimales y la moneda del grupo

---

### REQ-1.2 Rechazo de registro de gasto sin participantes

**Basado en eventos**

CUANDO el administrador intente guardar un gasto sin haber seleccionado al menos un participante, el sistema debe rechazar el registro y mostrar el mensaje "Debe seleccionar al menos un participante", sin almacenar el gasto.

**Origen:** Evita registros incompletos que distorsionarían los saldos. Se deriva de C01 y Reglas de negocio.

**Criterios de Aceptación**

**Escenario: Intento de guardar gasto sin participantes**

- **Dado** que el administrador del hogar se encuentra en el formulario de nuevo gasto y completa los campos de monto y descripción
- **Cuando** hace clic en el botón Guardar sin haber marcado ningún participante en la lista
- **Entonces** el sistema muestra el mensaje "Debe seleccionar al menos un participante" y el gasto no se almacena

**Escenario: Guardado exitoso con participantes asignados**

- **Dado** que el administrador del hogar se encuentra en el formulario de nuevo gasto con el monto "350.00", la descripción "Supermercado semanal" y 3 participantes seleccionados de la lista
- **Cuando** hace clic en el botón Guardar
- **Entonces** el sistema almacena el gasto, recalcula los saldos de los 3 participantes y muestra la pantalla de balance con los montos actualizados
