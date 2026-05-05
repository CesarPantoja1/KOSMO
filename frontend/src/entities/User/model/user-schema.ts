import { z } from '@/shared/lib';

export const UserSchema = z.object({
	name: z.string(),
});

export type User = z.infer<typeof UserSchema>;
