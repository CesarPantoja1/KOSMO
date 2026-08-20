let vizLoaded = false;
let vizLoading: Promise<void> | null = null;

function loadViz(): Promise<void> {
	if (vizLoaded) return Promise.resolve();
	if (vizLoading) return vizLoading;

	vizLoading = import('@plantuml/core/viz-global.js')
		.then(() => {
			vizLoaded = true;
			vizLoading = null;
		})
		.catch((error: unknown) => {
			vizLoading = null;
			throw new Error('Error al cargar el motor de renderizado PlantUML', { cause: error });
		});

	return vizLoading;
}

let modulePromise: Promise<Record<string, unknown>> | null = null;

function loadPlantUmlModule(): Promise<Record<string, unknown>> {
	if (modulePromise) return modulePromise;
	modulePromise = import('@plantuml/core/plantuml.js');
	modulePromise.catch(() => {
		modulePromise = null;
	});
	return modulePromise;
}

function preloadPlantUmlEngine(): void {
	loadViz().catch(() => undefined);
	loadPlantUmlModule().catch(() => undefined);
}

export { loadPlantUmlModule, loadViz, preloadPlantUmlEngine };
