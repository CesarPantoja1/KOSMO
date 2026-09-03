import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/extract-headings', () => ({
	extractHeadings: vi.fn(() => [{ id: 'a', text: 'A', depth: 1 }]),
}));

import { extractHeadings } from '../lib/extract-headings';
import { useHeadings } from './use-headings';

describe('useHeadings', () => {
	beforeEach(() => {
		vi.mocked(extractHeadings).mockClear();
	});

	it('delega la extracción de encabezados a extractHeadings', () => {
		// Act
		const { result } = renderHook(() => useHeadings('# A'));

		// Assert
		expect(extractHeadings).toHaveBeenCalledWith('# A');
		expect(result.current).toEqual([{ id: 'a', text: 'A', depth: 1 }]);
	});

	it('memoiza el resultado mientras el markdown no cambie', () => {
		// Arrange
		const { result, rerender } = renderHook(({ md }) => useHeadings(md), {
			initialProps: { md: '# A' },
		});
		const firstResult = result.current;

		// Act
		rerender({ md: '# A' });

		// Assert
		expect(result.current).toBe(firstResult);
		expect(extractHeadings).toHaveBeenCalledTimes(1);
	});

	it('recalcula cuando el markdown cambia', () => {
		// Arrange
		const { rerender } = renderHook(({ md }) => useHeadings(md), {
			initialProps: { md: '# A' },
		});

		// Act
		rerender({ md: '# B' });

		// Assert
		expect(extractHeadings).toHaveBeenCalledTimes(2);
	});
});
