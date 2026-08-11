import { z } from 'zod';

export const characteristicSchema = z.object({
	title: z
		.string()
		.max(50, 'Máximo 50 caracteres')
		.regex(/^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]*$/, 'Solo se permiten letras y espacios'),
	description: z
		.string()
		.max(500, 'Máximo 500 caracteres')
		.regex(
			/^[a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ\s.,:;\-()¿?¡!]*$/,
			'Solo se permiten letras, números y signos de puntuación básicos',
		),
});
export type CharacteristicFormData = z.infer<typeof characteristicSchema>;

export interface FieldError {
	title: string;
	description: string;
}
