// Utilidades puras de mensaje: viven en `shared` (ver shared/model/chat-message.ts)
// y se re-exportan aquí para mantener compatibilidad con los consumidores de esta entidad.
export {
	createUserMessage,
	createAssistantError,
	appendMessage,
} from '@/shared/model/chat-message';
