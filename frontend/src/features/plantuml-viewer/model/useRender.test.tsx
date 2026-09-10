import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const { renderPlantUmlMock } = vi.hoisted(() => ({
	renderPlantUmlMock: vi.fn(),
}));

vi.mock('../lib/render-queue', () => ({
	renderPlantUml: renderPlantUmlMock,
}));

import { useRender } from './useRender';

describe('useRender', () => {
	afterEach(() => {
		renderPlantUmlMock.mockReset();
	});

	it('pasa a done cuando el render devuelve svg', async () => {
		renderPlantUmlMock.mockResolvedValue({ ok: true, svg: '<svg></svg>' });

		const { result } = renderHook(() =>
			useRender('@startuml\nstart\n:Paso;\nstop\n@enduml'),
		);

		await waitFor(() => expect(result.current.state).toBe('done'));
		expect(result.current.svg).toBe('<svg></svg>');
	});

	it('pasa a error cuando el render falla', async () => {
		renderPlantUmlMock.mockResolvedValue({ ok: false, error: 'motor roto' });

		const { result } = renderHook(() =>
			useRender('@startuml\nstart\n:Paso;\nstop\n@enduml'),
		);

		await waitFor(() => expect(result.current.state).toBe('error'));
		expect(result.current.error).toBe('motor roto');
	});

	it('queda en idle con fuente vacía sin llamar al motor', () => {
		const { result } = renderHook(() => useRender('   '));

		expect(result.current.state).toBe('idle');
		expect(renderPlantUmlMock).not.toHaveBeenCalled();
	});
});
