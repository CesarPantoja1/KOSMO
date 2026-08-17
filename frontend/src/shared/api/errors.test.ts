import { describe, expect, it } from 'vitest';
import { ApiError, formatApiError, parseApiError } from './errors';

function makeResponse(status: number): Response {
	return new Response(null, { status });
}

describe('parseApiError', () => {
	it('mapea un ProblemDetail RFC 7807 completo', () => {
		const error = parseApiError(makeResponse(409), {
			type: 'urn:kosmo:consistency:stale',
			title: 'Sugerencia obsoleta',
			status: 409,
			detail: 'La lógica de origen cambió. La sugerencia se re-evaluará automáticamente.',
			instance: '/api/v1/projects/prj_01/consistency',
			trace_id: '01KT05JRA7466PPYQXYTX',
		});

		expect(error).toBeInstanceOf(ApiError);
		expect(error.status).toBe(409);
		expect(error.type).toBe('urn:kosmo:consistency:stale');
		expect(error.title).toBe('Sugerencia obsoleta');
		expect(error.traceId).toBe('01KT05JRA7466PPYQXYTX');
		expect(error.detail).toContain('re-evaluará');
	});

	it('mapea violaciones 422 de FastAPI (detail como lista)', () => {
		const error = parseApiError(makeResponse(422), {
			detail: [
				{ loc: ['body', 'content'], msg: 'El mensaje no puede estar vacío.', type: 'value_error' },
			],
		});

		expect(error.title).toBe('Datos inválidos');
		expect(error.violations).toHaveLength(1);
		expect(error.violations[0].loc).toEqual(['body', 'content']);
	});

	it('mapea errores OAuth (RFC 6749)', () => {
		const error = parseApiError(makeResponse(401), {
			error: 'invalid_grant',
			error_description: 'Credenciales inválidas',
		});

		expect(error.errorCode).toBe('invalid_grant');
		expect(error.detail).toBe('Credenciales inválidas');
	});

	it('produce un error genérico sin body', () => {
		const error = parseApiError(makeResponse(500), null);

		expect(error.status).toBe(500);
		expect(error.title).toBeNull();
	});
});

describe('formatApiError', () => {
	it('incluye el trace_id en el mensaje', () => {
		const error = new ApiError({
			status: 409,
			title: 'Sugerencia obsoleta',
			traceId: 'trc_01',
		});

		expect(formatApiError(error, 'fallback')).toBe('Sugerencia obsoleta (trace_id: trc_01)');
	});

	it('usa el fallback para errores no ApiError', () => {
		expect(formatApiError(new Error('boom'), 'fallback')).toBe('boom');
		expect(formatApiError(null, 'fallback')).toBe('fallback');
	});
});
