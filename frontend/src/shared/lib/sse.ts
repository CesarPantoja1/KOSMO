export type SseEventHandler = (event: Record<string, unknown>) => void;

export async function consumeSse(response: Response, onEvent: SseEventHandler): Promise<void> {
	if (!response.body) {
		throw new Error('Respuesta sin cuerpo');
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';

	const dispatch = (block: string) => {
		for (const line of block.split('\n')) {
			if (!line.startsWith('data: ')) continue;
			const data = line.slice(6).trim();
			if (!data) continue;
			let parsed: Record<string, unknown> | null = null;
			try {
				parsed = JSON.parse(data) as Record<string, unknown>;
			} catch {
				// ignorar líneas malformadas
				continue;
			}
			if (parsed) {
				onEvent(parsed);
			}
		}
	};

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });

		const blocks = buffer.split('\n\n');
		buffer = blocks.pop() ?? '';
		for (const block of blocks) {
			dispatch(block);
		}
	}

	if (buffer.trim()) {
		dispatch(buffer);
	}
}
