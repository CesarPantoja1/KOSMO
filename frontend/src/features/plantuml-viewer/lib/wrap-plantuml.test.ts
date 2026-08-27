import { describe, expect, it } from 'vitest';

import { wrapPlantUmlSource } from './wrap-plantuml';

describe('wrapPlantUmlSource', () => {
	it('envuelve fragmentos sin marcadores', () => {
		const source = '|#lightgray|Sistema|\n:Procesar pago;';

		const result = wrapPlantUmlSource(source);

		expect(result.startsWith('@startuml\n')).toBe(true);
		expect(result.endsWith('\n@enduml')).toBe(true);
		expect(result).toContain(':Procesar pago;');
	});

	it('normaliza diagramas que ya traen marcadores', () => {
		const source = '@startuml\nstart\n:Paso;\nstop\n@enduml';

		const result = wrapPlantUmlSource(source);

		expect(result).toBe('@startuml\nstart\n:Paso;\nstop\n@enduml');
	});

	it('corrige diagramas con marcadores parciales', () => {
		const result = wrapPlantUmlSource('@startuml\nstart\n:Paso;\nstop');

		expect(result).toBe('@startuml\nstart\n:Paso;\nstop\n@enduml');
	});
});
