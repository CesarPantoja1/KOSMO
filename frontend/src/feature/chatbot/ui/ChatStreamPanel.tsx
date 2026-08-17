'use client';

import { useEffect, useRef, useState } from 'react';
import type { ChatMessage, ChatPhase } from '@/entities/chat';
import { useChatSessions, useChatSessionsStore } from '@/entities/chat';
import { ApiError, formatApiError } from '@/shared/api';
import { useChatStream } from '../hooks/useChatStream';
import { Chatbot } from './Chatbot';
import { SessionSelector } from './SessionSelector';

interface ChatStreamPanelProps {
	title?: string;
	subtitle?: string;
	greeting?: string;
	placeholder?: string;
	onClose?: () => void;
	messages: ChatMessage[];
	streamUrl: string | null;
	isLoading?: boolean;
	projectId?: string | null;
	phase?: ChatPhase | null;
	contextId?: string | null;
	onLoadHistory?: (sessionId: string | null) => Promise<void> | void;
	hasMore?: boolean;
	loadingMore?: boolean;
	onLoadMore?: (sessionId: string | null) => void;
	onUserMessage: (content: string) => void;
	onMessage: (message: ChatMessage) => void;
	onRedirect?: (message: string) => void;
	onError?: (error: unknown) => void;
}

export const ChatStreamPanel = ({
	title,
	subtitle,
	greeting,
	placeholder,
	onClose,
	messages,
	streamUrl,
	isLoading = false,
	projectId = null,
	phase = null,
	contextId = null,
	onLoadHistory,
	hasMore = false,
	loadingMore = false,
	onLoadMore,
	onUserMessage,
	onMessage,
	onRedirect,
	onError,
}: ChatStreamPanelProps) => {
	const [streamingContent, setStreamingContent] = useState<string | null>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);
	const lastContentRef = useRef<string | null>(null);

	const onMessageRef = useRef(onMessage);
	useEffect(() => {
		onMessageRef.current = onMessage;
	}, [onMessage]);

	const onRedirectRef = useRef(onRedirect);
	useEffect(() => {
		onRedirectRef.current = onRedirect;
	}, [onRedirect]);

	const onErrorRef = useRef(onError);
	useEffect(() => {
		onErrorRef.current = onError;
	}, [onError]);

	const onLoadHistoryRef = useRef(onLoadHistory);
	useEffect(() => {
		onLoadHistoryRef.current = onLoadHistory;
	}, [onLoadHistory]);

	const onLoadMoreRef = useRef(onLoadMore);
	useEffect(() => {
		onLoadMoreRef.current = onLoadMore;
	}, [onLoadMore]);

	const { phase: streamPhase, send, stop } = useChatStream({
		onChunk: (content) => setStreamingContent((prev) => (prev ?? '') + content),
		onMessage: (message) => {
			setStreamingContent(null);
			onMessageRef.current(message);
			// Re-lista las sesiones para refrescar el título derivado del primer prompt
			if (projectId && phase) {
				void useChatSessionsStore
					.getState()
					.listSessions(projectId, phase, contextId)
					.catch(() => undefined);
			}
		},
		onError: (err) => {
			setStreamingContent(null);
			const text = formatApiError(err, 'Error al enviar el mensaje.');
			// El endpoint de stream devuelve 400 cuando el cambio pertenece a otra fase
			if (err instanceof ApiError && err.status === 400) {
				onRedirectRef.current?.(err.detail ?? text);
			} else {
				setErrorMessage(text);
				onErrorRef.current?.(err);
			}
		},
	});

	const chatSessions = useChatSessions(projectId, phase, contextId);

	// Rehidrata el historial al cambiar de sesión o de contexto
	useEffect(() => {
		if (!projectId || !phase) return;
		const timer = window.setTimeout(() => {
			void onLoadHistoryRef.current?.(chatSessions.activeSessionId);
		}, 0);
		return () => window.clearTimeout(timer);
	}, [projectId, phase, contextId, chatSessions.activeSessionId]);

	const handleSend = (content: string) => {
		if (!streamUrl) return;
		lastContentRef.current = content;
		setErrorMessage(null);
		setStreamingContent('');
		onUserMessage(content);
		send(streamUrl, { content, session_id: chatSessions.activeSessionId });
	};

	const handleRetry = () => {
		const last = lastContentRef.current;
		if (!last || !streamUrl) return;
		setErrorMessage(null);
		setStreamingContent('');
		send(streamUrl, { content: last, session_id: chatSessions.activeSessionId });
	};

	const isStreaming = streamPhase === 'connecting' || streamPhase === 'streaming';

	const handleCreateSession = () => {
		void chatSessions.createNewSession().catch((err) => {
			setErrorMessage(formatApiError(err, 'No se pudo crear el chat.'));
		});
	};

	const handleDeleteSession = (sessionId: string) => {
		void chatSessions.deleteSession(sessionId).catch((err) => {
			setErrorMessage(formatApiError(err, 'No se pudo eliminar el chat.'));
		});
	};

	return (
		<Chatbot
			title={title}
			subtitle={subtitle}
			greeting={greeting}
			placeholder={placeholder}
			onClose={onClose}
			messages={messages}
			onSendMessage={handleSend}
			isLoading={isLoading || chatSessions.loading}
			streamingContent={streamingContent}
			isStreaming={isStreaming}
			onStop={stop}
			errorMessage={errorMessage}
			onRetry={handleRetry}
			hasMore={hasMore}
			loadingMore={loadingMore}
			onLoadMore={() => onLoadMoreRef.current?.(chatSessions.activeSessionId)}
			sessionSelector={
				projectId && phase ? (
					<SessionSelector
						sessions={chatSessions.sessions}
						activeSessionId={chatSessions.activeSessionId}
						loading={chatSessions.loading}
						onSelect={chatSessions.selectSession}
						onCreate={handleCreateSession}
						onDelete={handleDeleteSession}
					/>
				) : null
			}
		/>
	);
};
