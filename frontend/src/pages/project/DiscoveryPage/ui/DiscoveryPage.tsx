'use client';

import { useDiscoveryStore, type DiscoveryChatResponse } from '@/entities/discovery';
import { usePlanActions } from '@/entities/plan';
import {
	Chatbot,
	FloatingPlan,
	MarkdownEditor,
	MarkdownEditorSkeleton,
	type MarkdownEditorHandle,
} from '@/feature';
import type { ChatMessage } from '@/feature/chatbot';
import { Ai, ArrowRight, Loading, ModalConfirmLeave, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

const generatingDiscoveryMessages = [
	'Analizando información del proyecto...',
	'Identificando problemas y oportunidades...',
	'Generando documento de descubrimiento...',
];

/** Adapta el tipo de dominio DiscoveryChatResponse al tipo generico ChatMessage del chatbot UI */
function toChatMessage(r: DiscoveryChatResponse): ChatMessage {
	return {
		id: r.id,
		role: r.role,
		content: r.content,
		created_at: r.created_at,
		change_suggestions: r.change_suggestions ?? undefined,
	};
}

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const [markdown, setMarkdown] = useState('');
	const currentProject = useAppStore((s) => s.currentProject);
	const [isLoading, _setIsLoading] = useState(!!currentProject);
	const [hasDiscovery, setHasDiscovery] = useState(false);
	const [isGeneratingDiscovery, setIsGeneratingDiscovery] = useState(false);
	const savedContentRef = useRef('');
	const router = useRouter();

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);

	const [isChatbotOpen, setIsChatbotOpen] = useState(false);
	const [isChatLoading, setIsChatLoading] = useState(false);
	const [hasUnsavedChanges, setHasUnsavedChangesLocal] = useState(false);

	const chatHistory = useDiscoveryStore((s) => s.chatHistory);
	const sendChatMessage = useDiscoveryStore((s) => s.sendChatMessage);
	const saveDiscovery = useDiscoveryStore((s) => s.saveDiscovery);
	const generateDiscovery = useDiscoveryStore((s) => s.generateDiscovery);

	useEffect(() => {
		setHasUnsavedChangesLocal(markdown !== savedContentRef.current);
	}, [markdown]);

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

	const getDiscovery = useDiscoveryStore((s) => s.getDiscovery);

	useEffect(() => {
		if (!currentProject) {
			router.push('/proyecto');
			return;
		}

		getDiscovery(currentProject.id)
			.then((data) => {
				setMarkdown(data.content);
				savedContentRef.current = data.content;
				setHasDiscovery(true);
			})
			.catch(() => {
				setMarkdown('');
				savedContentRef.current = '';
			})
			.finally(() => _setIsLoading(false));
	}, [currentProject, router]); // eslint-disable-line react-hooks/exhaustive-deps

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
		router.push('caracteristicas');
	};

	const handleGenerateDiscovery = async () => {
		if (!currentProject) return;

		setIsGeneratingDiscovery(true);
		try {
			const data = await generateDiscovery(currentProject.id);
			setMarkdown(data.content);
			savedContentRef.current = data.content;
			setHasDiscovery(true);
			toast.success('Descubrimiento generado exitosamente');
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'Error al generar el descubrimiento';
			toast.error(message);
		} finally {
			setIsGeneratingDiscovery(false);
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
				router.push('caracteristicas');
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

	const handlePlanAction = usePlanActions(
		currentProject?.id ?? null,
		'discovery',
		currentProject?.id ?? null,
	);

	const handleSendChat = async (content: string) => {
		if (!currentProject) return;
		setIsChatLoading(true);
		try {
			await sendChatMessage(currentProject.id, content);
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : 'Error al enviar el mensaje.';
			toast.error(errorMessage);
		} finally {
			setIsChatLoading(false);
		}
	};

	const chatMessages: ChatMessage[] = chatHistory.map(toChatMessage);

	return (
		<>
			{isGeneratingDiscovery && (
				<Loading
					title='Analizando tu proyecto'
					description='El asistente está procesando la información y generando el documento de descubrimiento.'
					messages={generatingDiscoveryMessages}
				/>
			)}

			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			<div className={`page-container gap-2 ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header flex-8/12'>
					<div className='flex items-start justify-between gap-4'>
						<div className='flex flex-col gap-1'>
							<h2 className='text-neutral-800 text-3xl font-bold'>
								Descubrimiento del proyecto
							</h2>
							<p className='text-neutral-500 text-base'>
								Identifica y documenta el problema de negocio, el contexto y el alcance de
								tu proyecto.
							</p>
						</div>

						{!isEditorMaximized && (
							<div className='flex items-center gap-3 shrink-0'>
								<button onClick={() => setIsChatbotOpen(true)} className='btn btn-ai'>
									<Ai size={18} color='' />
									Mejorar con IA
								</button>
								<button onClick={handleNextLink} className='btn btn-primary'>
									Continuar
									<ArrowRight size={18} color='' />
								</button>
							</div>
						)}
					</div>

					<div className='flex-1 flex flex-col min-h-0'>
						{/* Skeleton loading */}
						{isLoading && <MarkdownEditorSkeleton />}

						{/* Empty state */}
						{!isLoading && !isGeneratingDiscovery && !hasDiscovery && (
							<div className='w-full my-auto min-h-105 flex flex-col items-center justify-center'>
								<div className='flex flex-col items-center gap-5 text-center px-6 max-w-lg'>
									<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-ai-50'>
										<Ai color='text-ai-500' size={48} />
									</div>
									<div className='flex flex-col gap-2'>
										<h3 className='text-xl font-semibold text-neutral-800'>
											Aún no hay análisis del problema
										</h3>
										<p className='text-neutral-500 text-base'>
											El asistente analizará tu proyecto y generará un documento que
											describe el problema de negocio, el contexto y los objetivos.
										</p>
									</div>
									<button onClick={handleGenerateDiscovery} className='btn btn-ai btn-lg'>
										<Ai size={18} color='' />
										Analizar mi proyecto
									</button>
								</div>
							</div>
						)}

						{/* Editor with content */}
						{!isLoading && hasDiscovery && (
							<div className='w-full h-full relative'>
								<MarkdownEditor
									ref={editorRef}
									markdown={markdown}
									onChange={setMarkdown}
									isMaximized={isEditorMaximized}
									onMaximize={() => setEditorMaximized(true)}
									onMinimize={() => setEditorMaximized(false)}
								/>
								<FloatingPlan
									phase='discovery'
									navigateTo='/proyecto/descubrimiento/plan'
									contextId={currentProject?.id ?? null}
								/>
							</div>
						)}
					</div>
				</div>

				{/* Chatbot panel */}
				<div
					className={`chatbot ${
						isChatbotOpen
							? 'opacity-100 translate-x-0 w-96 shrink-0'
							: 'opacity-0 translate-x-8 pointer-events-none max-w-0 flex-none'
					}`}
				>
					<Chatbot
						placeholder='ej., ¿Qué alcance tiene el módulo de pagos?'
						onClose={() => setIsChatbotOpen(false)}
						messages={chatMessages}
						onSendMessage={handleSendChat}
						isLoading={isChatLoading}
						onPlanAction={handlePlanAction}
					/>
				</div>
			</div>
		</>
	);
};

export { DiscoveryPage };
