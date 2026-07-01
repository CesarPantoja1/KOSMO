'use client';

import { ChatbotPopup, MarkdownEditor, type MarkdownEditorHandle } from '@/feature';
import { useAppStore } from 'app/store/app.store';
import { Ai, ArrowRight, Loading, toast } from '@/shared/ui';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { getDiscovery, saveDiscovery, refineDiscovery } from '../api/api';
import { generateCharacteristics } from '@/entities/characteristic';

import ModalConfimLeave from './ModalConfimLeave';

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
	const [hasUnsavedChanges, setHasUnsavedChangesLocal] = useState(false);

	useEffect(() => {
		setHasUnsavedChangesLocal(markdown !== savedContentRef.current);
	}, [markdown]);

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

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
	}, [currentProject, router]);

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
		try {
			const data = await refineDiscovery(currentProject.id, instructions);
			setMarkdown(data.content);
			savedContentRef.current = data.content;
			setHasUnsavedChangesLocal(false);
			toast.success('Documento refinado correctamente');
			setIsChatbotOpen(false);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Error al refinar';
			toast.error(errorMessage);
			throw err; 
		}
	};

	return (
		<>
			{isChatbotOpen && <ChatbotPopup onClose={() => setIsChatbotOpen(false)} onSubmitInstructions={handleRefine} />}

			{pendingNavigationPath && (
				<ModalConfimLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			{isLoading && <Loading title='Generando Descripción General' description='Optimizando la estructura de la Descripción General. Por favor, espera un momento.' />}

			<div
				className={`flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8 pb-4 ${isEditorMaximized ? 'px-8' : 'px-0'}`}
			>
				<div className='flex flex-col gap-3'>
					<div className='flex flex-col'>
						<h3 className='text-base-800 text-3xl font-bold'>
							Descubrimiento del proyecto
						</h3>
						<p className='text-base-600 mt-2'>
							Identificar y documentar la información estratégica del proyecto para
							comprender el problema, el contexto y el alcance del negocio.
						</p>
					</div>
					{!isEditorMaximized && (
						<div className='flex justify-end gap-3'>
							<button
								onClick={() => setIsChatbotOpen(true)}
								className='flex justify-center cursor-pointer items-center px-3.5 py-1.5 gap-1 rounded-sm bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
							>
								<Ai size={20} color='text-base-50' />
								<span className='text-center font-semibold'>Refinar</span>
							</button>
							<button
								onClick={handleNextLink}
								disabled={isGenerating}
								className='flex justify-center cursor-pointer items-center px-3.5 py-1.5 gap-1 rounded-sm bg-primary-100 text-base-50 hover:bg-primary-100/90 disabled:opacity-50'
							>
								<span className='text-center font-semibold'>
									{isGenerating ? 'Generando...' : 'Ir a características'}
								</span>
								<ArrowRight size={20} color='text-base-50' />
							</button>
						</div>
					)}
				</div>

				{!isLoading && (
					<div className='flex-1 min-h-0'>
						<MarkdownEditor
							ref={editorRef}
							markdown={markdown}
							onChange={setMarkdown}
							isMaximized={isEditorMaximized}
							onMaximize={() => setEditorMaximized(true)}
							onMinimize={() => setEditorMaximized(false)}
						/>
					</div>
				)}
			</div>
		</>
	);
};

export { DiscoveryPage };
