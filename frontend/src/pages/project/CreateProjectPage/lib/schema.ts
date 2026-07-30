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
})

export type ProjectFormData = z.infer<typeof projectSchema>
