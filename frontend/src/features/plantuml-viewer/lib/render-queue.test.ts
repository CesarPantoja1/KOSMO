import { afterEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => {
	const renderToString = vi.fn();
	return {
		renderToString,
		loadViz: vi.fn(async () => undefined),
		loadPlantUmlModule: vi.fn(async () => ({ renderToString })),
	};
});

vi.mock('./engine-loader', () => ({
	loadViz: mocks.loadViz,
	loadPlantUmlModule: mocks.loadPlantUmlModule,
}));

import { renderPlantUml } from './render-queue';

describe('renderPlantUml', () => {
	afterEach(() => {
		vi.useRealTimers();
		mocks.renderToString.mockReset();
	});

	it('serializa renders y continúa tras un timeout', async () => {
		vi.useFakeTimers();

		let secondResolve: ((svg: string) => void) | null = null;
		let callCount = 0;
		mocks.renderToString.mockImplementation((_lines: string[], ok: (s: string) => void) => {
			callCount += 1;
			if (callCount === 1) return; // el primer render cuelga
			secondResolve = ok;
		});

		const p1 = renderPlantUml('diagrama_uno');
		const p2 = renderPlantUml('diagrama_dos');

		await vi.advanceTimersByTimeAsync(0);
		expect(mocks.renderToString).toHaveBeenCalledTimes(1);

		await vi.advanceTimersByTimeAsync(20000);

		const r1 = await p1;
		expect(r1.ok).toBe(false);

		expect(mocks.renderToString).toHaveBeenCalledTimes(2);
		secondResolve?.('<svg>dos</svg>');

		const r2 = await p2;
		expect(r2).toEqual({ ok: true, svg: '<svg>dos</svg>' });
	});

	it('cachea el resultado por fuente', async () => {
		mocks.renderToString.mockImplementation((_lines: string[], ok: (s: string) => void) => {
			ok('<svg>cache</svg>');
		});

		const p1 = renderPlantUml('diagrama_cache');
		const p2 = renderPlantUml('diagrama_cache');

		expect(await p1).toEqual({ ok: true, svg: '<svg>cache</svg>' });
		expect(await p2).toEqual({ ok: true, svg: '<svg>cache</svg>' });
		expect(mocks.renderToString).toHaveBeenCalledTimes(1);
	});

	it('reporta el error del motor', async () => {
		mocks.renderToString.mockImplementation(
			(_lines: string[], _ok: unknown, err: (m: string) => void) => err('sintaxis rota'),
		);

		const result = await renderPlantUml('diagrama_error');

		expect(result).toEqual({ ok: false, error: 'sintaxis rota' });
	});
});
