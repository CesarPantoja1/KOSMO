'use client';

import { useRequirementsStore } from '@/entities/requirements';
import { toast } from '@/shared/ui';
import { useEffect, useState } from 'react';
import { Chatbot } from './Chatbot';

interface PanelAsistenteRequisitoProps {
	featureId: string | null;
	projectId?: string | null;
	onClose?: () => void;
	title?: string;
	subtitle?: string;
	placeholder?: string;
}

export const PanelAsistenteRequisito = ({
	featureId,
	projectId,
	onClose,
	title = 'Asistente de Requisitos EARS',
	subtitle = 'Refinamiento y criterios de aceptación',
	placeholder = 'Ej., Agregar escenarios alternativos...',
}: PanelAsistenteRequisitoProps) => {
	const [isLoading, setIsLoading] = useState(false);

	const chatHistories = useRequirementsStore((s) => s.chatHistories);
	const loadChatHistory = useRequirementsStore((s) => s.loadChatHistory);
	const sendChatMessage = useRequirementsStore((s) => s.sendChatMessage);
	const getRequirements = useRequirementsStore((s) => s.getRequirements);

	// T5: Limpieza y recarga del historial al cambiar de requisito seleccionado
	useEffect(() => {
		if (!featureId) return;

		let isMounted = true;

		const fetchHistory = async () => {
			const hasHistory = Boolean(
				useRequirementsStore.getState().chatHistories[featureId],
			);
			if (!hasHistory) {
				setIsLoading(true);
			}
			try {
				await loadChatHistory(featureId);
			} catch (err) {
				console.warn('[PanelAsistenteRequisito] Error al cargar historial:', err);
			} finally {
				if (isMounted) {
					setIsLoading(false);
				}
			}
		};

		fetchHistory();

		return () => {
			isMounted = false;
		};
	}, [featureId, loadChatHistory]);

	// T5: Manejo del envío de mensajes y captura de errores de formato del agente
	const handleSendMessage = async (content: string) => {
		if (!featureId) return;

		setIsLoading(true);
		try {
			const response = await sendChatMessage(featureId, content);
			if (response.modification && projectId && featureId) {
				await getRequirements(projectId, featureId);
			}
		} catch (err) {
			const message = err instanceof Error ? err.message : '';
			if (message.includes('inválido') || message.includes('format')) {
				toast.error(
					'El agente devolvió una respuesta con formato inválido. Por favor reformula tu mensaje.',
				);
			} else {
				toast.error('Error al enviar el mensaje al asistente de requisitos.');
			}
		} finally {
			setIsLoading(false);
		}
	};

	const messages = featureId ? (chatHistories[featureId] ?? []) : [];

	return (
		<Chatbot
			key={featureId || 'empty'}
			title={title}
			subtitle={subtitle}
			greeting='Hola 👋. Soy tu asistente de Requisitos EARS. Puedo ayudarte a refinar los requisitos y generar sus criterios de aceptación (Dado-Cuando-Entonces).'
			placeholder={placeholder}
			onClose={onClose}
			messages={messages}
			onSendMessage={handleSendMessage}
			isLoading={isLoading}
		/>
	);
};
