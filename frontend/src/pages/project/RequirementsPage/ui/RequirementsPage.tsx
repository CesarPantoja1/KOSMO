'use client';

import {
	FloatingPlan,
	MarkdownEditor,
	MarkdownEditorSkeleton,
	PanelAsistenteRequisito,
	type SaveStatus,
} from '@/feature';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { usePlanActions, usePlanStore } from '@/entities/plan';
import { useRequirementsStore } from '@/entities/requirements';
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

import { useCharacteristicStore } from '@/entities/characteristic';

import { AsideCharacteristic } from '@/widgets';
import { Requirements } from '@/widgets/main-navbar/ui/icons';

const generatingRequirementsMessages = [
	'Analizando característica...',
	'Generando requisitos EARS...',
	'Finalizando generación de requisitos...',
];

const RequirementsPage = () => {
	const router = useRouter();

	// Plan store
	const fetchAndHydratePlan = usePlanStore((s) => s.fetchAndHydratePlan);

	// Características estado
	const characteristics = useCharacteristicStore((s) => s.currentCharacteristics);
	const selectedId = useCharacteristicStore((s) => s.selectedId);
	const setSelectedId = useCharacteristicStore((s) => s.setSelectedId);
	const [isLoading] = useState(false);
	const [isGenerating, setIsGenerating] = useState(false);

	// Requisitos estado
	const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);
	const hasRequirements = useRequirementsStore((s) => s.hasRequirements);
	const currentRequirements = useRequirementsStore((s) => s.currentRequirements);
	const getRequirements = useRequirementsStore((s) => s.getRequirements);
	const saveRequirements = useRequirementsStore((s) => s.saveRequirements);
	const generateRequirements = useRequirementsStore((s) => s.generateRequirements);
	const [markdown, setMarkdown] = useState('');
	const [savedContent, setSavedContent] = useState('');
	const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');

	// App estado
	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);
	const currentProject = useProjectStore((s) => s.currentProject);

	// Otros estados
	const [isChatbotOpen, setIsChatbotOpen] = useState(false);
	const selectedCharacteristic = characteristics.find((c) => c.id === selectedId) ?? null;
	const hasUnsavedChanges = markdown !== savedContent;
	const [pendingCharSwitch, setPendingCharSwitch] = useState<string | null>(null);

	const selectedIdRef = useRef(selectedId);
	useEffect(() => {
		selectedIdRef.current = selectedId;
		console.log('id actual es ' + selectedIdRef.current);
		console.log('id actual es ' + markdown);
	}, [selectedId]);

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
		if (!selectedId || !currentProject) return;

		let cancelled = false;

		const load = async () => {
			const storedContent = currentRequirements[selectedId];
			if (storedContent) {
				setMarkdown(storedContent);
				setSavedContent(storedContent);
				return;
			}

			setIsLoadingRequirements(true);
			try {
				const content = await getRequirements(currentProject.id, selectedId);
				if (cancelled) return;
				setMarkdown(content);
				setSavedContent(content);
			} catch (err) {
				if (!cancelled && (err as { status?: number }).status !== 404) {
					toast.error('Error al cargar los requisitos');
				}
			} finally {
				if (!cancelled) setIsLoadingRequirements(false);
			}
		};

		load();

		return () => {
			cancelled = true;
		};
	}, [selectedId, currentProject]);

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
			setMarkdown(content);
			setSavedContent(content);
		} catch (_err) {
			toast.error('Error al generar los requisitos');
			console.log(_err);
		} finally {
			setIsGenerating(false);
		}
	};

	const handleSave = async (): Promise<boolean> => {
		const charId = selectedIdRef.current;
		if (!charId || !currentProject) return false;

		setSaveStatus('saving');

		try {
			await saveRequirements(currentProject.id, charId, markdown);
			setSavedContent(markdown);
			setSaveStatus('saved');
			return true;
		} catch (_err) {
			setSaveStatus('error');
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

	const hasCharacteristics = characteristics.length > 0;

	return (
		<>
			{pendingCharSwitch && (
				<ModalConfirm onCancel={handleCancelSwitch} onConfirm={handleConfirmSwitch} />
			)}

			{pendingNavigationPath && (
				<ModalConfirm onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{isGenerating && (
				<Loading
					title='Generando criterios de aceptación'
					description='Estructurando la funcionalidad seleccionada bajo el estándar EARS. Esto tomará unos segundos.'
					messages={generatingRequirementsMessages}
				/>
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header'>
					{/* Header row */}
					<div className='flex items-start justify-between gap-4'>
						<div className='flex flex-col gap-1'>
							<h2 className='text-neutral-800 text-3xl font-bold'>
								Criterios de aceptación
							</h2>
							<p className='text-neutral-500 text-base'>
								Estructura los requisitos de cada funcionalidad bajo el estándar EARS.
							</p>
						</div>

						{!isLoading && hasCharacteristics && !isEditorMaximized && (
							<div className='flex items-center gap-3 shrink-0'>
								<button
									onClick={() => setIsChatbotOpen(true)}
									disabled={!hasRequirements[selectedId ? selectedId : '']}
									className='btn btn-ai disabled:opacity-50 disabled:cursor-not-allowed'
								>
									<Ai size={18} color='' />
									Mejorar con IA
								</button>
								<Link
									href='modelo'
									onClick={handleNextLink('modelo')}
									className='btn btn-primary'
								>
									Continuar
									<ArrowRight color='' size={18} />
								</Link>
							</div>
						)}
					</div>

					{isLoading ? (
						<div className='flex gap-1 flex-1 min-h-0 pb-4'>
							<div className='w-72 bg-neutral-50 border-r border-neutral-200 rounded-lg flex flex-col gap-3 p-3 animate-pulse shrink-0'>
								<div className='h-5 bg-neutral-200 rounded-md w-40' />
								{[1, 2, 3, 4].map((i) => (
									<div key={i} className='h-12 bg-neutral-200 rounded-md' />
								))}
							</div>
							<div className='flex-1 min-h-0 bg-neutral-50'>
								<div className='flex flex-col gap-3 h-full min-h-0'>
									<div className='flex flex-col gap-1 px-4 mt-3'>
										<div className='flex items-center gap-2'>
											<div className='h-4 w-16 rounded-md bg-neutral-200 animate-pulse' />
											<div className='h-4 w-48 rounded-md bg-neutral-200 animate-pulse' />
										</div>
										<div className='h-4 w-full max-w-2xl rounded-md bg-neutral-200 animate-pulse' />
									</div>
									<MarkdownEditorSkeleton />
								</div>
							</div>
						</div>
					) : !hasCharacteristics ? (
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
										definir sus criterios de aceptación.
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
								hasIcon={hasRequirements}
								icon={Requirements}
							/>

							{/* Content area */}
							<div className='relative flex-1 flex flex-col pl-3 pt-2 bg-neutral-50 border-l border-neutral-200 min-h-0 overflow-hidden'>
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
												Elige una funcionalidad del listado lateral para ver o generar sus
												criterios de aceptación.
											</p>
										</div>
									</div>
								)}

								{/* Loading requirements */}
								{selectedCharacteristic && isLoadingRequirements && (
									<div className='flex flex-1 items-center justify-center gap-3'>
										<div className='h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-primary-500' />
										<span className='text-neutral-500 text-sm'>
											Cargando criterios...
										</span>
									</div>
								)}

								{/* Has requirements — editor */}
								{selectedCharacteristic &&
									!isLoadingRequirements &&
									hasRequirements[selectedCharacteristic.id] &&
									markdown && (
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
												<MarkdownEditor
													key={selectedId}
													markdown={markdown}
													onChange={setMarkdown}
													isMaximized={isEditorMaximized}
													onMaximize={() => setEditorMaximized(true)}
													onMinimize={() => setEditorMaximized(false)}
													saveStatus={saveStatus}
												/>
											</div>
										</div>
									)}

								{/* No requirements — empty state */}
								{selectedCharacteristic &&
									!isLoadingRequirements &&
									!hasRequirements[selectedCharacteristic.id] && (
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
														Aún no hay criterios generados
													</h3>
													<p className='text-neutral-500 text-sm'>
														Esta funcionalidad aún no tiene criterios de aceptación. El
														asistente los estructurará automáticamente bajo el formato
														EARS.
													</p>
												</div>
												<button onClick={handleGenerate} className='btn btn-ai'>
													<Ai color='' size={18} />
													Generar criterios
												</button>
											</div>
										</div>
									)}

								<FloatingPlan
									phase='requirements'
									navigateTo='/proyecto/requisitos/plan'
									contextId={selectedId}
								/>
							</div>
						</div>
					)}
				</div>

				{/* Chatbot panel */}
				<div
					className={`chatbot ${
						isChatbotOpen
							? 'opacity-100 translate-x-0 w-96 shrink-0'
							: 'opacity-0 translate-x-8 pointer-events-none max-w-0 flex-none'
					}`}
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
