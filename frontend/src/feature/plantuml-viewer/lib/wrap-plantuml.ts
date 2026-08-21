export function wrapPlantUmlSource(source: string): string {
	const content = source
		.trim()
		.replace(/^@startuml\s*/i, '')
		.replace(/@enduml\s*$/i, '')
		.trim();
	return `@startuml\n${content}\n@enduml`;
}
