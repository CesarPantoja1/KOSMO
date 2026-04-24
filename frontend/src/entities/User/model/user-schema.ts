import { z } from '@/shared/lib';

export const UserSchema = z.object({
	id: z.number(),
	name: z.string(),
});

export type User = z.infer<typeof UserSchema>;
