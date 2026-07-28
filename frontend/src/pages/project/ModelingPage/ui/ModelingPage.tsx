'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { Chatbot, PlantUmlViewer } from '@/feature';
import {
	Ai,
	ArrowRight,
	CursorClickFill,
	Loading,
	ModalConfirmLeave,
	toast,
} from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';

import type { Characteristic } from '@/entities/characteristic';
import {
	getCharacteristicRequirements,
	getCharacteristics,
} from '@/entities/characteristic';

import { Modeling } from '@/widgets/main-navbar/ui/icons';

import { generatePlantUmlDiagram, getDiagram } from '@/entities/modeling';

const ModelingPage = () => {
	const currentProject = useAppStore((s) => s.currentProject);
	const router = useRouter();

	const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isGenerating, setIsGenerating] = useState(false);
	const [isChatbotOpen, setIsChatbotOpen] = useState(false);
	const [isRefining, setIsRefining] = useState(false);

	const [markdown, setMarkdown] = useState('');
	const [savedContent, setSavedContent] = useState('');
	const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);

	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);

	const [plantumlSource, setPlantumlSource] = useState('');
	const [isPlantumlMaximized, setPlantumlMaximized] = useState(false);

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const hasRequirements = useAppStore((s) => s.hasRequirements);
	const setHasRequirements = useAppStore((s) => s.setHasRequirements);
	const hasDiagram = useAppStore((s) => s.hasDiagram);
	const setHasDiagram = useAppStore((s) => s.setHasDiagram);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);

	const selectedCharacteristic = characteristics.find((c) => c.id === selectedId) ?? null;
	const hasUnsavedChanges = markdown !== savedContent;

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const fetch = async () => {
			setIsLoading(true);
			try {
				const data = await getCharacteristics(currentProject.id);
				setCharacteristics(data);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : 'Error al cargar las características';
				toast.error(message);
			} finally {
				setIsLoading(false);
			}
		};

		fetch();
	}, [currentProject, router]);

	useEffect(() => {
		if (!selectedId || !currentProject) return;

		let cancelled = false;
		const projectId = currentProject.id;
		const characteristicId = selectedId;

		const load = async () => {
			setIsLoadingRequirements(true);
			setMarkdown('');
			setSavedContent('');
			setPlantumlSource('');
			setPlantumlMaximized(false);

			try {
				const content = await getCharacteristicRequirements(
					projectId,
					characteristicId,
				).catch(() => '');
				if (cancelled) return;
				if (content) {
					setHasRequirements(characteristicId, true);
				}
				setCharacteristics((prev) =>
					prev.map((c) =>
						c.id === characteristicId ? { ...c, requirements: content } : c,
					),
				);
				setMarkdown(content);
				setSavedContent(content);

				// Intentar cargar el diagrama existente
				try {
					const source = await getDiagram(projectId, characteristicId);
					if (!cancelled && source) {
						setPlantumlSource(source);
						setHasDiagram(characteristicId, true);
					}
				} catch {
					if (!cancelled) {
						setPlantumlSource('');
						setHasDiagram(characteristicId, false);
					}
				}
			} catch {
				if (!cancelled)
					toast.error('Error al cargar la información de la característica');
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
	}, [selectedId, currentProject, setHasRequirements, setHasDiagram]);

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
			const source = await generatePlantUmlDiagram(
				currentProject.id,
				selectedCharacteristic.id,
			);
			setPlantumlSource(source);
			setHasDiagram(selectedCharacteristic.id, true);
			toast.success('Diagrama de actividad generado con éxito');
		} catch (_err) {
			console.log(_err);
			toast.error('No se pudo generar el diagrama de actividad. Intenta de nuevo.');
		} finally {
			setIsGenerating(false);
		}
	};

	const handleRefine = async (_instructions: string) => {
		if (!selectedCharacteristic || !currentProject) return;
		setIsChatbotOpen(false);
		setIsRefining(true);
		try {
			const source = await generatePlantUmlDiagram(
				currentProject.id,
				selectedCharacteristic.id,
			);
			setPlantumlSource(source);
			setHasDiagram(selectedCharacteristic.id, true);
			toast.success('Diagrama refinado correctamente');
		} catch (err) {
			const errorMessage =
				err instanceof Error
					? err.message
					: 'No se pudo refinar el diagrama. Intenta nuevamente.';
			toast.error(errorMessage);
		} finally {
			setIsRefining(false);
		}
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
		setHasUnsavedChanges(false);
		if (!path) return;
		router.push(path);
	}, [pendingNavigationPath, setPendingNavigationPath, setHasUnsavedChanges, router]);

	const cancelLeave = useCallback(() => {
		setPendingNavigationPath(null);
	}, [setPendingNavigationPath]);

	if (isLoading) {
		return (
			<div className='page-container'>
				<div className='page-header'>
					<h2 className='text-3xl font-bold text-base-800'>Diagramas</h2>
					<p className='text-base-600 text-lg'>
						Usar el asistente AI para generar diagramas UML de acuerdo a los requisitos
						EARS generados.
					</p>
					<div className='inline-flex justify-end items-start gap-3 text-base-50'>
						<button disabled className='btn text-base-50 disabled:opacity-50 bg-ai'>
							<Ai color='' size={20} />
							Refinar
						</button>

						<Link
							href='codigo'
							aria-disabled
							onClick={(e) => e.preventDefault()}
							className='btn text-base-50 disabled:opacity-50 bg-primary-100 hover:bg-primary-100/90'
						>
							Ir a código
							<ArrowRight color='' size={20} />
						</Link>
					</div>
				</div>

				<div className='flex gap-4 flex-1 min-h-0 pb-4'>
					<div className='w-88 pt-2 bg-base-100/50 rounded-sm flex flex-col gap-3 p-3 animate-pulse'>
						<div className='h-7 bg-base-200 rounded w-48' />
						{[1, 2, 3, 4].map((i) => (
							<div key={i} className='h-14 bg-base-200 rounded' />
						))}
					</div>
					<div className='flex-1 bg-base-100/50 rounded-sm animate-pulse' />
				</div>
			</div>
		);
	}

	const hasReqs = Boolean(
		selectedCharacteristic &&
		(selectedCharacteristic.requirements || hasRequirements[selectedCharacteristic.id]),
	);
	const hasDiag = Boolean(
		selectedCharacteristic &&
		(plantumlSource.trim() !== '' || hasDiagram[selectedCharacteristic.id]),
	);

	return (
		<>
			{isRefining && (
				<Loading
					title='Refinando modelo'
					description='Mejorando la calidad y consistencia del modelo. Esto tomará unos segundos.'
				/>
			)}

			{isChatbotOpen && (
				<Chatbot
					placeholder='ej., "Haz que el diagrama de actividad sea más conciso y claro"'
					onClose={() => setIsChatbotOpen(false)}
					onSubmitInstructions={handleRefine}
				/>
			)}
			{pendingCharSwitch && (
				<ModalConfirmLeave
					onCancel={handleCancelSwitch}
					onConfirm={handleConfirmSwitch}
				/>
			)}

			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{isGenerating && (
				<Loading
					title='Generando diagrama de actividad'
					description='Analizando los requisitos EARS para construir el diagrama PlantUML. Esto tomará unos segundos.'
				/>
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header'>
					<h2 className='text-3xl font-bold text-base-800'>Diagramas</h2>
					<p className='text-base-600 text-lg'>
						Usar el asistente AI para generar diagramas UML de acuerdo a los requisitos
						EARS generados.
					</p>

					{!isEditorMaximized && !isPlantumlMaximized && (
						<div className='inline-flex justify-end items-start gap-3 text-base-50'>
							<button
								onClick={() => setIsChatbotOpen(true)}
								disabled={!hasDiag}
								className='btn text-base-50 bg-ai hover:bg-ai/90 disabled:opacity-50 rounded-sm'
							>
								<Ai color='' size={20} />
								Refinar
							</button>

							<Link
								href='codigo'
								onClick={handleNextLink('codigo')}
								className='btn text-base-50 bg-primary-100 hover:bg-primary-100/90 rounded-sm'
							>
								Ir a código
								<ArrowRight color='' size={20} />
							</Link>
						</div>
					)}
				</div>

				<div className='flex gap-4 flex-1 min-h-0'>
					<aside className='w-88 pt-3 bg-base-100/50 rounded-sm flex flex-col'>
						<h3 className='text-primary-100 text-lg font-bold px-4 pb-3'>
							Lista de Características
						</h3>

						<div className='flex-1 px-2 flex flex-col gap-1 overflow-y-auto pb-4'>
							{characteristics.length === 0 && (
								<p className='text-base-600 text-sm px-3 py-2'>
									No hay características disponibles.
								</p>
							)}
							{characteristics.map((c) => {
								const isSelected = c.id === selectedId;
								const cHasReq = Boolean(c.requirements || hasRequirements[c.id]);
								const cHasDiag = Boolean(
									hasDiagram[c.id] ||
									(c.id === selectedId && plantumlSource.trim() !== ''),
								);

								return (
									<button
										key={c.id}
										onClick={() => handleSelectCharacteristic(c.id)}
										className={`w-full p-3 flex justify-start items-center gap-3 text-left cursor-pointer transition-colors ${
											isSelected
												? 'bg-primary-100/10 border-l-4 border-primary-100'
												: 'border-l-4 border-transparent hover:bg-base-200/30'
										}`}
									>
										<span
											className={`text-base font-bold shrink-0 ${
												isSelected ? 'text-base-800' : 'text-base-800'
											}`}
										>
											{c.display_id}
										</span>
										<p
											className={`flex-1 text-sm font-medium leading-snug ${
												isSelected ? 'text-primary-100' : 'text-base-600'
											}`}
										>
											{c.title}
										</p>
										{cHasDiag && (
											<div className='shrink-0' title='Modelo generado'>
												<Modeling
													size={20}
													color={isSelected ? 'text-primary-100' : 'text-base-600'}
												/>
											</div>
										)}
										{!cHasDiag && cHasReq && (
											<span
												className='shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded bg-primary-100/10 text-primary-100'
												title='Requisitos EARS listos para modelar'
											>
												Reqs OK
											</span>
										)}
									</button>
								);
							})}
						</div>
					</aside>

					<div className='flex-1 flex flex-col pl-2 pt-2 bg-base-100/50 min-h-0 overflow-hidden'>
						{!selectedCharacteristic && (
							<div className='flex flex-col items-center justify-center h-full gap-3'>
								<CursorClickFill color='text-base-800' size={70} />
								<div className='self-stretch px-24 flex flex-col justify-start items-start'>
									<div className='self-stretch p-2.5 inline-flex justify-center items-center gap-2.5'>
										<div className='text-center justify-start text-base-800 text-2xl font-semibold'>
											Selecciona una Característica
										</div>
									</div>
									<div className='self-stretch p-2.5 inline-flex justify-center items-center gap-2.5'>
										<div className='flex-1 text-center justify-start text-base-600 text-lg font-medium'>
											Selecciona una característica del listado lateral para ver
											<br />o comenzar a generar su diagrama UML.
										</div>
									</div>
								</div>
							</div>
						)}

						{selectedCharacteristic && isLoadingRequirements && (
							<div className='flex flex-1 items-center justify-center'>
								<span className='text-base-600 text-lg'>Cargando modelo...</span>
							</div>
						)}

						{/* Caso 1: La característica NO tiene requisitos EARS generados todavía */}
						{selectedCharacteristic && !isLoadingRequirements && !hasReqs && (
							<section className='flex flex-col h-full justify-center items-center gap-5 px-20'>
								<Ai color='text-ai' size={70} />
								<span className='text-center justify-start text-base-800 text-2xl font-medium'>
									Sin requisitos EARS generados
								</span>
								<p className='text-base-800 text-lg text-center'>
									Esta característica aún no tiene requisitos EARS generados. Primero
									debes generar los requisitos en la sección correspondiente para poder
									construir el diagrama UML.
								</p>
								<Link
									href='/proyecto/requisitos'
									onClick={handleNextLink('/proyecto/requisitos')}
									className='btn text-base-50 bg-primary-100 hover:bg-primary-100/90 rounded-sm mt-2'
								>
									Ir a Requisitos
									<ArrowRight color='' size={20} />
								</Link>
							</section>
						)}

						{/* Caso 2: Tiene requisitos EARS Y el diagrama ya fue generado -> Mostrar PlantUmlViewer */}
						{selectedCharacteristic && !isLoadingRequirements && hasReqs && hasDiag && (
							<div className='flex flex-col flex-1 min-h-0 gap-4'>
								{!isPlantumlMaximized && (
									<div className='flex flex-col flex-1 min-h-0 gap-4'>
										<div className='flex flex-col gap-2 px-2'>
											<div className='inline-flex justify-between items-center w-full'>
												<div className='inline-flex justify-start gap-3 items-center'>
													<span className='text-2xl font-bold text-base-800'>
														{selectedCharacteristic.display_id}
													</span>
													<span className='text-2xl font-bold text-primary-100'>
														{selectedCharacteristic.title}
													</span>
												</div>
											</div>
											<p className='text-base-600 text-base'>
												{selectedCharacteristic.description}
											</p>
										</div>
										<div className='flex-1 min-h-0 mt-2'>
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

						{/* Caso 3: Tiene requisitos EARS pero NO tiene diagrama generado todavía -> Mostrar pantalla "Sin modelo generado" + Botón "Generar" */}
						{selectedCharacteristic && !isLoadingRequirements && hasReqs && !hasDiag && (
							<section className='flex flex-col h-full justify-center items-center gap-5 px-20'>
								<Ai color='text-ai' size={70} />

								<span className='text-center justify-start text-base-800 text-2xl font-medium'>
									Sin modelo generado
								</span>

								<p className='text-base-800 text-lg text-center'>
									Los requisitos EARS están listos. Haz clic en el botón{' '}
									<span className='text-xl font-bold'>Generar </span>
									para construir el diagrama de actividad UML automáticamente.
								</p>

								<button
									onClick={handleGenerate}
									className='btn text-base-50 bg-ai mt-2 hover:bg-ai/90'
								>
									<Ai color='' size={20} />
									Generar
								</button>
							</section>
						)}
					</div>
				</div>
			</div>
		</>
	);
};

export { ModelingPage };
