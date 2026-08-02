'use client';

import {
	FloatingPlan,
	MarkdownEditor,
	PanelAsistenteRequisito,
} from '@/feature';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import {
	usePlanActions,
	usePlanStore,
} from '@/entities/plan';
import {
	generateRequirements,
	getRequirements,
	saveRequirements,
	useRequirementsStore,
} from '@/entities/requirements';
import {
	Ai,
	ArrowRight,
	CursorClickFill,
	Loading,
	ModalConfirmLeave,
	toast,
} from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';

import { useCharacteristicStore } from '@/entities/characteristic';

import { Requirements } from '@/widgets/main-navbar/ui/icons';

const RequirementsPage = () => {
	const router = useRouter();

	// Plan store
	const fetchAndHydratePlan = usePlanStore((s) => s.fetchAndHydratePlan);

	// Características estado
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isGenerating, setIsGenerating] = useState(false);

	const characteristics = useCharacteristicStore((s) => s.currentCharacteristics);
	const storeGetCharacteristics = useCharacteristicStore((s) => s.getCharacteristics);

	// Requisitos estado
	const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);
	const hasRequirements = useRequirementsStore((s) => s.hasRequirements);
	const setHasRequirements = useRequirementsStore((s) => s.setHasRequirements);
	const selectedFeatureId = useRequirementsStore((s) => s.selectedFeatureId);
	const setSelectedFeatureId = useRequirementsStore((s) => s.setSelectedFeatureId);
	const [markdown, setMarkdown] = useState('');
	const [savedContent, setSavedContent] = useState('');

	// App estado
	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);
	const currentProject = useAppStore((s) => s.currentProject);

	// Otros estados
	const [isChatbotOpen, setIsChatbotOpen] = useState(false);
	const selectedCharacteristic = characteristics.find((c) => c.id === selectedId) ?? null;
	const hasUnsavedChanges = markdown !== savedContent;
	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);
	const [editorKey, setEditorKey] = useState(0);

	useEffect(() => {
		if (currentProject) {
			fetchAndHydratePlan(currentProject.id, 'requirements');
		}
	}, [currentProject, fetchAndHydratePlan]);

	const handlePlanAction = usePlanActions(
		currentProject?.id ?? null,
		'requirements',
		selectedId,
	);

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
				await storeGetCharacteristics(currentProject.id);
			} catch (err) {
				const message =
					err instanceof Error ? err.message : 'Error al cargar las características';
				toast.error(message);
			} finally {
				setIsLoading(false);
			}
		};

		fetch();
	}, [currentProject, router, storeGetCharacteristics]);

	useEffect(() => {
		if (!selectedId || !currentProject) return;

		let cancelled = false;
		const projectId = currentProject.id;
		const characteristicId = selectedId;

		const load = async () => {
			setIsLoadingRequirements(true);
			setMarkdown('');
			setSavedContent('');
			try {
				const content = (await getRequirements(projectId, characteristicId))
					.document_markdown;
				if (cancelled) return;
				if (content) {
					setHasRequirements(characteristicId, true);
				}
				useCharacteristicStore.setState((state) => ({
					currentCharacteristics: state.currentCharacteristics.map((c) =>
						c.id === characteristicId ? { ...c, requirements: content } : c,
					),
				}));
				setMarkdown(content);
				setSavedContent(content);
			} catch {
				if (!cancelled) toast.error('Error al cargar los requisitos');
			} finally {
				if (!cancelled) setIsLoadingRequirements(false);
			}
		};

		load();

		return () => {
			cancelled = true;
		};
	}, [selectedId, currentProject]);

	useEffect(() => {
		if (selectedFeatureId) {
			setSelectedId(selectedFeatureId);
			setSelectedFeatureId(null);
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

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
		// Cerrar chat si la nueva característica no tiene requisitos
		if (!hasRequirements[id]) {
			setIsChatbotOpen(false);
		}
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
			const content = await generateRequirements(
				currentProject.id,
				selectedCharacteristic.id,
			);
			if (content) {
				setHasRequirements(selectedCharacteristic.id, true);
			}
			useCharacteristicStore.setState((state) => ({
				currentCharacteristics: state.currentCharacteristics.map((c) =>
					c.id === selectedCharacteristic.id
						? { ...c, requirements: content.document_markdown }
						: c,
				),
			}));
			setMarkdown(content.document_markdown);
			setSavedContent(content.document_markdown);
			setEditorKey((prev) => prev + 1);
		} catch (_err) {
			toast.error('Error al generar los requisitos');
			console.log(_err);
		} finally {
			setIsGenerating(false);
		}
	};

	const handleSave = async (): Promise<boolean> => {
		if (!selectedCharacteristic || !currentProject) return false;

		const savingToast = toast.info('Guardando...');

		try {
			await saveRequirements(currentProject.id, selectedCharacteristic.id, markdown);
			if (markdown) {
				setHasRequirements(selectedCharacteristic.id, true);
			}
			setSavedContent(markdown);
			useCharacteristicStore.setState((state) => ({
				currentCharacteristics: state.currentCharacteristics.map((c) =>
					c.id === selectedCharacteristic.id ? { ...c, requirements: markdown } : c,
				),
			}));
			toast.close(savingToast);
			toast.success('Guardado');
			return true;
		} catch (_err) {
			toast.close(savingToast);
			toast.error('No se pudo guardar');
			console.log(_err);
			return false;
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

	useEffect(() => {
		if (hasUnsavedChanges) {
			const handler = (e: BeforeUnloadEvent) => {
				e.preventDefault();
			};
			window.addEventListener('beforeunload', handler);
			return () => window.removeEventListener('beforeunload', handler);
		}
	}, [hasUnsavedChanges]);

	useEffect(() => {
		const handler = () => {
			if (hasUnsavedChanges) {
				setPendingNavigationPath(window.location.href);
			}
		};
		window.addEventListener('popstate', handler);
		return () => window.removeEventListener('popstate', handler);
	}, [hasUnsavedChanges, setPendingNavigationPath]);

	useEffect(() => {
		if (markdown === savedContent) return;

		const timer = setTimeout(() => {
			handleSave();
		}, 3000);

		return () => clearTimeout(timer);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [markdown]);

	if (isLoading) {
		return (
			<div className='page-container'>
				<div className='page-header'>
					<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>
					<p className='text-base-600 text-lg'>
						Usa el asistente de IA para desglosar y estructurar los requisitos específicos
						de cada función de la lista.
					</p>
					<div className='inline-flex justify-end items-start gap-3 text-base-50'>
						<button disabled className='btn text-base-50 disabled:opacity-50 bg-ai'>
							<Ai color='' size={20} />
							Refinar
						</button>

						<Link
							href='modelo'
							aria-disabled
							onClick={(e) => e.preventDefault()}
							className='btn text-base-50 disabled:opacity-50 bg-primary-100 hover:bg-primary-100/90'
						>
							Ir a modelo
							<ArrowRight color='' size={20} />
						</Link>
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
			</div>
		);
	}

	return (
		<>
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
					title='Generando requisitos EARS'
					description='Estructurando la característica seleccionada bajo el estándar EARS. Esto tomará unos segundos.'
				/>
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header'>
					<h2 className='text-3xl font-bold text-base-800'>Generar requisitos</h2>
					<p className='text-base-600 text-lg'>
						Usa el asistente de IA para desglosar y estructurar los requisitos específicos
						de cada función de la lista.
					</p>

					{!isEditorMaximized && (
						<div className='inline-flex justify-end items-start gap-3 text-base-50'>
							<button
								onClick={() => setIsChatbotOpen(true)}
								disabled={!hasRequirements[selectedId ? selectedId : '']}
								className='btn bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
							>
								<Ai size={20} color='text-base-50' />
								<span className='text-center'>Refinar</span>
							</button>

							<Link
								href='modelo'
								onClick={handleNextLink('modelo')}
								className='btn text-base-50 bg-primary-100 hover:bg-primary-100/90 rounded-sm'
							>
								Ir a modelo
								<ArrowRight color='' size={20} />
							</Link>
						</div>
					)}

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
									return (
										<button
											key={c.id}
											onClick={() => handleSelectCharacteristic(c.id)}
											className={`w-full p-3 flex justify-start items-start gap-3 text-left cursor-pointer transition-colors ${
												isSelected
													? 'bg-primary-100/10 border-l-4 border-primary-100'
													: 'border-l-4 border-transparent hover:bg-base-200/30'
											}`}
										>
											<span
												className={`text-base font-bold mt-0.5 shrink-0 ${
													isSelected ? 'text-base-800' : 'text-base-800'
												}`}
											>
												{c.display_id}
											</span>
											<p
												className={`flex-1 text-sm font-medium leading-snug pt-0.5 ${
													isSelected ? 'text-primary-100' : 'text-base-600'
												}`}
											>
												{c.title}
											</p>
											{hasRequirements[c.id] && (
												<div className='shrink-0 mt-0.5'>
													<Requirements
														size={20}
														color={isSelected ? 'text-primary-100' : 'text-base-600'}
													/>
												</div>
											)}
										</button>
									);
								})}
							</div>
						</aside>

						<div className='relative flex-1 flex flex-col pl-2 pt-2 bg-base-100/50 min-h-0 overflow-hidden'>
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
												Selecciona una característica del listado lateral para ver su
												detalle
												<br />o comenzar a generar sus requisitos EARS.
											</div>
										</div>
									</div>
								</div>
							)}

							{selectedCharacteristic && isLoadingRequirements && (
								<div className='flex flex-1 items-center justify-center'>
									<span className='text-base-600 text-lg'>Cargando requisitos...</span>
								</div>
							)}

							{selectedCharacteristic &&
								!isLoadingRequirements &&
								hasRequirements[selectedCharacteristic.id] && (
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
											<MarkdownEditor
												key={editorKey}
												markdown={markdown}
												onChange={setMarkdown}
												isMaximized={isEditorMaximized}
												onMaximize={() => setEditorMaximized(true)}
												onMinimize={() => setEditorMaximized(false)}
											/>
										</div>
									</div>
								)}

							{selectedCharacteristic &&
								!isLoadingRequirements &&
								!hasRequirements[selectedCharacteristic.id] && (
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

										<section className='flex flex-col h-full justify-center items-center gap-5 px-20'>
											<Ai color='text-ai' size={70} />

											<span className='text-center justify-start text-base-800 text-2xl font-medium'>
												Sin requisitos EARS
											</span>

											<p className='text-base-800 text-lg text-center'>
												Esta característica aún no tiene requisitos generados. Haz clic en
												el botón <span className='text-xl font-bold'>Generar </span>
												para estructurarlos y completarlos automáticamente bajo el formato
												EARS.
											</p>

											<button
												onClick={handleGenerate}
												className='btn text-base-50 bg-ai mt-2 hover:bg-ai/90'
											>
												<Ai color='' size={20} />
												Generar
											</button>
										</section>
									</div>
								)}

							<FloatingPlan phase='requirements' navigateTo='/proyecto/requisitos/plan' contextId={selectedId} />
						</div>
					</div>
				</div>

				<div
					className={`chatbot
						${
							isChatbotOpen
								? 'opacity-100 translate-x-0 flex-4/12'
								: 'opacity-0 translate-x-8 pointer-events-none max-w-0 flex-none'
						}
				`}
				>
					<PanelAsistenteRequisito
						featureId={selectedId}
						onClose={() => setIsChatbotOpen(false)}
						onPlanAction={handlePlanAction}
					/>
				</div>
			</div>
		</>
	);
};

export { RequirementsPage };
