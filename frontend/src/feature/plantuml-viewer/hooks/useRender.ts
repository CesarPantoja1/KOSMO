import { useEffect, useRef, useState } from 'react';

import type { PlantUmlModule, RenderState } from '../model/types';
import {
	PLANTUML_MODULE_URL,
	dynamicImport,
	loadViz,
} from '../lib/engine-loader';

export function useRender(source: string) {
	const [svg, setSvg] = useState<string | null>(null);
	const [state, setState] = useState<RenderState>('idle');
	const [error, setError] = useState<string | null>(null);
	const cancelledRef = useRef(false);

	useEffect(() => {
		cancelledRef.current = false;
		const cancelled = () => cancelledRef.current;

		async function renderDiagram() {
			setSvg(null);
			setError(null);

			if (!source.trim()) {
				setState('idle');
				return;
			}

			try {
				setState('loading-engine');
				await loadViz();
				if (cancelled()) return;

				setState('rendering');
				const plantumlModule = (await dynamicImport(
					PLANTUML_MODULE_URL,
				)) as unknown as PlantUmlModule;
				if (cancelled()) return;

				const svgResult = await new Promise<string>((resolve, reject) => {
					plantumlModule.renderToString(
						source.split('\n'),
						(result: string) => resolve(result),
						(err: string) => reject(new Error(err)),
					);
				});

				if (cancelled()) return;
				setSvg(svgResult);
				setState('done');
			} catch (err) {
				if (!cancelled()) {
					setError(
						err instanceof Error
							? err.message
							: 'Error al renderizar el diagrama PlantUML',
					);
					setState('error');
				}
			}
		}

		renderDiagram();

		return () => {
			cancelledRef.current = true;
		};
	}, [source]);

	return { svg, state, error };
}
