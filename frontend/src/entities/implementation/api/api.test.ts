import { describe, expect, it } from 'vitest';
import { buildSummary } from './api';

describe('buildSummary', () => {
	it('construye el resumen con métricas reales desde el evento done', () => {
		// Arrange
		const data: Record<string, unknown> = {
			status: 'implemented',
			generated_files: ['src/app/page.tsx', 'tests/app.test.tsx'],
			traceability_edges: 4,
		};

		// Act
		const summary = buildSummary(
			'feat_01',
			'Registrar gastos',
			'F-01',
			data,
			'2026-08-19T10:00:00Z',
		);

		// Assert
		expect(summary.featureId).toBe('feat_01');
		expect(summary.featureTitle).toBe('Registrar gastos');
		expect(summary.featureDisplayId).toBe('F-01');
		expect(summary.status).toBe('completed');
		expect(summary.metrics).toHaveLength(3);
		expect(summary.metrics[0]).toMatchObject({ value: '2', label: 'Archivos generados' });
		expect(summary.metrics[1]).toMatchObject({ value: '4/4', label: 'Validaciones en verde' });
		expect(summary.metrics[2]).toMatchObject({
			value: '4',
			label: 'Aristas de trazabilidad',
		});
		expect(summary.generatedAt).toBe('2026-08-19T10:00:00Z');
		expect(summary.technologies).toContain('Next.js');
	});

	it('usa cero cuando el evento no trae archivos ni aristas', () => {
		// Arrange
		const data: Record<string, unknown> = { status: 'implemented' };

		// Act
		const summary = buildSummary('feat_02', 'Título', 'F-02', data, '2026-08-19T10:00:00Z');

		// Assert
		expect(summary.metrics[0].value).toBe('0');
		expect(summary.metrics[2].value).toBe('0');
	});
});
