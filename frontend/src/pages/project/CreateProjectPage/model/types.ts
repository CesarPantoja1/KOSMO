import { z } from 'zod'

const hasEmoji = (value: string) => /\p{Extended_Pictographic}/u.test(value)

export const projectSchema = z.object({
  name: z
    .string()
    .min(3, 'Mínimo 3 caracteres')
    .max(25, 'Máximo 25 caracteres')
    .regex(/^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$/, 'Solo se permiten letras y espacios')
    .refine((val) => !hasEmoji(val), 'No se permiten emojis'),
  description: z
    .string()
    .min(50, 'Mínimo 50 caracteres')
    .max(1000, 'Máximo 1000 caracteres')
    .refine((val) => !hasEmoji(val), 'No se permiten emojis'),
  repo_name: z
    .string()
    .trim()
    .min(1, 'Ingresa el nombre del repositorio')
    .max(100, 'El nombre no puede superar los 100 caracteres'),
  is_public: z.boolean(),
})

export type ProjectFormData = z.infer<typeof projectSchema>
