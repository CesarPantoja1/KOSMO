'use client';

import {
	useRequirementsStore,
	type RequirementChatResponse,
} from '@/entities/requirements';
import { toast } from '@/shared/ui';
import { useEffect, useState } from 'react';
import type { ChangeSuggestion, ChatMessage } from '../types/chatbot';
import { Chatbot } from './Chatbot';

interface PanelAsistenteRequisitoProps {
	/** ID de la característica para el chat (contexto activo) */
	featureId: string | null;
	/** Callback para cerrar el panel */
	onClose?: () => void;
	/** Callback para cuando el usuario interactúa con una sugerencia del plan */
	onPlanAction?: (
		action: 'add' | 'remove' | 'discard',
		suggestion: ChangeSuggestion,
		messageId: string,
	) => void;
	title?: string;
	subtitle?: string;
	placeholder?: string;
}

/**
 * Adapta la respuesta del backend de requisitos al tipo genérico de mensaje de Chatbot UI
 */
function toChatMessage(r: RequirementChatResponse): ChatMessage {
	return {
		id: r.id,
		role: r.role,
		content: r.content,
		created_at: r.created_at,
		change_suggestions: r.change_suggestions ?? undefined,
	};
}

export const PanelAsistenteRequisito = ({
	featureId,
	onClose,
	onPlanAction,
	title = 'Asistente de Requisitos EARS',
	subtitle = 'Refinamiento y criterios de aceptación',
	placeholder = 'Ej., Agregar escenarios alternativos...',
}: PanelAsistenteRequisitoProps) => {
	const [isLoading, setIsLoading] = useState(false);

	const chatHistories = useRequirementsStore((s) => s.chatHistories);
	const loadChatHistory = useRequirementsStore((s) => s.loadChatHistory);
	const sendChatMessage = useRequirementsStore((s) => s.sendChatMessage);

	// T5: Limpieza y recarga del historial al cambiar de requisito seleccionado
	useEffect(() => {
		if (!featureId) return;

		let isMounted = true;

		const fetchHistory = async () => {
			const hasHistory = Boolean(useRequirementsStore.getState().chatHistories[featureId]);
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
			await sendChatMessage(featureId, content);
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

	const raw = featureId ? (chatHistories[featureId] ?? []) : [];
	const messages: ChatMessage[] = Array.isArray(raw) ? raw.map(toChatMessage) : [];

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
			onPlanAction={onPlanAction}
		/>
	);
};
