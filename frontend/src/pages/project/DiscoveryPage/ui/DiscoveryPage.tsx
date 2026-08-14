'use client';

import { useDiscoveryStore } from '@/entities/discovery';
import {
	Chatbot,
	MarkdownEditor,
	MarkdownEditorSkeleton,
	type MarkdownEditorHandle,
	type SaveStatus,
} from '@/feature';
import { Ai, ArrowRight, Loading, ModalConfirm, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useProjectStore } from '@/entities/project';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

const generatingDiscoveryMessages = [
	'Analizando información del proyecto...',
	'Identificando problemas y oportunidades...',
	'Generando documento de descubrimiento...',
];

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const currentProject = useProjectStore((s) => s.currentProject);
	const [isLoading] = useState(false);
	const [isGeneratingDiscovery, setIsGeneratingDiscovery] = useState(false);
	const savedContentRef = useRef('');
	const router = useRouter();
	const isSavingRef = useRef(false);

	const pendingNavigationPath = useAppStore((s) => s.pendingNavigationPath);
	const setPendingNavigationPath = useAppStore((s) => s.setPendingNavigationPath);
	const setHasUnsavedChanges = useAppStore((s) => s.setHasUnsavedChanges);
	const isEditorMaximized = useAppStore((s) => s.isEditorMaximized);
	const setEditorMaximized = useAppStore((s) => s.setEditorMaximized);

	const [isChatbotOpen, setIsChatbotOpen] = useState(false);
	const [isChatLoading, setIsChatLoading] = useState(false);
	const [hasUnsavedChanges, setHasUnsavedChangesLocal] = useState(false);
	const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');

	const chatHistory = useDiscoveryStore((s) => s.chatHistory);
	const sendChatMessage = useDiscoveryStore((s) => s.sendChatMessage);
	const getDiscovery = useDiscoveryStore((s) => s.getDiscovery);
	const saveDiscovery = useDiscoveryStore((s) => s.saveDiscovery);
	const generateDiscovery = useDiscoveryStore((s) => s.generateDiscovery);
	const currentDiscovery = useDiscoveryStore((s) => s.currentDiscovery);
	const hasDiscovery = !!currentDiscovery?.content;
	const [markdown, setMarkdown] = useState(currentDiscovery?.content ?? '');

	// Sync markdown with store after Zustand persist hydration.
	useEffect(() => {
		if (
			currentDiscovery?.content &&
			currentDiscovery.content !== savedContentRef.current
		) {
			setMarkdown(currentDiscovery.content);
			savedContentRef.current = currentDiscovery.content;
		}
	}, [currentDiscovery]);

	useEffect(() => {
		setHasUnsavedChangesLocal(markdown !== savedContentRef.current);
	}, [markdown]);

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

	useEffect(() => {
		if (!hasUnsavedChanges && pendingNavigationPath) {
			setPendingNavigationPath(null);
		}
	}, [hasUnsavedChanges, pendingNavigationPath, setPendingNavigationPath]);

	const doSave = async (): Promise<boolean> => {
		if (!currentProject) return false;

		setSaveStatus('saving');

		try {
			isSavingRef.current = true;
			await saveDiscovery(currentProject.id, markdown);
			savedContentRef.current = markdown;
			setHasUnsavedChangesLocal(false);
			setSaveStatus('saved');
			return true;
		} catch {
			setSaveStatus('error');
			return false;
		} finally {
			isSavingRef.current = false;
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

	const handleSendChat = async (content: string) => {
		if (!currentProject) return;
		setIsChatLoading(true);
		try {
			const response = await sendChatMessage(currentProject.id, content);
			if (response.modification) {
				const updated = await getDiscovery(currentProject.id);
				setMarkdown(updated.content);
				savedContentRef.current = updated.content;
			}
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : 'Error al enviar el mensaje.';
			toast.error(errorMessage);
		} finally {
			setIsChatLoading(false);
		}
	};

	const chatMessages = chatHistory;

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
				<ModalConfirm onCancel={cancelLeave} onConfirm={confirmLeave} />
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

						{!isEditorMaximized && hasDiscovery && (
							<div className='flex items-center gap-3 shrink-0'>
								<button
									onClick={() => setIsChatbotOpen(true)}
									className='btn btn-ai'
									title={
										!hasDiscovery ? 'Primero genera el documento de descubrimiento' : ''
									}
								>
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
									saveStatus={saveStatus}
									readOnly={isChatLoading}
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
					/>
				</div>
			</div>
		</>
	);
};

export { DiscoveryPage };
