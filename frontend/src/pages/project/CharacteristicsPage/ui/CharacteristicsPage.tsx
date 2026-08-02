'use client';

import {
	useCharacteristicStore,
	type CharacteristicChatResponse,
} from '@/entities/characteristic';
import {
	usePlanActions,
	usePlanStore,
} from '@/entities/plan';
import { Chatbot, FloatingPlan } from '@/feature';
import type { ChatMessage } from '@/feature/chatbot';
import { Ai, Loading, Plus, toast } from '@/shared/ui';
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
					title='Generando Características'
					description='La IA está analizando el descubrimiento para generar las características. Por favor, espera un momento.'
					messages={generatingCharacteristicMessages}
				/>
			)}

			<div className='page-container gap-2'>
				<div className='page-header'>
					<h2 className='text-base-800 text-3xl font-bold'>Características</h2>
					<p className='text-base-600 text-lg'>
						Gestiona y organiza las funciones principales de tu proyecto. Tienes el
						control total para editar, eliminar o añadir nuevas características según tus
						necesidades.
					</p>
					<div className='w-full inline-flex justify-between items-center gap-4'>
						{hasCharacteristics && (
							<Search value={searchQuery} onChange={setSearchQuery} />
						)}
						<div className='flex justify-end items-center gap-4'>
							{hasCharacteristics && (
								<Link
									href='caracteristicas/nueva'
									className='btn bg-primary-100 hover:bg-primary-100/90'
								>
									<Plus color='text-base-50' size={20} />
									<span className='text-center text-base-50'>Nueva Característica</span>
								</Link>
							)}

							{hasCharacteristics && (
								<Link
									href='requisitos'
									className='btn bg-primary-100 hover:bg-primary-100/90'
								>
									<div className='text-center text-base-50'>Ir a Requisitos</div>
									<ArrowRight color='text-base-50' size={20} />
								</Link>
							)}
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

						{!isLoading && !isGeneratingCharacteristics && !hasCharacteristics && (
							<div className='w-full my-auto min-h-105 flex flex-col items-center justify-center'>
								<div className='flex flex-col items-center gap-4 text-center px-6'>
									<Ai color='text-ai' size={70} />
									<h3 className='text-xl font-semibold text-base-800'>
										Sin Características generadas
									</h3>
									<p className='text-base-600 max-w-md'>
										Aún no se han generado las características de este proyecto. Haz clic
										en el botón para que la IA analice el descubrimiento y genere las
										características.
									</p>
									<button
										onClick={handleGenerateCharacteristics}
										disabled={isGeneratingCharacteristics}
										className='btn bg-ai text-base-50 hover:bg-ai/90 disabled:opacity-50'
									>
										<Ai size={20} color='text-base-50' />
										<span className='text-center'>Generar</span>
									</button>
								</div>
							</div>
						)}

						{!isLoading && hasCharacteristics && (
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
									contextId={activeFeatureId}
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
		</>
	);
};

export { CharacteristicsPage };
