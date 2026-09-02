@startuml
|#f1f5f9|Colaborador|
start
:Completar formulario de nuevo ticket
con título, descripción y categoría;
if (¿Desea adjuntar archivos?) is (sí) then
  :Seleccionar uno o varios archivos
desde su equipo;
  :Ver nombres de archivos en
la lista de adjuntos;
else (no)
endif
:Presionar botón Registrar;
|#e2e8f0|Sistema|
:Validar que título, descripción
y categoría estén completos;
if (¿Campos obligatorios completos?) is (sí) then
  |#f8fafc|Registros|
  :Almacenar ticket con estado
"Pendiente de revisión" y generar
código único;
  |#e2e8f0|Sistema|
  :Crear historial inicial con acción
"Creación de ticket", fecha/hora
y nombre del colaborador;
  :Mostrar pantalla de confirmación
con código, fecha y estado;
  |#f1f5f9|Colaborador|
  if (¿Ver detalle del ticket?) is (sí) then
    :Navegar a pantalla de detalle
mostrando toda la información;
  else (no)
  endif
  |#e2e8f0|Sistema|
  :Mostrar ticket en lista de pendientes
del equipo de soporte (ordenado por
fecha, prioridad sin asignar);
else (no)
  :Mostrar mensajes de error por
campo faltante y mantener los
datos ya ingresados;
endif
stop
@enduml
