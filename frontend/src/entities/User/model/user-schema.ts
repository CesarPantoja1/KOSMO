import { z } from '@/shared/lib';

export const UserSchema = z.object({
	subject: z.string(),
	scopes: z.array(z.string()),
});

export type User = z.infer<typeof UserSchema>;
