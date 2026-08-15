import type { PlantUmlModule } from '../model/types';
import { loadPlantUmlModule, loadViz } from './engine-loader';

const RENDER_TIMEOUT_MS = 20000;
const CACHE_LIMIT = 50;

export type RenderResult = { ok: true; svg: string } | { ok: false; error: string };

const cache = new Map<string, Promise<RenderResult>>();
let queueTail: Promise<void> = Promise.resolve();
let modulePromise: Promise<PlantUmlModule> | null = null;

function getModule(): Promise<PlantUmlModule> {
	if (!modulePromise) {
		modulePromise = (async () => {
			await loadViz();
			return (await loadPlantUmlModule()) as unknown as PlantUmlModule;
		})();
	}
	return modulePromise;
}

export function renderPlantUml(source: string): Promise<RenderResult> {
	const cached = cache.get(source);
	if (cached) return cached;

	const task = queueTail.then(async (): Promise<RenderResult> => {
		try {
			const engine = await getModule();
			return await new Promise<RenderResult>((resolve) => {
				let settled = false;
				const finish = (result: RenderResult) => {
					if (settled) return;
					settled = true;
					resolve(result);
				};
				const timer = window.setTimeout(
					() =>
						finish({
							ok: false,
							error: 'El motor de diagramas tardó demasiado en renderizar.',
						}),
					RENDER_TIMEOUT_MS,
				);
				try {
					engine.renderToString(
						source.split('\n'),
						(svg: string) => {
							window.clearTimeout(timer);
							finish({ ok: true, svg });
						},
						(err: string) => {
							window.clearTimeout(timer);
							finish({ ok: false, error: err });
						},
					);
				} catch (err) {
					window.clearTimeout(timer);
					finish({
						ok: false,
						error:
							err instanceof Error
								? err.message
								: 'Error al renderizar el diagrama PlantUML',
					});
				}
			});
		} catch (err) {
			return {
				ok: false,
				error:
					err instanceof Error
						? err.message
						: 'Error al cargar el motor de diagramas',
			} satisfies RenderResult;
		}
	});

	cache.set(source, task);
	queueTail = task.then(
		() => undefined,
		() => undefined,
	);
	void task.then((result) => {
		if (!result.ok) cache.delete(source);
	});

	if (cache.size > CACHE_LIMIT) {
		const oldest = cache.keys().next().value;
		if (oldest !== undefined) cache.delete(oldest);
	}

	return task;
}
