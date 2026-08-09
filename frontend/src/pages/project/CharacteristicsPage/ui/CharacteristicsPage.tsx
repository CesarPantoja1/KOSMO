'use client';

import {
	useCharacteristicStore,
	deleteFeature,
	type CharacteristicChatResponse,
} from '@/entities/characteristic';
import { usePlanActions, usePlanStore } from '@/entities/plan';
import { Chatbot, FloatingPlan } from '@/feature';
import type { ChatMessage } from '@/feature/chatbot';
import { Ai, Loading, ModalConfirmLeave, Plus, toast } from '@/shared/ui';
import ArrowRight from '@/shared/ui/icons/ArrowRight';
import { useAppStore } from 'app/store/app.store';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useCharacteristicsPage } from '../hooks/use-characteristics-page';
import CardCharacterist from './CardCharacterist';
import Search from './Search';

const generatingCharacteristicMessages = [
	'Analizando descubrimiento del proyecto...',
	'Generando características del proyecto...',
	'Finalizando generación de características...',
];

function toChatMessage(r: CharacteristicChatResponse): ChatMessage {
	return {
		id: r.id,
		role: r.role,
		content: r.content,
		created_at: r.created_at,
		change_suggestions: r.change_suggestions ?? undefined,
	};
}

const CharacteristicsPage = () => {
	const { isLoading, hasCharacteristics, searchQuery, setSearchQuery, filtered } =
		useCharacteristicsPage();

	const [activeFeatureId, setActiveFeatureId] = useState<string | null>(null);
	const [isChatLoading, setIsChatLoading] = useState(false);
	const [isGeneratingCharacteristics, setIsGeneratingCharacteristics] = useState(false);
	const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

	const currentProject = useAppStore((s) => s.currentProject);

	const chatHistories = useCharacteristicStore((s) => s.chatHistories);
	const sendChatMessage = useCharacteristicStore((s) => s.sendChatMessage);
	const generateCharacteristics = useCharacteristicStore(
		(s) => s.generateCharacteristics,
	);

	const fetchAndHydratePlan = usePlanStore((s) => s.fetchAndHydratePlan);

	useEffect(() => {
		if (currentProject) {
			fetchAndHydratePlan(currentProject.id, 'features');
		}
	}, [currentProject, fetchAndHydratePlan]);

	const handleRefine = (featureId: string) => {
		setActiveFeatureId(featureId);
	};

	const handleDelete = async () => {
		if (!currentProject || !confirmDeleteId) return;

		const featureId = confirmDeleteId;
		setConfirmDeleteId(null);

		const toastId = toast.info('Eliminando...');
		try {
			await deleteFeature(currentProject.id, featureId);
			useCharacteristicStore.setState((state) => ({
				currentCharacteristics: state.currentCharacteristics.filter(
					(c) => c.id !== featureId,
				),
			}));
			if (activeFeatureId === featureId) setActiveFeatureId(null);
			toast.close(toastId);
			toast.success('Característica eliminada');
		} catch (err) {
			toast.close(toastId);
			const message =
				err instanceof Error ? err.message : 'Error al eliminar la característica';
			toast.error(message);
		}
	};

	const handleGenerateCharacteristics = async () => {
		if (!currentProject) return;

		setIsGeneratingCharacteristics(true);
		try {
			await generateCharacteristics(currentProject.id);
			fetchAndHydratePlan(currentProject.id, 'features');
			toast.success('Características generadas exitosamente');
		} catch (err) {
			const message =
				err instanceof Error ? err.message : 'Error al generar las características';
			toast.error(message);
		} finally {
			setIsGeneratingCharacteristics(false);
		}
	};

	const handleSendChat = async (content: string) => {
		if (!activeFeatureId) return;
		setIsChatLoading(true);
		try {
			await sendChatMessage(activeFeatureId, content);
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : 'Error al enviar el mensaje.';
			toast.error(errorMessage);
		} finally {
			setIsChatLoading(false);
		}
	};

	const handlePlanAction = usePlanActions(
		currentProject?.id ?? null,
		'features',
		activeFeatureId,
	);

	const chatMessages: ChatMessage[] = (chatHistories[activeFeatureId!] ?? []).map(
		toChatMessage,
	);

	return (
		<>
			{isGeneratingCharacteristics && (
				<Loading
					title='Generando funcionalidades'
					description='El asistente está analizando el descubrimiento del proyecto para identificar sus funcionalidades principales.'
					messages={generatingCharacteristicMessages}
				/>
			)}

			<div className='page-container gap-2'>
				<div className='page-header'>
					{/* Header row */}
					<div className='flex flex-col gap-4'>
						<div className='flex flex-row justify-between items-start gap-4'>
							<div className='flex flex-col gap-1'>
								<h2 className='text-neutral-800 text-3xl font-bold'>Funcionalidades</h2>
								<p className='text-neutral-500 text-base'>
									Gestiona y organiza las funciones principales de tu proyecto.
								</p>
							</div>
							{hasCharacteristics && (
								<div className='flex items-center justify-end gap-3 flex-wrap'>
									<Link href='caracteristicas/nueva' className='btn btn-primary'>
										<Plus color='' size={18} />
										Nueva funcionalidad
									</Link>
									<Link href='requisitos' className='btn btn-primary'>
										Continuar
										<ArrowRight color='' size={18} />
									</Link>
								</div>
							)}
						</div>

						{hasCharacteristics && (
							<div className='w-full'>
								<Search value={searchQuery} onChange={setSearchQuery} />
							</div>
						)}
					</div>

					{/* Content area */}
					<div className='relative flex-1 flex flex-col min-h-0 overflow-y-auto'>
						{/* Skeleton */}
						{isLoading && (
							<div className='flex flex-col gap-3 pb-4'>
								{[1, 2, 3, 4, 5].map((i) => (
									<div
										key={i}
										className='border border-neutral-200 rounded-lg m-0.5 px-6 py-4 inline-flex items-center gap-6 animate-pulse bg-neutral-0'
									>
										<div className='w-12 h-8 bg-neutral-200 rounded-md' />
										<div className='flex-1 flex flex-col gap-2.5'>
											<div className='h-5 bg-neutral-200 rounded-md w-3/4' />
											<div className='h-4 bg-neutral-200 rounded-md w-full' />
										</div>
									</div>
								))}
							</div>
						)}

						{/* Empty state */}
						{!isLoading && !isGeneratingCharacteristics && !hasCharacteristics && (
							<div className='w-full my-auto min-h-105 flex flex-col items-center justify-center'>
								<div className='flex flex-col items-center gap-5 text-center px-6 max-w-lg'>
									<div className='flex h-20 w-20 items-center justify-center rounded-2xl bg-ai-50'>
										<Ai color='text-ai-500' size={48} />
									</div>
									<div className='flex flex-col gap-2'>
										<h3 className='text-xl font-semibold text-neutral-800'>
											Aún no hay funcionalidades definidas
										</h3>
										<p className='text-neutral-500 text-base'>
											El asistente analizará el descubrimiento del proyecto y generará las
											funcionalidades principales de tu aplicación.
										</p>
									</div>
									<button
										onClick={handleGenerateCharacteristics}
										disabled={isGeneratingCharacteristics}
										className='btn btn-ai'
									>
										<Ai size={18} color='' />
										Generar funcionalidades
									</button>
								</div>
							</div>
						)}

						{/* List */}
						{!isLoading && hasCharacteristics && (
							<>
								<div className='flex flex-col gap-2 pb-4'>
									{filtered.length === 0 && searchQuery.trim() ? (
										<div className='border border-neutral-200 rounded-lg m-0.5 px-8 py-16 flex flex-col justify-center items-center gap-3 bg-neutral-0'>
											<p className='text-neutral-500 text-base font-medium text-center'>
												No se encontraron funcionalidades que coincidan con la búsqueda
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
												onDelete={setConfirmDeleteId}
											/>
										))
									)}
								</div>

								<FloatingPlan
									phase='features'
									navigateTo='/proyecto/caracteristicas/plan'
									contextId={activeFeatureId}
								/>
							</>
						)}
					</div>
				</div>

				{/* Chatbot panel */}
				<div
					className={`chatbot relative ${
						activeFeatureId
							? 'opacity-100 translate-x-0 w-96 shrink-0'
							: 'opacity-0 translate-x-8 pointer-events-none max-w-0 flex-none'
					}`}
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

			{confirmDeleteId && (
				<ModalConfirmLeave
					title='Eliminar funcionalidad'
					description='¿Estás seguro de eliminar esta funcionalidad? Esta acción no se puede deshacer.'
					cancelText='Cancelar'
					confirmText='Eliminar'
					onCancel={() => setConfirmDeleteId(null)}
					onConfirm={handleDelete}
				/>
			)}
		</>
	);
};

export { CharacteristicsPage };
