import { describe, expect, it } from 'vitest';
import { appendMessage, createAssistantError, createUserMessage } from './chat-message';

describe('createUserMessage', () => {
	it('crea un mensaje de usuario con el contenido dado', () => {
		// Act
		const message = createUserMessage('Hola mundo');

		// Assert
		expect(message.role).toBe('user');
		expect(message.content).toBe('Hola mundo');
		expect(message.change_suggestions).toBeNull();
		expect(message.modification).toBeNull();
		expect(message.id).toBeTruthy();
	});
});

describe('createAssistantError', () => {
	it('crea un mensaje de asistente con el contenido de error dado', () => {
		// Act
		const message = createAssistantError('Ocurrió un error');

		// Assert
		expect(message.role).toBe('assistant');
		expect(message.content).toBe('Ocurrió un error');
	});
});

describe('appendMessage', () => {
	it('agrega el mensaje al final sin mutar el arreglo original', () => {
		// Arrange
		const original = [createUserMessage('primero')];

		// Act
		const result = appendMessage(original, createUserMessage('segundo'));

		// Assert
		expect(result).toHaveLength(2);
		expect(original).toHaveLength(1);
		expect(result[1].content).toBe('segundo');
	});
});
