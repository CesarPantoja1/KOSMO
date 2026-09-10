@startuml
|#f1f5f9|Administrador|
start
:Completar formulario de nuevo gasto
con monto, descripción y participantes;
|#e2e8f0|Módulo de validación|
:Validar que el monto sea mayor a cero;
if (¿Monto > 0?) is (sí) then
  :Verificar que haya al menos un participante;
  if (¿Hay participantes?) is (sí) then
    |#f8fafc|Registros|
    :Almacenar el gasto con sus participantes;
    |#e2e8f0|Servicio de cálculo|
    :Dividir el monto entre los participantes;
    :Actualizar los saldos de cada participante;
    |#f1f5f9|Administrador|
    :Ver la pantalla de balance con los
    montos actualizados y dos decimales;
  else (no)
    :Mostrar mensaje:
    "Debe seleccionar al menos un participante";
  endif
else (no)
  :Mostrar mensaje:
  "El monto debe ser mayor a cero";
endif
stop
@enduml

