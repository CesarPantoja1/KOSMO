'use client';

import { useEffect } from 'react';
import Link from 'next/link';

import { useCharacteristicStore } from '@/entities/characteristic';
import { useImplementationStore } from '@/entities/implementation';
import { useModelingStore } from '@/entities/modeling';
import { useProjectStore } from '@/entities/project';
import { AsideCharacteristic } from '@/widgets';
import { Implementation, toast } from '@/shared/ui';
import {
	Ai,
	ArrowLeft,
	CursorClickFill,
	SuccessCheckIcon,
	WarningIcon,
} from '@/shared/ui';
import { formatApiError } from '@/shared/api';
import { ImplementationLiveProgress } from './ImplementationLiveProgress';

const ImplementationPage = () => {
	const characteristics = useCharacteristicStore((s) => s.currentCharacteristics);
	const selectedId = useCharacteristicStore((s) => s.selectedId);
	const setSelectedId = useCharacteristicStore((s) => s.setSelectedId);
	const getCharacteristics = useCharacteristicStore((s) => s.getCharacteristics);
	const currentProject = useProjectStore((s) => s.currentProject);
	const currentProjectId = currentProject?.id;

	const status = useImplementationStore((s) => s.status);
	const progress = useImplementationStore((s) => s.progress);
	const errorMessage = useImplementationStore((s) => s.errorMessage);
	const implementations = useImplementationStore((s) => s.implementations);
	const startGeneration = useImplementationStore((s) => s.startGeneration);
	const loadImplementation = useImplementationStore((s) => s.loadImplementation);

	const hasDiagram = useModelingStore((s) => s.hasDiagram);

	const selectedCharacteristic = characteristics.find((c) => c.id === selectedId) ?? null;
	const hasCharacteristics = characteristics.length > 0;
	const hasAnyImplementation = Object.values(implementations).some(Boolean);
	const currentHasImpl = selectedId ? !!implementations[selectedId] : false;
	const selectedHasDiagram = selectedId ? !!hasDiagram[selectedId] : false;
	const isGenerating = status === 'generating';

	useEffect(() => {
		if (!currentProjectId) return;
		let cancelled = false;

		void getCharacteristics(currentProjectId)
			.then((features) => {
				if (cancelled) return;
				const currentSelection = useCharacteristicStore.getState().selectedId;
				if (!features.some((feature) => feature.id === currentSelection)) {
					setSelectedId(features[0]?.id ?? null);
				}
			})
			.catch((error: unknown) => {
				if (!cancelled)
					toast.error(formatApiError(error, 'Error al cargar las funcionalidades'));
			});

		return () => {
			cancelled = true;
		};
	}, [currentProjectId, getCharacteristics, setSelectedId]);

	// La verdad de la implementación vive en el backend: al abrir el proyecto o
	// cambiar de característica se hidrata el estado desde el servidor.
	useEffect(() => {
		if (!selectedCharacteristic) return;
		loadImplementation(
			selectedCharacteristic.id,
			selectedCharacteristic.title,
			selectedCharacteristic.display_id,
		);
	}, [selectedCharacteristic, loadImplementation]);

	const handleSelectCharacteristic = (id: string) => {
		setSelectedId(id);
	};

	const handleGenerate = async () => {
		if (!selectedId || !selectedCharacteristic) return;
		await startGeneration(
			selectedId,
			selectedCharacteristic.title,
			selectedCharacteristic.display_id,
		);
	};

	return (
		<>
			{isGenerating && <ImplementationLiveProgress progress={progress} />}

			{status === 'failed' && errorMessage && (
				<div className='mb-4 flex items-center gap-3 rounded-lg border border-warning-200 bg-warning-50 px-4 py-3'>
					<WarningIcon size={20} color='text-warning-600' />
					<p className='text-sm text-warning-700'>{errorMessage}</p>
				</div>
			)}

			<section className='page-container px-0'>
				<div className='page-header'>
					<div className='flex items-start justify-between gap-4'>
						<div className='flex flex-col gap-1'>
							<h1 className='text-neutral-800 text-lg md:text-xl font-bold'>
								Implementación
							</h1>
							<p className='text-neutral-500 text-sm md:text-base'>
								Tu aplicación está lista. KOSMO ha transformado todo lo que definiste en
								los pasos anteriores en una estructura funcional para continuar con su
								desarrollo.
							</p>
						</div>

						{hasCharacteristics && hasAnyImplementation && (
							<div className='flex items-center gap-3 shrink-0'>
								<Link href='/proyecto/codigo/resumen' className='btn btn-primary'>
									Ver resumen
								</Link>
							</div>
						)}
					</div>

				{!hasCharacteristics ? (
						<div className='w-full my-auto min-h-105 flex flex-col items-center justify-center'>
							<div className='flex flex-col items-center gap-5 text-center px-6 max-w-lg'>
								<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-neutral-100'>
									<Implementation color='text-neutral-400' size={48} />
								</div>
								<div className='flex flex-col gap-2'>
									<h3 className='text-xl font-semibold text-neutral-800'>
										No hay funcionalidades definidas
									</h3>
									<p className='text-neutral-500 text-base'>
										Primero debes generar las funcionalidades del proyecto para poder
										generar su implementación.
									</p>
								</div>
								<Link href='/proyecto/caracteristicas' className='btn btn-secondary'>
									<ArrowLeft color='' size={18} />
									Ir a Funcionalidades
								</Link>
							</div>
						</div>
					) : (
						<div className='flex gap-1 flex-1 min-h-0'>
							<AsideCharacteristic
								characteristics={characteristics}
								selectedId={selectedId}
								onSelectCharacteristic={handleSelectCharacteristic}
								hasIcon={implementations}
								icon={Implementation}
							/>

							<div className='relative flex-1 flex flex-col pl-3 pt-2 bg-neutral-50 border-l border-neutral-200 min-h-0 overflow-hidden'>
								{!selectedCharacteristic && (
									<div className='flex flex-col items-center justify-center h-full gap-4'>
										<div className='flex h-16 w-16 items-center justify-center rounded-2xl bg-neutral-100'>
											<CursorClickFill color='text-neutral-400' size={40} />
										</div>
										<div className='flex flex-col items-center gap-2 text-center max-w-sm'>
											<h3 className='text-neutral-700 text-lg font-semibold'>
												Selecciona una funcionalidad
											</h3>
											<p className='text-neutral-400 text-sm'>
												Elige una funcionalidad del listado lateral para generar su
												implementación.
											</p>
										</div>
									</div>
								)}

								{selectedCharacteristic && !currentHasImpl && (
									<div className='flex flex-col flex-1 min-h-0 gap-3'>
										<div className='flex flex-col gap-1 px-2'>
											<div className='flex items-center gap-2'>
												<span className='text-base font-bold text-neutral-500'>
													{selectedCharacteristic.display_id}
												</span>
												<span className='text-base font-semibold text-neutral-800'>
													{selectedCharacteristic.title}
												</span>
											</div>
											<p className='text-neutral-500 text-sm'>
												{selectedCharacteristic.description}
											</p>
										</div>

										{!selectedHasDiagram ? (
											<div className='flex flex-col my-auto items-center gap-5 px-12'>
												<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-warning-50'>
													<Ai color='text-warning-500' size={48} />
												</div>
												<div className='flex flex-col items-center gap-2 text-center max-w-md'>
													<h3 className='text-neutral-800 text-lg font-semibold'>
														Falta diagrama de actividad
													</h3>
													<p className='text-neutral-500 text-sm'>
														Esta funcionalidad no tiene diagrama de actividad
														generado. Genera el diagrama antes de continuar con la
														implementación.
													</p>
												</div>
												<Link href='/proyecto/modelo' className='btn btn-secondary'>
													<ArrowLeft color='' size={18} />
													Ir a diagramas
												</Link>
											</div>
										) : (
											<div className='flex flex-col my-auto items-center gap-5 px-12'>
												<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-ai-50'>
													<Ai color='text-ai-500' size={48} />
												</div>
												<div className='flex flex-col items-center gap-2 text-center max-w-md'>
													<h3 className='text-neutral-800 text-lg font-semibold'>
														Aún no hay implementación generada
													</h3>
													<p className='text-neutral-500 text-sm'>
														Esta funcionalidad aún no tiene código generado. El
														asistente creará la estructura de implementación
														automáticamente.
													</p>
												</div>
												<button onClick={handleGenerate} className='btn btn-ai'>
													<Ai color='' size={18} />
													Generar implementación
												</button>
											</div>
										)}
									</div>
								)}

								{selectedCharacteristic && currentHasImpl && (
									<div className='flex flex-col flex-1 min-h-0 gap-3'>
										<div className='flex flex-col gap-1 px-2'>
											<div className='flex items-center gap-2'>
												<span className='text-base font-bold text-neutral-500'>
													{selectedCharacteristic.display_id}
												</span>
												<span className='text-base font-semibold text-neutral-800'>
													{selectedCharacteristic.title}
												</span>
											</div>
											<p className='text-neutral-500 text-sm'>
												{selectedCharacteristic.description}
											</p>
										</div>

										<div className='flex flex-col my-auto items-center gap-5 px-12'>
											<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-success-50'>
												<SuccessCheckIcon size={40} color='text-success-600' />
											</div>
											<div className='flex flex-col items-center gap-2 text-center max-w-md'>
												<h3 className='text-neutral-800 text-lg font-semibold'>
													Implementación generada
												</h3>
												<p className='text-neutral-500 text-sm'>
													La estructura de esta funcionalidad ha sido generada
													exitosamente. Puedes ver el resumen completo en el botón
													&quot;Ver resumen&quot;.
												</p>
											</div>
										</div>
									</div>
								)}
							</div>
						</div>
					)}
				</div>
			</section>
		</>
	);
};

export { ImplementationPage };
