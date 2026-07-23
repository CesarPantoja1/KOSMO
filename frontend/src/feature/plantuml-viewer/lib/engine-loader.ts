const PLANTUML_VERSION = '1.2026.6';
const CDN_BASE = `https://unpkg.com/@plantuml/core@${PLANTUML_VERSION}`;
const VIZ_GLOBAL_URL = `${CDN_BASE}/viz-global.js`;
const PLANTUML_MODULE_URL = `${CDN_BASE}/plantuml.js`;

const dynamicImport = new Function('url', 'return import(url)') as (
	url: string,
) => Promise<Record<string, unknown>>;

let vizLoaded = false;
let vizLoading: Promise<void> | null = null;

function loadViz(): Promise<void> {
	if (vizLoaded) return Promise.resolve();
	if (vizLoading) return vizLoading;

	vizLoading = new Promise((resolve, reject) => {
		const script = document.createElement('script');
		script.src = VIZ_GLOBAL_URL;
		script.async = false;
		script.onload = () => {
			vizLoaded = true;
			vizLoading = null;
			resolve();
		};
		script.onerror = () => {
			vizLoading = null;
			reject(new Error('Error al cargar el motor de renderizado PlantUML'));
		};
		document.head.appendChild(script);
	});

	return vizLoading;
}

export { PLANTUML_MODULE_URL, dynamicImport, loadViz };
