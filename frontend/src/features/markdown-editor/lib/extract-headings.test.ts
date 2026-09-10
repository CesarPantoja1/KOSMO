import { describe, expect, it } from 'vitest';
import { extractHeadings } from './extract-headings';

describe('extractHeadings', () => {
	it('extrae encabezados con su nivel de profundidad', () => {
		// Act
		const headings = extractHeadings('# Título\n\n## Subtítulo\n\nTexto normal.\n\n### Detalle');

		// Assert
		expect(headings).toEqual([
			{ id: 'ttulo', text: 'Título', depth: 1 },
			{ id: 'subttulo', text: 'Subtítulo', depth: 2 },
			{ id: 'detalle', text: 'Detalle', depth: 3 },
		]);
	});

	it('elimina caracteres acentuados y símbolos al generar el slug (no transliterados)', () => {
		// Act
		const headings = extractHeadings('# Sección 1: Visión & Alcance!');

		// Assert
		expect(headings[0].id).toBe('seccin-1-visin-alcance');
	});

	it('ignora encabezados vacíos', () => {
		// Act
		const headings = extractHeadings('#    \n\nTexto\n\n## Real');

		// Assert
		expect(headings).toHaveLength(1);
		expect(headings[0].text).toBe('Real');
	});

	it('extrae el texto de encabezados con formato inline (bold/italic)', () => {
		// Act
		const headings = extractHeadings('# Título **importante** y *cursiva*');

		// Assert
		expect(headings[0].text).toBe('Título importante y cursiva');
	});

	it('devuelve una lista vacía cuando no hay encabezados', () => {
		// Act
		const headings = extractHeadings('Solo un párrafo sin títulos.');

		// Assert
		expect(headings).toEqual([]);
	});
});
