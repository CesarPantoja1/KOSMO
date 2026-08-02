'use client';

import { useDiscoveryStore, type DiscoveryChatResponse } from '@/entities/discovery';
import type { PlanChange } from '@/entities/plan';
import { addPlanChange, deletePlanChange, usePlanStore } from '@/entities/plan';
import {
	Chatbot,
	FloatingPlan,
	MarkdownEditor,
	type MarkdownEditorHandle,
} from '@/feature';
import type { ChangeSuggestion, ChatMessage } from '@/feature/chatbot';
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
		change_suggestion: r.change_suggestion
			? {
					id: r.change_suggestion.id,
					section: r.change_suggestion.section,
					description: r.change_suggestion.description,
					diff_before: r.change_suggestion.diff_before,
					diff_after: r.change_suggestion.diff_after,
					rationale: r.change_suggestion.rationale,
				}
			: undefined,
	};
}

const DiscoveryPage = () => {
	const editorRef = useRef<MarkdownEditorHandle>(null);
	const [markdown, setMarkdown] = useState('');
	const currentProject = useAppStore((s) => s.currentProject);
	const [isLoading, setIsLoading] = useState(!!currentProject);
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
	const getDiscovery = useDiscoveryStore((s) => s.getDiscovery);
	const saveDiscovery = useDiscoveryStore((s) => s.saveDiscovery);
	const generateDiscovery = useDiscoveryStore((s) => s.generateDiscovery);

	const addToPlan = usePlanStore((s) => s.addToPlan);
	const removeFromPlan = usePlanStore((s) => s.removeFromPlan);

	useEffect(() => {
		setHasUnsavedChangesLocal(markdown !== savedContentRef.current);
	}, [markdown]);

	useEffect(() => {
		setHasUnsavedChanges(hasUnsavedChanges);
	}, [hasUnsavedChanges, setHasUnsavedChanges]);

	const fetchAndHydratePlan = usePlanStore((s) => s.fetchAndHydratePlan);

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
				setHasDiscovery(true);
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
					setHasDiscovery(false);
					setMarkdown('');
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
			fetchAndHydratePlan(currentProject.id, 'discovery');
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

	const handlePlanAction = (
		action: 'add' | 'remove' | 'discard',
		suggestion: ChangeSuggestion,
		messageId: string,
	) => {
		if (!currentProject) return;

		if (action === 'add') {
			const change: PlanChange = {
				id: suggestion.id,
				section: suggestion.section,
				description: suggestion.description ?? suggestion.section,
				diff: {
					before: suggestion.diff_before,
					after: suggestion.diff_after,
				},
				status: 'pending',
				origin: 'chat',
				phase: 'discovery',
				context: currentProject.id,
				rationale: suggestion.rationale ?? undefined,
				created_at: new Date().toISOString(),
			};
			addToPlan('discovery', change);
			addPlanChange(currentProject.id, 'discovery', change).catch((err) => {
				console.warn('[DiscoveryPage] Error al persistir cambio en backend:', err);
			});
		}

		if (action === 'remove') {
			removeFromPlan('discovery', suggestion.id);
			deletePlanChange(currentProject.id, 'discovery', suggestion.id).catch((err) => {
				console.warn('[DiscoveryPage] Error al eliminar cambio en backend:', err);
			});
		}
	};

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
					title='Generando Descubrimiento'
					description='La IA está analizando la información del proyecto. Por favor, espera un momento.'
					messages={generatingDiscoveryMessages}
				/>
			)}

			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			<div className={`page-container gap-2 ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header flex-8/12'>
					<h2 className='text-base-800 text-3xl font-bold'>
						Descubrimiento del proyecto
					</h2>
					<p className='text-base-600 text-lg'>
						Identificar y documentar la información estratégica del proyecto para
						comprender el problema, el contexto y el alcance del negocio.
					</p>
					{!isEditorMaximized && hasDiscovery && (
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
								className='btn bg-primary-100 text-base-50 hover:bg-primary-100/90 disabled:opacity-50'
							>
								<span className='text-center'>Ir a características</span>
								<ArrowRight size={20} color='text-base-50' />
							</button>
						</div>
					)}
					<div className='flex-1 flex flex-col min-h-0'>
						{isLoading && (
							<div className='w-full min-h-105 relative'>
								<div className='flex justify-end gap-3 mb-4'>
									<button
										disabled={true}
										className='btn bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
									>
										<Ai size={20} color='text-base-50' />
										<span className='text-center'>Refinar</span>
									</button>
									<button
										disabled={true}
										className='btn bg-primary-100 text-base-50 hover:bg-primary-100/90 disabled:opacity-50'
									>
										<span className='text-center'>Ir a características</span>
										<ArrowRight size={20} color='text-base-50' />
									</button>
								</div>

								<div className='w-full h-full rounded-sm border border-base-300 bg-base-50 shadow-sm overflow-hidden'>
									<div className='flex items-center justify-between border-b border-base-200 bg-base-100 px-4 py-3'>
										<div className='flex items-center gap-2'>
											<div className='h-4 w-20 animate-pulse rounded bg-base-200' />
											<div className='h-4 w-16 animate-pulse rounded bg-base-200' />
											<div className='h-4 w-16 animate-pulse rounded bg-base-200' />
										</div>
										<div className='h-8 w-8 animate-pulse rounded bg-base-200' />
									</div>

									<div className='space-y-4 p-6'>
										<div className='h-5 w-3/4 animate-pulse rounded bg-base-200' />
										<div className='h-5 w-full animate-pulse rounded bg-base-200' />
										<div className='h-5 w-5/6 animate-pulse rounded bg-base-200' />
										<div className='h-5 w-full animate-pulse rounded bg-base-200' />
										<div className='h-5 w-2/3 animate-pulse rounded bg-base-200' />
										<div className='h-28 w-full animate-pulse rounded-lg bg-base-200' />
									</div>
								</div>
							</div>
						)}

						{!isLoading && !isGeneratingDiscovery && !hasDiscovery && (
							<div className='w-full my-auto min-h-105 flex flex-col items-center justify-center'>
								<div className='flex flex-col items-center gap-4 text-center px-6'>
									<Ai color='text-ai' size={70} />
									<h3 className='text-xl font-semibold text-base-800'>
										Sin Descubrimiento generado
									</h3>
									<p className='text-base-600 max-w-md'>
										Aún no se ha generado el descubrimiento de este proyecto. Haz clic en
										el botón para que la IA analice la información y genere el documento.
									</p>
									<button
										onClick={handleGenerateDiscovery}
										className='btn bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
									>
										<Ai size={20} color='text-base-50' />
										<span className='text-center'>Generar</span>
									</button>
								</div>
							</div>
						)}

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
								/>
							</div>
						)}
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
