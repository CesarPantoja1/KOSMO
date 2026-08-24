'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { useModelingStore } from '@/entities/modeling';
import { useRequirementsStore } from '@/entities/requirements';
import { PlantUmlViewer } from '@/feature';
import {
	Ai,
	ArrowLeft,
	ArrowRight,
	CursorClickFill,
	Loading,
	ModalConfirm,
	toast,
} from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useProjectStore } from '@/entities/project';
import { useUnsavedChanges } from '@/shared/hooks/useUnsavedChanges';
import { formatApiError } from '@/shared/api';

import { useCharacteristicStore } from '@/entities/characteristic';

import { AsideCharacteristic } from '@/widgets';
import { Modeling } from '@/shared/ui';

const generatingPlantUmlMessages = [
	'Analizando requisitos...',
	'Generando diagrama de actividad UML...',
	'Finalizando generación del diagrama...',
];

const ModelingPage = () => {
	const currentProject = useProjectStore((s) => s.currentProject);
	const currentProjectId = currentProject?.id;
	const router = useRouter();

	const [isGenerating, setIsGenerating] = useState(false);
	const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

	const [uml, setUML] = useState('');
	const [savedContent, setSavedContent] = useState('');
	const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);

	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);

	const [plantumlSource, setPlantumlSource] = useState('');
	const [isPlantumlMaximized, setPlantumlMaximized] = useState(false);

	const characteristics = useCharacteristicStore((s) => s.currentCharacteristics);
	const selectedId = useCharacteristicStore((s) => s.selectedId);
	const setSelectedId = useCharacteristicStore((s) => s.setSelectedId);
	const getCharacteristics = useCharacteristicStore((s) => s.getCharacteristics);

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const hasRequirements = useRequirementsStore((s) => s.hasRequirements);
	const hasDiagram = useModelingStore((s) => s.hasDiagram);
	const currentDiagrams = useModelingStore((s) => s.currentDiagrams);
	const storeGetDiagram = useModelingStore((s) => s.getDiagram);
	const storeGeneratePlantUmlDiagram = useModelingStore((s) => s.generatePlantUmlDiagram);
	const storeDeleteDiagram = useModelingStore((s) => s.deleteDiagram);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);

	const selectedCharacteristic = characteristics.find((c) => c.id === selectedId) ?? null;
	const hasUnsavedChanges = uml !== savedContent;

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
				if (!cancelled) toast.error(formatApiError(error, 'Error al cargar las funcionalidades'));
			});

		return () => {
			cancelled = true;
		};
	}, [currentProjectId, getCharacteristics, setSelectedId]);

	useUnsavedChanges({ isDirty: hasUnsavedChanges });

	useEffect(() => {
		if (!selectedId || !currentProject) return;

		let cancelled = false;

		const load = async () => {
			setIsLoadingRequirements(true);
			setUML('');
			setSavedContent('');
			setPlantumlSource('');
			setPlantumlMaximized(false);

			try {
				const storedContent = currentDiagrams[selectedId];
				if (storedContent) {
					if (!cancelled) {
						setUML(storedContent);
						setSavedContent(storedContent);
						setPlantumlSource(storedContent);
					}
				} else {
					const content = await storeGetDiagram(currentProject.id, selectedId);
					if (cancelled) return;
					setUML(content);
					setSavedContent(content);
					setPlantumlSource(content);
				}
			} catch {
				if (!cancelled) {
					setPlantumlSource('');
				}
			} finally {
				if (!cancelled) {
					setIsLoadingRequirements(false);
				}
			}
		};

		load();

		return () => {
			cancelled = true;
		};
	}, [selectedId, currentProject, currentDiagrams, storeGetDiagram]);

	const handleSelectCharacteristic = (id: string) => {
		if (id === selectedId) return;
		if (hasUnsavedChanges) {
			setPendingCharSwitch(id);
		} else {
			applySelected(id);
		}
	};

	const applySelected = (id: string) => {
		setSelectedId(id);
		setPendingCharSwitch(null);
	};

	const handleConfirmSwitch = () => {
		if (pendingCharSwitch) applySelected(pendingCharSwitch);
	};

	const handleCancelSwitch = () => {
		setPendingCharSwitch(null);
	};

	const handleGenerate = async () => {
		if (!selectedCharacteristic || !currentProject) return;
		setIsGenerating(true);
		try {
			const content = await storeGeneratePlantUmlDiagram(
				currentProject.id,
				selectedCharacteristic.id,
			);
			setPlantumlSource(content);
		} catch (err) {
			toast.error(
				formatApiError(
					err,
					'No se pudo generar el diagrama de actividad. Intenta de nuevo.',
				),
			);
		} finally {
			setIsGenerating(false);
		}
	};

	const handleDeleteDiagram = async () => {
		if (!confirmDeleteId || !currentProject) return;
		const featureId = confirmDeleteId;
		setConfirmDeleteId(null);
		try {
			await storeDeleteDiagram(currentProject.id, featureId);
			setPlantumlSource('');
			setUML('');
			setSavedContent('');
			toast.success('Diagrama eliminado');
		} catch (err) {
			toast.error(formatApiError(err, 'Error al eliminar el diagrama'));
		}
	};

	const handleDeleteClick = (id: string) => {
		setConfirmDeleteId(id);
	};

	const handleNextLink = (href: string) => (e: React.MouseEvent) => {
		const { hasUnsavedChanges: unsaved, setPendingNavigationPath: setPath } =
			useAppStore.getState();
		if (unsaved) {
			e.preventDefault();
			setPath(href);
		}
	};

	const confirmLeave = useCallback(() => {
		const path = pendingNavigationPath;
		setPendingNavigationPath(null);
		useAppStore.getState().setHasUnsavedChanges(false);
		if (!path) return;
		router.push(path);
	}, [pendingNavigationPath, setPendingNavigationPath, router]);

	const cancelLeave = useCallback(() => {
		setPendingNavigationPath(null);
	}, [setPendingNavigationPath]);

	const hasCharacteristics = characteristics.length > 0;
	const hasReqs = Boolean(
		selectedCharacteristic && hasRequirements[selectedCharacteristic.id],
	);
	const hasDiag = Boolean(
		selectedCharacteristic &&
		(plantumlSource.trim() !== '' || hasDiagram[selectedCharacteristic.id]),
	);

	return (
		<>
			{pendingCharSwitch && (
				<ModalConfirm onCancel={handleCancelSwitch} onConfirm={handleConfirmSwitch} />
			)}

			{pendingNavigationPath && (
				<ModalConfirm onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{confirmDeleteId && (
				<ModalConfirm
					title='Eliminar diagrama'
					description='Esta acción no se puede deshacer. Se eliminará el diagrama de actividad de esta funcionalidad.'
					cancelText='Cancelar'
					confirmText='Eliminar'
					onCancel={() => setConfirmDeleteId(null)}
					onConfirm={handleDeleteDiagram}
				/>
			)}

			{isGenerating && (
				<Loading
					title='Generando diagrama de flujo'
					description='Analizando los criterios de aceptación para construir el diagrama de actividad UML.'
					messages={generatingPlantUmlMessages}
				/>
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header'>
					{/* Header row */}
					<div className='flex items-start justify-between gap-4'>
						<div className='flex flex-col gap-1'>
							<h1 className='text-neutral-800 text-lg md:text-xl font-bold'>Diagrama de flujo</h1>
							<p className='text-neutral-500 text-sm md:text-base'>
								Genera el diagrama de actividad UML a partir de los criterios de
								aceptación.
							</p>
						</div>

						{hasCharacteristics &&
							!isEditorMaximized &&
							!isPlantumlMaximized && (
								<div className='flex items-center gap-3 shrink-0'>
									<Link
										href='codigo'
										onClick={handleNextLink('codigo')}
										className='btn btn-primary'
									>
										Continuar
										<ArrowRight color='' size={18} />
									</Link>
								</div>
							)}
					</div>

					{!hasCharacteristics ? (
						<div className='w-full my-auto min-h-105 flex flex-col items-center justify-center'>
							<div className='flex flex-col items-center gap-5 text-center px-6 max-w-lg'>
								<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-neutral-100'>
									<Ai color='text-neutral-400' size={48} />
								</div>
								<div className='flex flex-col gap-2'>
									<h3 className='text-xl font-semibold text-neutral-800'>
										No hay funcionalidades definidas
									</h3>
									<p className='text-neutral-500 text-base'>
										Primero debes generar las funcionalidades del proyecto para poder
										crear sus diagramas de actividad.
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
								onDeleteCharacteristic={handleDeleteClick}
								hasIcon={hasDiagram}
								icon={Modeling}
							/>

							<div className='flex-1 flex flex-col pl-3 pt-2 bg-neutral-50 border-l border-neutral-200 min-h-0 overflow-hidden'>
								{/* No selection */}
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
												Elige una funcionalidad del listado lateral para ver o generar su
												diagrama de actividad UML.
											</p>
										</div>
									</div>
								)}

								{/* Loading diagram */}
								{selectedCharacteristic && isLoadingRequirements && (
									<div className='flex flex-1 w-full items-center justify-center gap-3'>
										<div className='h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500' />
										<span className='text-neutral-500 text-sm'>Cargando diagrama...</span>
									</div>
								)}

								{/* Caso 1: Sin criterios de aceptación */}
								{selectedCharacteristic && !isLoadingRequirements && !hasReqs && (
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
											<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-warning-50'>
												<Ai color='text-warning-500' size={48} />
											</div>
											<div className='flex flex-col items-center gap-2 text-center max-w-md'>
												<h3 className='text-neutral-800 text-lg font-semibold'>
													Faltan criterios de aceptación
												</h3>
												<p className='text-neutral-500 text-sm'>
													Para generar el diagrama primero debes definir los criterios de
													aceptación de esta funcionalidad en la fase anterior.
												</p>
											</div>
											<Link
												href='/proyecto/requisitos'
												onClick={handleNextLink('/proyecto/requisitos')}
												className='btn btn-secondary'
											>
												<ArrowLeft color='' size={18} />
												Ir a criterios
											</Link>
										</div>
									</div>
								)}

								{/* Caso 2: Tiene criterios Y diagrama generado */}
								{selectedCharacteristic &&
									!isLoadingRequirements &&
									hasReqs &&
									hasDiag && (
										<div className='flex flex-col flex-1 min-h-0 gap-3'>
											{!isPlantumlMaximized && (
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
													<div className='flex-1 min-h-0'>
														<PlantUmlViewer
															key={selectedCharacteristic.id}
															source={plantumlSource}
															isMaximized={isEditorMaximized}
															onMaximize={() => setEditorMaximized(true)}
															onMinimize={() => setEditorMaximized(false)}
														/>
													</div>
												</div>
											)}
										</div>
									)}

								{/* Caso 3: Tiene criterios pero sin diagrama */}
								{selectedCharacteristic &&
									!isLoadingRequirements &&
									hasReqs &&
									!hasDiag && (
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
												<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-ai-50'>
													<Ai color='text-ai-500' size={48} />
												</div>
												<div className='flex flex-col items-center gap-2 text-center max-w-md'>
													<h3 className='text-neutral-800 text-lg font-semibold'>
														Aún no hay diagrama generado
													</h3>
													<p className='text-neutral-500 text-sm'>
														Los criterios de aceptación están listos. El asistente
														construirá el diagrama de actividad UML automáticamente.
													</p>
												</div>
												<button onClick={handleGenerate} className='btn btn-ai'>
													<Ai color='' size={18} />
													Generar diagrama
												</button>
											</div>
										</div>
									)}
							</div>
						</div>
					)}
				</div>
			</div>
		</>
	);
};

export { ModelingPage };
