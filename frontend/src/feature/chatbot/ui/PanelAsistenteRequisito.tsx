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
	/** ID del requisito seleccionado actualmente (contexto activo) */
	requirementId: string | null;
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

export const PanelAsistenteRequisito = ({
	requirementId,
	onClose,
	onPlanAction,
	title = 'Asistente de Requisitos EARS',
	subtitle = 'Refinamiento y criterios de aceptación Gherkin',
	placeholder = 'Ej., Agregar escenarios alternativos en formato Gherkin...',
}: PanelAsistenteRequisitoProps) => {
	const [isLoading, setIsLoading] = useState(false);

	const chatHistories = useRequirementsStore((s) => s.chatHistories);
	const loadChatHistory = useRequirementsStore((s) => s.loadChatHistory);
	const sendChatMessage = useRequirementsStore((s) => s.sendChatMessage);

	// T5: Limpieza y recarga del historial al cambiar de requisito seleccionado
	useEffect(() => {
		if (!requirementId) return;

		let isMounted = true;

		const fetchHistory = async () => {
			setIsLoading(true);
			try {
				await loadChatHistory(requirementId);
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
	}, [requirementId, loadChatHistory]);

	// T5: Manejo del envío de mensajes y captura de errores de formato del agente
	const handleSendMessage = async (content: string) => {
		if (!requirementId) return;

		setIsLoading(true);
		try {
			await sendChatMessage(requirementId, content);
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

	const messages: ChatMessage[] = requirementId
		? (chatHistories[requirementId] ?? []).map(toChatMessage)
		: [];

	return (
		<Chatbot
			title={title}
			subtitle={subtitle}
			greeting='Hola 👋. Soy tu asistente de Requisitos EARS. Puedo ayudarte a refinar los requisitos y generar sus criterios de aceptación en formato Gherkin (Dado-Cuando-Entonces).'
			placeholder={placeholder}
			onClose={onClose}
			messages={messages}
			onSendMessage={handleSendMessage}
			isLoading={isLoading}
			onPlanAction={onPlanAction}
		/>
	);
};
