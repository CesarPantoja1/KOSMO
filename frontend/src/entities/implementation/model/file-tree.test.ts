import { describe, expect, it } from 'vitest';
import { buildFileTree } from './file-tree';

describe('buildFileTree', () => {
	it('agrupa archivos en árbol por directorios y ordena alfabéticamente', () => {
		// Arrange
		const paths = [
			'tests/app.test.tsx',
			'src/app/page.tsx',
			'package.json',
			'src/app/layout.tsx',
		];

		// Act
		const tree = buildFileTree(paths);

		// Assert
		expect(tree.map((node) => node.name)).toEqual(['package.json', 'src', 'tests']);

		const src = tree.find((node) => node.name === 'src');
		expect(src?.children.map((node) => node.name)).toEqual(['app']);
		expect(src?.children[0].children.map((node) => node.name)).toEqual([
			'layout.tsx',
			'page.tsx',
		]);

		const tests = tree.find((node) => node.name === 'tests');
		expect(tests?.children.map((node) => node.name)).toEqual(['app.test.tsx']);
		expect(tests?.children[0].children).toHaveLength(0);
	});

	it('elimina duplicados de la lista de paths', () => {
		// Arrange
		const paths = ['src/a.ts', 'src/a.ts'];

		// Act
		const tree = buildFileTree(paths);

		// Assert
		expect(tree).toHaveLength(1);
		expect(tree[0].children).toHaveLength(1);
	});

	it('devuelve un árbol vacío para una lista vacía', () => {
		// Arrange & Act
		const tree = buildFileTree([]);

		// Assert
		expect(tree).toHaveLength(0);
	});
});
