import { useEffect, useRef, useState } from 'react';

import type { RenderState } from '../model/types';
import { renderPlantUml } from '../lib/render-queue';

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

			setState('rendering');
			const result = await renderPlantUml(source);
			if (cancelled()) return;

			if (result.ok) {
				setSvg(result.svg);
				setState('done');
			} else {
				setError(result.error);
				setState('error');
			}
		}

		renderDiagram();

		return () => {
			cancelledRef.current = true;
		};
	}, [source]);

	return { svg, state, error };
}
