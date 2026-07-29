'use client';

import { generateCharacteristics } from '@/entities/characteristic';
import {
	getDiscovery,
	saveDiscovery,
	useDiscoveryStore,
	type DiscoveryChatResponse,
} from '@/entities/discovery';
import type { PlanChange } from '@/entities/plan';
import { addPlanChange, deletePlanChange, usePlanStore } from '@/entities/plan';
import { Chatbot, MarkdownEditor, type MarkdownEditorHandle } from '@/feature';
import type { ChangeSuggestion, ChatMessage } from '@/feature/chatbot';
import { Ai, ArrowRight, ModalConfirmLeave, toast } from '@/shared/ui';
import { useAppStore } from 'app/store/app.store';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { FloatingDiscoveryPlan } from './FloatingPlan';

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
	const [isGenerating, setIsGenerating] = useState(false);
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
	const [editorKey, setEditorKey] = useState(0);

	const chatHistory = useDiscoveryStore((s) => s.chatHistory);
	const storeSendChatMessage = useDiscoveryStore((s) => s.sendChatMessage);

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

	const handlePlanAction = (
		action: 'add' | 'remove' | 'discard',
		suggestion: ChangeSuggestion,
		messageId: string,
	) => {
		if (!currentProject) return;

		if (action === 'add') {
			const change: PlanChange = {
				id: messageId,
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
			addPlanChange(currentProject.id, change.id).catch((err) => {
				console.warn('[DiscoveryPage] Error al persistir cambio en backend:', err);
			});
		}

		if (action === 'remove') {
			removeFromPlan('discovery', messageId);
			deletePlanChange(currentProject.id, 'discovery', messageId).catch((err) => {
				console.warn('[DiscoveryPage] Error al eliminar cambio en backend:', err);
			});
		}
	};

	const handleSendChat = async (content: string) => {
		if (!currentProject) return;
		setIsChatLoading(true);
		try {
			await storeSendChatMessage(currentProject.id, content);
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
			{pendingNavigationPath && (
				<ModalConfirmLeave onCancel={cancelLeave} onConfirm={confirmLeave} />
			)}

			<div className={`page-container ${isEditorMaximized ? 'px-8' : 'px-0'}`}>
				<div className='page-header'>
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
				</div>

				<div className='page-row'>
					<div className='flex-1 flex flex-col min-h-0'>
						{/* TODO: Mejorar el skeleton */}
						{isLoading && (
							<div className='w-full min-h-105 relative'>
								<div className='w-full h-full rounded-xl border border-base-300 bg-base-50 shadow-sm overflow-hidden'>
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
						className={`chatbot-panel ${isChatbotOpen ? '' : 'closed'}`}
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
			</div>
		</>
	);
};

export { DiscoveryPage };
