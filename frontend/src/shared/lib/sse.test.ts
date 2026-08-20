import { describe, expect, it, vi } from 'vitest';
import { consumeSse } from './sse';

function sseResponse(payload: string): Response {
	const encoder = new TextEncoder();
	const stream = new ReadableStream<Uint8Array>({
		start(controller) {
			controller.enqueue(encoder.encode(payload));
			controller.close();
		},
	});
	return new Response(stream, {
		headers: { 'Content-Type': 'text/event-stream' },
	});
}

function sseResponseInPieces(payload: string, pieceSize: number): Response {
	const encoder = new TextEncoder();
	const stream = new ReadableStream<Uint8Array>({
		start(controller) {
			for (let i = 0; i < payload.length; i += pieceSize) {
				controller.enqueue(encoder.encode(payload.slice(i, i + pieceSize)));
			}
			controller.close();
		},
	});
	return new Response(stream, {
		headers: { 'Content-Type': 'text/event-stream' },
	});
}

const fixtureStart = { type: 'start' };
const fixtureChunk = { type: 'chunk', content: 'Hola, ' };
const fixtureMessage = {
	type: 'message',
	id: 'msg_01',
	role: 'assistant',
	content: 'Cambio aplicado.',
	suggestions: [
		{
			id: 'chg_01',
			section: 'título',
			description: 'Renombrar',
			diff_before: 'Antes',
			diff_after: 'Después',
			rationale: 'Claridad',
			applied: true,
			not_applied_reason: null,
		},
	],
	modification: {
		applied: true,
		modified_section: 'título',
		change_description: 'Se aplicaron los cambios sugeridos.',
		modified_document: null,
		before: null,
		after: null,
		undo_version_id: null,
		clarification_message: null,
	},
	consistency: null,
	timestamp: '2026-08-14T12:00:00Z',
};

describe('consumeSse', () => {
	it('despacha los eventos del backend en orden', async () => {
		const onEvent = vi.fn();
		const payload = [fixtureStart, fixtureChunk, fixtureMessage]
			.map((e) => `data: ${JSON.stringify(e)}\n\n`)
			.join('');

		await consumeSse(sseResponse(payload), onEvent);

		expect(onEvent).toHaveBeenCalledTimes(3);
		expect(onEvent.mock.calls[0][0]).toEqual(fixtureStart);
		expect(onEvent.mock.calls[1][0]).toEqual(fixtureChunk);
		expect(onEvent.mock.calls[2][0]).toEqual(fixtureMessage);
	});

	it('reconstruye eventos partidos entre chunks de red', async () => {
		const onEvent = vi.fn();
		const payload = [fixtureStart, fixtureChunk, fixtureMessage]
			.map((e) => `data: ${JSON.stringify(e)}\n\n`)
			.join('');

		await consumeSse(sseResponseInPieces(payload, 7), onEvent);

		expect(onEvent).toHaveBeenCalledTimes(3);
		expect(onEvent.mock.calls[2][0]).toEqual(fixtureMessage);
	});

	it('ignora líneas malformadas', async () => {
		const onEvent = vi.fn();
		const payload = `data: {no-json}\n\ndata: ${JSON.stringify(fixtureStart)}\n\n`;

		await consumeSse(sseResponse(payload), onEvent);

		expect(onEvent).toHaveBeenCalledTimes(1);
		expect(onEvent.mock.calls[0][0]).toEqual(fixtureStart);
	});

	it('despacha el último evento sin separador final', async () => {
		const onEvent = vi.fn();
		const payload = `data: ${JSON.stringify(fixtureChunk)}`;

		await consumeSse(sseResponse(payload), onEvent);

		expect(onEvent).toHaveBeenCalledTimes(1);
		expect(onEvent.mock.calls[0][0]).toEqual(fixtureChunk);
	});

	it('propaga los errores lanzados por el manejador onEvent', async () => {
		const onEvent = vi.fn().mockImplementation(() => {
			throw new Error('Error en procesamiento SSE');
		});
		const payload = `data: ${JSON.stringify(fixtureStart)}\n\n`;

		await expect(consumeSse(sseResponse(payload), onEvent)).rejects.toThrow(
			'Error en procesamiento SSE',
		);
	});

	it('procesa eventos con delimitadores CRLF (\\r\\n\\r\\n) generados por FastAPI/sse_starlette', async () => {
		const onEvent = vi.fn();
		const payload = [fixtureStart, fixtureChunk, fixtureMessage]
			.map((e) => `event: custom\r\ndata: ${JSON.stringify(e)}\r\n\r\n`)
			.join('');

		await consumeSse(sseResponse(payload), onEvent);

		expect(onEvent).toHaveBeenCalledTimes(3);
		expect(onEvent.mock.calls[0][0]).toEqual(fixtureStart);
		expect(onEvent.mock.calls[1][0]).toEqual(fixtureChunk);
		expect(onEvent.mock.calls[2][0]).toEqual(fixtureMessage);
	});
});

