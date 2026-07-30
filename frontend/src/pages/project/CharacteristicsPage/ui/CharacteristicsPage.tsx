'use client';

import {
	useCharacteristicStore,
	type CharacteristicChatResponse,
} from '@/entities/characteristic';
import {
	addPlanChange,
	deletePlanChange,
	usePlanStore,
	type PlanChange,
} from '@/entities/plan';
import { Chatbot, FloatingPlan } from '@/feature';
import type { ChangeSuggestion, ChatMessage } from '@/feature/chatbot';
import { Plus, toast } from '@/shared/ui';
import ArrowRight from '@/shared/ui/icons/ArrowRight';
import { useAppStore } from 'app/store/app.store';
import Link from 'next/link';
import { useState } from 'react';
import { useCharacteristicsPage } from '../hooks/use-characteristics-page';
import CardCharacterist from './CardCharacterist';
import Search from './Search';

function toChatMessage(r: CharacteristicChatResponse): ChatMessage {
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

const CharacteristicsPage = () => {
	const { isLoading, searchQuery, setSearchQuery, filtered } = useCharacteristicsPage();

	const [activeFeatureId, setActiveFeatureId] = useState<string | null>(null);
	const [isChatLoading, setIsChatLoading] = useState(false);

	const currentProject = useAppStore((s) => s.currentProject);

	const chatHistories = useCharacteristicStore((s) => s.chatHistories);
	const storeSendChatMessage = useCharacteristicStore((s) => s.sendChatMessage);

	const addToPlan = usePlanStore((s) => s.addToPlan);
	const removeFromPlan = usePlanStore((s) => s.removeFromPlan);

	const handleRefine = (featureId: string) => {
		setActiveFeatureId(featureId);
	};

	const handleSendChat = async (content: string) => {
		if (!activeFeatureId) return;
		setIsChatLoading(true);
		try {
			await storeSendChatMessage(activeFeatureId, content);
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : 'Error al enviar el mensaje.';
			toast.error(errorMessage);
		} finally {
			setIsChatLoading(false);
		}
	};

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
				phase: 'features',
				context: currentProject.id,
				rationale: suggestion.rationale ?? undefined,
				created_at: new Date().toISOString(),
			};
			addToPlan('features', change);
			addPlanChange(currentProject.id, 'features', change).catch((err) => {
				console.warn('[CharacteristicsPage] Error al persistir cambio en backend:', err);
			});
		}

		if (action === 'remove') {
			removeFromPlan('features', messageId);
			deletePlanChange(currentProject.id, 'features', messageId).catch((err) => {
				console.warn('[CharacteristicsPage] Error al eliminar cambio en backend:', err);
			});
		}
	};

	const chatMessages: ChatMessage[] = (chatHistories[activeFeatureId!] ?? []).map(
		toChatMessage,
	);

	return (
		<div className='page-container gap-2'>
			<div className='page-header'>
				<h2 className='text-base-800 text-3xl font-bold'>Características</h2>
				<p className='text-base-600 text-lg'>
					Gestiona y organiza las funciones principales de tu proyecto. Tienes el control
					total para editar, eliminar o añadir nuevas características según tus
					necesidades.
				</p>
				<div className='w-full inline-flex justify-between items-center gap-4'>
					<Search value={searchQuery} onChange={setSearchQuery} />
					<div className='flex justify-end items-center gap-4'>
						<Link
							href='caracteristicas/nueva'
							className='btn bg-primary-100 hover:bg-primary-100/90'
						>
							<Plus color='text-base-50' size={20} />
							<span className='text-center text-base-50'>Nueva Característica</span>
						</Link>

						<Link
							href='requisitos'
							className='btn bg-primary-100 hover:bg-primary-100/90'
						>
							<div className='text-center text-base-50'>Ir a Requisitos</div>
							<ArrowRight color='text-base-50' size={20} />
						</Link>
					</div>
				</div>

				<div className='relative flex-1 flex flex-col min-h-0 overflow-y-auto'>
					{isLoading && (
						<div className='overflow-y-auto flex flex-col gap-4 pb-4'>
							{[1, 2, 3, 4, 5].map((i) => (
								<div
									key={i}
									className='outline outline-base-300 m-0.5 p-8 inline-flex justify-start items-center gap-7 animate-pulse'
								>
									<div className='w-14 h-10 bg-base-200 rounded' />
									<div className='flex-1 flex flex-col gap-3'>
										<div className='h-6 bg-base-200 rounded w-3/4' />
										<div className='h-4 bg-base-200 rounded w-full' />
									</div>
								</div>
							))}
						</div>
					)}

					{!isLoading && (
						<>
							<div className='overflow-y-auto flex flex-col gap-4 pb-4'>
								{filtered.length === 0 && searchQuery.trim() ? (
									<div className='outline outline-base-300 m-0.5 px-8 py-16 flex flex-col justify-center items-center gap-4'>
										<p className='text-base-600 text-lg font-medium text-center'>
											No se encontraron características que coincidan con su búsqueda
										</p>
									</div>
								) : (
									filtered.map((c) => (
										<CardCharacterist
											key={c.id}
											id={c.id}
											displayId={c.display_id}
											title={c.title}
											description={c.description}
											searchQuery={searchQuery}
											isActive={c.id === activeFeatureId}
											onRefine={handleRefine}
										/>
									))
								)}
							</div>

							<FloatingPlan
								phase='features'
								navigateTo='/proyecto/caracteristicas/plan'
							/>
						</>
					)}
				</div>
			</div>

			<div
				className={`chatbot relative
						${
							activeFeatureId
								? 'opacity-100 translate-x-0 flex-4/12'
								: 'opacity-0 translate-x-8 pointer-events-none max-w-0 flex-none'
						}
				`}
			>
				<Chatbot
					placeholder='ej. mejorar característica de búsqueda'
					onClose={() => setActiveFeatureId(null)}
					messages={chatMessages}
					onSendMessage={handleSendChat}
					isLoading={isChatLoading}
					onPlanAction={handlePlanAction}
				/>
			</div>
		</div>
	);
};

export { CharacteristicsPage };
