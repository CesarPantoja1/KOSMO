'use client';

import { MarkdownEditor, type MarkdownEditorHandle } from '@/feature';
import { Ai } from '@/shared/ui';
import { useAppStore } from '@/shared/store/app.store';
import { useRef, useState, useEffect } from 'react';
import { getDiscovery } from '../api/api';
import LoadingDiscovery from './LoadingDiscovery';

const MockMD = `## Visión del producto
Una aplicación que permite a grupos de amigos o roomies registrar gastos compartidos, calcular balances automáticos y sugerir la forma más eficiente de liquidar deudas, eliminando conflictos y confusiones en la gestión del dinero común.

## Espacio del problema
En grupos de convivencia o viajes, dividir gastos como alquiler, comida o servicios genera tensiones y errores manuales. Las personas pierden tiempo calculando quién debe cuánto a quién, y a menudo terminan con deudas mal liquidadas o discusiones sobre montos. No existe una herramienta simple que automatice el balance y optimice los pagos finales.

## Actores
- **Roomie:** miembro del grupo que comparte gastos fijos y variables.
- **Amigo:** participante en un evento o viaje con gastos compartidos.
- **Administrador:** usuario que configura el grupo y gestiona las reglas de reparto.
- **Pagador:** miembro que realiza un pago en nombre del grupo.

## Propuesta de valor
- **Para Roomie:** evita cálculos manuales y conflictos al dividir gastos recurrentes.
- **Para Amigo:** liquida deudas de forma rápida y justa después de un viaje o evento.
- **Para Administrador:** centraliza la gestión de gastos y balances del grupo.
- **Para Pagador:** recupera el dinero adelantado sin tener que perseguir a los demás.

## Casos de uso
1. **Registrar gasto:** un miembro ingresa un gasto, selecciona los participantes y el método de reparto.
2. **Calcular balance:** el sistema calcula automáticamente cuánto debe cada persona al grupo.
3. **Sugerir liquidación:** el sistema propone la ruta de pagos más eficiente para saldar deudas.
4. **Ver historial:** cualquier miembro consulta el registro de gastos y pagos realizados.
5. **Cerrar grupo:** el administrador finaliza el período y liquida todas las deudas pendientes.

## Capacidades principales
- **Registro de gastos:** captura el monto, concepto, pagador y participantes.
- **Balance automático:** calcula saldos individuales en tiempo real.
- **Optimización de pagos:** sugiere la menor cantidad de transacciones para liquidar deudas.
- **Historial de transacciones:** mantiene un registro completo de gastos y pagos.
- **Notificaciones:** alerta a los miembros sobre deudas pendientes o pagos recibidos.

## Reglas de negocio
1. Un gasto debe tener al menos un pagador y un participante.
2. El reparto puede ser equitativo, por porcentaje o por montos fijos.
3. El balance se recalcula automáticamente tras cada nuevo gasto o pago.
4. La liquidación sugerida minimiza el número de transacciones entre los miembros.
5. Un grupo solo puede cerrarse cuando todos los saldos estén en cero.

## Atributos de calidad
- **Precisión:** el balance debe ser exacto, sin errores de redondeo.
- **Rapidez:** el cálculo del balance debe realizarse en menos de 2 segundos.
- **Usabilidad:** cualquier usuario debe poder registrar un gasto en menos de 3 pasos.
- **Disponibilidad:** el sistema debe estar operativo el 99.5% del tiempo.

## Alcance
**Incluido:**
- Registro de gastos con reparto equitativo, porcentual o fijo.
- Cálculo automático de balances individuales.
- Sugerencia de pagos optimizados para liquidar deudas.
- Historial de gastos y pagos por grupo.
- Notificaciones de deudas pendientes.

**Excluido:**
- Integración con bancos o pasarelas de pago.
- Gestión de ingresos o presupuestos personales.
- Soporte para múltiples monedas o tipos de cambio.
- Funcionalidades de chat o mensajería entre miembros.

**Futuro potencial:**
- Sincronización con calendarios para gastos recurrentes.
- Reportes de gastos por categoría o período.
- Exportación de balances a hojas de cálculo.
- Recordatorios automáticos de pagos vencidos.

`;

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const [markdown, setMarkdown] = useState(MockMD);
	const currentProject = useAppStore((s) => s.currentProject);
	const [isLoading, setIsLoading] = useState(!!currentProject);

	useEffect(() => {
		if (!currentProject) return;

		const fetchDiscovery = async () => {
			setIsLoading(true);
			try {
				const data = await getDiscovery(currentProject.id);
				setMarkdown(data.content);
			} catch {
				await new Promise((resolve) => setTimeout(resolve, 10000));
				setMarkdown(MockMD);
			} finally {
				setIsLoading(false);
			}
		};

		fetchDiscovery();
	}, [currentProject]);

	const handleSave = () => {
		if (editorRef.current?.isDirty) {
			// TODO: persistir markdown via API
			setMarkdown(markdown);
		}
	};

	return (
		<>
			{isLoading && <LoadingDiscovery />}
			<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
				<div className='flex flex-col gap-3'>
					<div className='flex flex-col'>
						<h3 className='text-base-800 text-3xl font-bold'>
							Descripción general del producto
						</h3>
						<p className='text-base-600 mt-2'>
							Visualiza y valida las especificaciones técnicas base de tu proyecto.
						</p>
					</div>
					<div className='flex justify-end gap-3'>
						<button
							className='px-3.5 py-1.5 bg-primary-100 text-base-50 rounded-sm'
							onClick={handleSave}
						>
							Guardar
						</button>

						<button className='flex justify-center items-center px-3.5 py-1.5 gap-3 rounded-sm bg-ai text-base-50 '>
							<Ai size={20} color='text-base-50' />
							<span className='text-center font-semibold'>Generar características</span>
						</button>
					</div>
				</div>

				<MarkdownEditor ref={editorRef} markdown={markdown} onChange={setMarkdown} />
			</div>
		</>
	);
};

export { DiscoveryPage };
