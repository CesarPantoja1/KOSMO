export type RenderState = 'idle' | 'loading-engine' | 'rendering' | 'done' | 'error';

export interface PlantUmlModule {
	renderToString: (
		lines: string[],
		onSuccess: (svg: string) => void,
		onError: (msg: string) => void,
	) => void;
}

export interface PlantUmlViewerProps {
	source: string;
	isMaximized?: boolean;
	onMaximize?: () => void;
	onMinimize?: () => void;
}
