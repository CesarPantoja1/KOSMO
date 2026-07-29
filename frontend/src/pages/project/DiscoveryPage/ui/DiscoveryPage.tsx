'use client';

import { generateCharacteristics } from '@/entities/characteristic';
import { Chatbot, MarkdownEditor, type MarkdownEditorHandle } from '@/feature';
import { Ai, ArrowRight, Loading, ModalConfirmLeave, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { getDiscovery, refineDiscovery, saveDiscovery } from '@/entities/discovery';
import { FloatingDiscoveryPlan } from './FloatingPlan';

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const [markdown, setMarkdown] = useState('');
	const currentProject = useAppStore((s) => s.currentProject);
	const [isLoading, setIsLoading] = useState(!!currentProject);
	const [isGenerating, setIsGenerating] = useState(false);
	const savedContentRef = useRef('');
	const router = useRouter();

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);

	const [isChatbotOpen, setIsChatbotOpen] = useState(false);
	const [isRefining, setIsRefining] = useState(false);
	const [hasUnsavedChanges, setHasUnsavedChangesLocal] = useState(false);
	const [editorKey, setEditorKey] = useState(0);

	useEffect(() => {
		setHasUnsavedChangesLocal(markdown !== savedContentRef.current);
	}, [markdown]);

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

	const fetchAndHydratePlan = useAppStore((s) => s.fetchAndHydratePlan);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		const fetchDiscovery = async () => {
			setIsLoading(true);
			try {
				const data = await getDiscovery(currentProject.id);
				setMarkdown(data.content);
				savedContentRef.current = data.content;
				// Sprint 4 (T9) — Sincronizar e hidratar el plan desde el backend
				fetchAndHydratePlan(currentProject.id, 'discovery');
			} catch (err) {
				const errorStatus =
					err && typeof err === 'object' && 'status' in err
						? (err as { status: unknown }).status
						: undefined;
				const errorMessage = err instanceof Error ? err.message : '';
				if (
					errorStatus === 404 ||
					errorMessage.includes('404') ||
					errorMessage.includes('no existe')
				) {
					setMarkdown(
						'## Visión del producto\n\nAún no hay descubrimiento para este proyecto.',
					);
					savedContentRef.current = '';
				} else {
					toast.error(errorMessage || 'Error al cargar el descubrimiento');
				}
			} finally {
				setIsLoading(false);
			}
		};

		fetchDiscovery();
	}, [currentProject, router, fetchAndHydratePlan]);

	const doSave = async (): Promise<boolean> => {
		if (!currentProject) return false;

		const savingToast = toast.info('Guardando...');

		try {
			await saveDiscovery(currentProject.id, markdown);
			savedContentRef.current = markdown;
			setHasUnsavedChangesLocal(false);
			toast.close(savingToast);
			toast.success('Guardado');
			return true;
		} catch {
			toast.close(savingToast);
			toast.error('No se pudo guardar');
			return false;
		}
	};

	const handleNextLink = async () => {
		const { hasUnsavedChanges, setPendingNavigationPath } = useAppStore.getState();
		if (hasUnsavedChanges) {
			setPendingNavigationPath('caracteristicas');
			return;
		}
		await generateAndNavigate();
	};

	const generateAndNavigate = async () => {
		if (!currentProject) return;

		setIsGenerating(true);
		try {
			await generateCharacteristics(currentProject.id);
			router.push('caracteristicas');
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'Error al generar las características';
			toast.error(message);
		} finally {
			setIsGenerating(false);
		}
	};

	const confirmLeave = async () => {
		const path = pendingNavigationPath;
		setPendingNavigationPath(null);
		if (!path) return;
		if (path === 'caracteristicas') {
			const saved = await doSave();
			setHasUnsavedChanges(false);
			if (saved) {
				await generateAndNavigate();
			}
		} else {
			setHasUnsavedChanges(false);
			router.push(path);
		}
	};

	const cancelLeave = () => {
		setPendingNavigationPath(null);
	};

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
		if (markdown === savedContentRef.current) return;

		const timer = setTimeout(() => {
			doSave();
		}, 3000);

		return () => clearTimeout(timer);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [markdown]);

	const handleRefine = async (instructions: string) => {
		if (!currentProject) return;
		setIsChatbotOpen(false);
		setIsRefining(true);
		try {
			const data = await refineDiscovery(currentProject.id, instructions);
			setMarkdown(data.content);
			savedContentRef.current = data.content;
			setHasUnsavedChangesLocal(false);
			setEditorKey((prev) => prev + 1);
			toast.success('Documento refinado correctamente');
		} catch (err) {
			const errorMessage =
				err instanceof Error
					? err.message
					: 'No se pudo refinar el documento. Intenta nuevamente.';
			toast.error(errorMessage);
		} finally {
			setIsRefining(false);
		}
	};

	return (
		<>
			{isRefining && (
				<Loading
					title='Refinando descubriemiento del proyecto'
					description='Optimizando la estructura del descubrimiento del proyecto. Porfavor, espere un momento.'
				/>
			)}

			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header flex-8/12'>
					<h2 className='text-base-800 text-3xl font-bold'>
						Descubrimiento del proyecto
					</h2>
					<p className='text-base-600 text-lg'>
						Identificar y documentar la información estratégica del proyecto para
						comprender el problema, el contexto y el alcance del negocio.
					</p>

					{!isEditorMaximized && (
						<div className='flex justify-end gap-3'>
							<button
								onClick={() => setIsChatbotOpen(true)}
								className='btn bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
							>
								<Ai size={20} color='text-base-50' />
								<span className='text-center'>Refinar</span>
							</button>
							<button
								onClick={handleNextLink}
								disabled={isGenerating}
								className='btn bg-primary-100 text-base-50 hover:bg-primary-100/90 disabled:opacity-50'
							>
								<span className='text-center'>
									{isGenerating ? 'Generando...' : 'Ir a características'}
								</span>
								<ArrowRight size={20} color='text-base-50' />
							</button>
						</div>
					)}

					{!isLoading && (
						<div className='w-full h-full relative'>
							<MarkdownEditor
								key={editorKey}
								ref={editorRef}
								markdown={markdown}
								onChange={setMarkdown}
								isMaximized={isEditorMaximized}
								onMaximize={() => setEditorMaximized(true)}
								onMinimize={() => setEditorMaximized(false)}
							/>

							<FloatingDiscoveryPlan />
						</div>
					)}
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
					<Chatbot
						placeholder='ej., Haz que la visión del producto sea más concisa y enfócate en los resultados estratégicos'
						onClose={() => setIsChatbotOpen(false)}
						onSubmitInstructions={handleRefine}
					/>
				</div>
			</div>
		</>
	);
};

export { DiscoveryPage };
