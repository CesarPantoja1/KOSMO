import { render } from '@testing-library/react';
import { MarkdownText } from './markdown-text';

describe('MarkdownText', () => {
	it('renderiza texto plano sin cambios', () => {
		const { container } = render(
			<MarkdownText content='Hola, ¿en qué puedo ayudarte?' />,
		);

		expect(container.textContent).toContain('Hola, ¿en qué puedo ayudarte?');
	});

	it('renderiza negrita sin símbolos literales', () => {
		const { container } = render(<MarkdownText content='Texto con **negrita** aquí' />);

		expect(container.querySelector('strong')).toHaveTextContent('negrita');
		expect(container.textContent).not.toContain('**');
	});

	it('renderiza cursiva sin símbolos literales', () => {
		const { container } = render(<MarkdownText content='Texto con *cursiva* aquí' />);

		expect(container.querySelector('em')).toHaveTextContent('cursiva');
		expect(container.textContent).not.toContain('*');
	});

	it('renderiza código inline sin backticks', () => {
		const { container } = render(
			<MarkdownText content='Usa `npm install` para instalar' />,
		);

		expect(container.querySelector('code')).toHaveTextContent('npm install');
		expect(container.textContent).not.toContain('`');
	});

	it('renderiza encabezados sin #', () => {
		const { container } = render(<MarkdownText content='## Visión del producto' />);

		expect(container.textContent).toContain('Visión del producto');
		expect(container.textContent).not.toContain('##');
	});

	it('distingue nivel de encabezado en clases', () => {
		render(<MarkdownText content={'## H2\n### H3\n#### H4'} />);

		const paragraphs = document.querySelectorAll('p');
		const h2 = paragraphs[0];
		const h3 = paragraphs[1];
		const h4 = paragraphs[2];

		expect(h2.className).toContain('font-semibold');
		expect(h3.className).toContain('font-semibold');
		expect(h4.className).toContain('font-semibold');
		expect(h2.className).toContain('text-[1.1em]');
		expect(h3.className).not.toContain('text-[1.1em]');
	});

	it('renderiza listas con viñetas', () => {
		const { container } = render(
			<MarkdownText content={'- Viajes LATAM\n- Integración\n- Pagos'} />,
		);

		const items = container.querySelectorAll('li');
		expect(items).toHaveLength(3);
		expect(container.textContent).not.toContain('- ');
	});

	it('renderiza mezcla de elementos sin símbolos', () => {
		const content =
			'## Alcance del producto\n\n**Incluido:**\n\n- Módulo de pagos\n- Notificaciones\n\n**Excluido:**\n\n- Facturación electrónica';

		const { container } = render(<MarkdownText content={content} />);

		expect(container.textContent).not.toContain('##');
		expect(container.textContent).not.toContain('**');
		expect(container.textContent).not.toContain('- ');
	});

	it('renderiza enlaces con atributos de seguridad', () => {
		const { container } = render(<MarkdownText content='[KOSMO](https://kosmo.ai)' />);

		const link = container.querySelector('a');
		expect(link).toHaveAttribute('href', 'https://kosmo.ai');
		expect(link).toHaveAttribute('target', '_blank');
		expect(link).toHaveAttribute('rel', 'noreferrer');
	});

	it('rinde contenido vacío sin errores', () => {
		const { container } = render(<MarkdownText content='' />);

		expect(container.querySelector('div')).toBeInTheDocument();
	});
});
