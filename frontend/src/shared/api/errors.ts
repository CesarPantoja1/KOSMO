export interface ApiViolation {
	loc: Array<string | number>;
	msg: string;
	input?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

function toViolations(items: unknown): ApiViolation[] {
	if (!Array.isArray(items)) return [];
	return items
		.filter(isRecord)
		.map((item) => {
			const loc = (item as Record<string, unknown>).loc;
			const msg = (item as Record<string, unknown>).msg;
			return {
				loc: Array.isArray(loc) ? (loc as Array<string | number>) : [],
				msg: typeof msg === 'string' ? msg : '',
				input: (item as Record<string, unknown>).input,
			};
		})
		.filter((v) => v.msg !== '');
}

export class ApiError extends Error {
	readonly status: number;
	readonly type: string | null;
	readonly title: string | null;
	readonly detail: string | null;
	readonly traceId: string | null;
	readonly violations: ApiViolation[];
	readonly errorCode: string | null;
	readonly retryAfter: number | null;

	constructor({
		status,
		type = null,
		title = null,
		detail = null,
		traceId = null,
		violations = [],
		errorCode = null,
		retryAfter = null,
	}: {
		status: number;
		type?: string | null;
		title?: string | null;
		detail?: string | null;
		traceId?: string | null;
		violations?: ApiViolation[];
		errorCode?: string | null;
		retryAfter?: number | null;
	}) {
		super(title ?? detail ?? `Error del servidor (HTTP ${status})`);
		this.name = 'ApiError';
		this.status = status;
		this.type = type;
		this.title = title;
		this.detail = detail;
		this.traceId = traceId;
		this.violations = violations;
		this.errorCode = errorCode;
		this.retryAfter = retryAfter;
	}
}

export function parseApiError(res: Response, body: unknown): ApiError {
	const status = res.status;
	const retryAfterHeader = res.headers.get('Retry-After');
	const retryAfterFromHeader = retryAfterHeader ? parseInt(retryAfterHeader, 10) : null;
	const retryAfter = retryAfterFromHeader
		?? (isRecord(body) && typeof body.seconds_remaining === 'number' ? body.seconds_remaining : null);

	if (!isRecord(body)) return new ApiError({ status, retryAfter });

	// FastAPI 422: detail es una lista de violaciones
	if (Array.isArray(body.detail)) {
		const violations = toViolations(body.detail);
		return new ApiError({
			status,
			title: 'Datos inválidos',
			detail: violations.map((v) => v.msg).join('; ') || null,
			violations,
			retryAfter,
		});
	}

	// RFC 6749 §5.2 (flujo OAuth)
	if (typeof body.error === 'string') {
		return new ApiError({
			status,
			errorCode: body.error,
			detail: typeof body.error_description === 'string' ? body.error_description : null,
			retryAfter,
		});
	}

	// RFC 7807 Problem Detail
	return new ApiError({
		status,
		type: typeof body.type === 'string' ? body.type : null,
		title: typeof body.title === 'string' ? body.title : null,
		detail: typeof body.detail === 'string' ? body.detail : null,
		traceId: typeof body.trace_id === 'string' ? body.trace_id : null,
		violations: toViolations(body.violations),
		retryAfter,
	});
}

export function formatApiError(err: unknown, fallback: string): string {
	if (err instanceof ApiError) {
		const base = err.title ?? err.detail ?? err.message;
		return err.traceId ? `${base} (trace_id: ${err.traceId})` : base;
	}
	return err instanceof Error && err.message ? err.message : fallback;
}
