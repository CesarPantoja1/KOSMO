import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/api', () => ({
	getRequirements: vi.fn(),
	saveRequirements: vi.fn(),
	generateRequirements: vi.fn(),
	deleteRequirements: vi.fn(),
	getRequirementChatHistory: vi.fn(),
	sendRequirementChatMessage: vi.fn(),
}));

import {
	getRequirements,
	saveRequirements,
	generateRequirements,
	deleteRequirements,
	getRequirementChatHistory,
	sendRequirementChatMessage,
} from '../api/api';
import { useRequirementsStore, clearRequirementsStore } from './store';

const api = {
	getRequirements: vi.mocked(getRequirements),
	saveRequirements: vi.mocked(saveRequirements),
	generateRequirements: vi.mocked(generateRequirements),
	deleteRequirements: vi.mocked(deleteRequirements),
	getRequirementChatHistory: vi.mocked(getRequirementChatHistory),
	sendRequirementChatMessage: vi.mocked(sendRequirementChatMessage),
};

describe('useRequirementsStore', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		clearRequirementsStore();
		useRequirementsStore.setState({ historyHasMore: false, historyCursor: null });
	});

	it('inicializa sin requisitos ni historiales', () => {
		const state = useRequirementsStore.getState();
		expect(state.currentRequirements).toEqual({});
		expect(state.hasRequirements).toEqual({});
		expect(state.chatHistories).toEqual({});
	});

	it('getRequirements guarda el contenido y marca hasRequirements=true', async () => {
		// Arrange
		api.getRequirements.mockResolvedValue({
			feature_id: 'f1',
			feature_number: 1,
			document_markdown: '## Doc',
			total: 1,
		});

		// Act
		const content = await useRequirementsStore.getState().getRequirements('prj_01', 'f1');

		// Assert
		expect(content).toBe('## Doc');
		expect(useRequirementsStore.getState().currentRequirements['f1']).toBe('## Doc');
		expect(useRequirementsStore.getState().hasRequirements['f1']).toBe(true);
	});

	it('getRequirements no marca hasRequirements cuando el contenido está vacío', async () => {
		// Arrange
		api.getRequirements.mockResolvedValue({
			feature_id: 'f1',
			feature_number: 1,
			document_markdown: '',
			total: 0,
		});

		// Act
		await useRequirementsStore.getState().getRequirements('prj_01', 'f1');

		// Assert
		expect(useRequirementsStore.getState().hasRequirements['f1']).toBeUndefined();
	});

	it('saveRequirements guarda el contenido enviado', async () => {
		// Arrange
		api.saveRequirements.mockResolvedValue(undefined);

		// Act
		await useRequirementsStore.getState().saveRequirements('prj_01', 'f1', 'guardado');

		// Assert
		expect(useRequirementsStore.getState().currentRequirements['f1']).toBe('guardado');
		expect(useRequirementsStore.getState().hasRequirements['f1']).toBe(true);
	});

	it('generateRequirements guarda el documento generado', async () => {
		// Arrange
		api.generateRequirements.mockResolvedValue({
			feature_id: 'f1',
			feature_number: 1,
			document_markdown: '## Generado',
			total: 4,
		});

		// Act
		const content = await useRequirementsStore.getState().generateRequirements('prj_01', 'f1');

		// Assert
		expect(content).toBe('## Generado');
		expect(useRequirementsStore.getState().currentRequirements['f1']).toBe('## Generado');
	});

	it('deleteRequirements limpia el contenido, flag e historial del feature', async () => {
		// Arrange
		useRequirementsStore.getState().setCurrentRequirements('f1', 'algo');
		useRequirementsStore.getState().setHasRequirements('f1', true);
		useRequirementsStore.getState().appendUserMessage('f1', 'mensaje');
		api.deleteRequirements.mockResolvedValue(undefined);

		// Act
		await useRequirementsStore.getState().deleteRequirements('prj_01', 'f1');

		// Assert
		const state = useRequirementsStore.getState();
		expect(state.currentRequirements['f1']).toBeUndefined();
		expect(state.hasRequirements['f1']).toBeUndefined();
		expect(state.chatHistories['f1']).toBeUndefined();
	});

	it('setHasRequirements y resetRequirements funcionan correctamente', () => {
		// Act
		useRequirementsStore.getState().setHasRequirements('f1', true);
		expect(useRequirementsStore.getState().hasRequirements['f1']).toBe(true);

		useRequirementsStore.getState().resetRequirements();

		// Assert
		expect(useRequirementsStore.getState().hasRequirements).toEqual({});
		expect(useRequirementsStore.getState().currentRequirements).toEqual({});
	});

	it('loadChatHistory reemplaza el historial y guarda cursor/hasMore', async () => {
		// Arrange
		api.getRequirementChatHistory.mockResolvedValue({
			phase: 'requirements',
			context: 'f1',
			messages: [{ id: 'm1', role: 'user', content: 'a' } as never],
			has_more: true,
			next_cursor: 'cur_1',
		});

		// Act
		const messages = await useRequirementsStore.getState().loadChatHistory('f1');

		// Assert
		expect(messages).toHaveLength(1);
		expect(useRequirementsStore.getState().historyHasMore).toBe(true);
		expect(useRequirementsStore.getState().historyCursor).toBe('cur_1');
	});

	it('loadOlderChatHistory no hace nada si no hay historyCursor', async () => {
		// Act
		await useRequirementsStore.getState().loadOlderChatHistory('f1');

		// Assert
		expect(api.getRequirementChatHistory).not.toHaveBeenCalled();
	});

	it('loadOlderChatHistory antepone mensajes más antiguos', async () => {
		// Arrange
		api.getRequirementChatHistory
			.mockResolvedValueOnce({
				phase: 'requirements',
				context: 'f1',
				messages: [{ id: 'recent', role: 'user', content: 'reciente' } as never],
				has_more: true,
				next_cursor: 'cur_1',
			})
			.mockResolvedValueOnce({
				phase: 'requirements',
				context: 'f1',
				messages: [{ id: 'old', role: 'user', content: 'antiguo' } as never],
				has_more: false,
				next_cursor: null,
			});
		await useRequirementsStore.getState().loadChatHistory('f1');

		// Act
		await useRequirementsStore.getState().loadOlderChatHistory('f1');

		// Assert
		const history = useRequirementsStore.getState().chatHistories['f1'];
		expect(history[0].id).toBe('old');
		expect(history[1].id).toBe('recent');
	});

	it('sendChatMessage agrega el mensaje del usuario y luego la respuesta', async () => {
		// Arrange
		api.sendRequirementChatMessage.mockResolvedValue({
			message: { id: 'm1', role: 'assistant', content: 'Respuesta' } as never,
			modification: null,
			redirect: null,
			consistency: null,
		});

		// Act
		await useRequirementsStore.getState().sendChatMessage('f1', 'Hola');

		// Assert
		const history = useRequirementsStore.getState().chatHistories['f1'];
		expect(history).toHaveLength(2);
		expect(history[0].role).toBe('user');
		expect(history[1].content).toBe('Respuesta');
	});

	it('sendChatMessage agrega un mensaje de error de formato inválido y relanza el error', async () => {
		// Arrange
		api.sendRequirementChatMessage.mockRejectedValue(
			new Error('Respuesta del agente en formato inválido'),
		);

		// Act & Assert
		await expect(
			useRequirementsStore.getState().sendChatMessage('f1', 'Hola'),
		).rejects.toThrow('formato inválido');

		const history = useRequirementsStore.getState().chatHistories['f1'];
		expect(history).toHaveLength(2);
		expect(history[1].content).toContain('formato inválido');
	});

	it('sendChatMessage agrega un mensaje de error genérico para otros errores', async () => {
		// Arrange
		api.sendRequirementChatMessage.mockRejectedValue(new Error('network down'));

		// Act & Assert
		await expect(
			useRequirementsStore.getState().sendChatMessage('f1', 'Hola'),
		).rejects.toThrow('network down');

		const history = useRequirementsStore.getState().chatHistories['f1'];
		expect(history[1].content).toContain('Ocurrió un error al procesar tu solicitud');
	});

	it('appendUserMessage y appendAssistantMessage agregan mensajes locales', () => {
		// Act
		useRequirementsStore.getState().appendUserMessage('f1', 'Pregunta');
		useRequirementsStore.getState().appendAssistantMessage('f1', {
			id: 'm2',
			role: 'assistant',
			content: 'Respuesta local',
		} as never);

		// Assert
		const history = useRequirementsStore.getState().chatHistories['f1'];
		expect(history).toHaveLength(2);
	});

	it('clearChatHistory vacía el historial de un feature', () => {
		// Arrange
		useRequirementsStore.getState().appendUserMessage('f1', 'msg');

		// Act
		useRequirementsStore.getState().clearChatHistory('f1');

		// Assert
		expect(useRequirementsStore.getState().chatHistories['f1']).toEqual([]);
	});

	it('clearRequirementsStore limpia el storage persistido y el estado', () => {
		// Arrange
		useRequirementsStore.getState().setCurrentRequirements('f1', 'algo');

		// Act
		clearRequirementsStore();

		// Assert
		expect(useRequirementsStore.getState().currentRequirements).toEqual({});
	});
});
