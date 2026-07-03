'use client';

import { useRouter } from 'next/navigation';
import CreateCharacteristic from '@/pages/project/CharacteristicsPage/ui/CreateCharacteristic';

export default function NuevaCaracteristicaPage() {
	const router = useRouter();

	return (
		<div className='flex h-full min-h-0 flex-col overflow-hidden gap-4 pt-8'>
			<CreateCharacteristic onCreated={() => router.push('/proyecto/caracteristicas')} />
		</div>
	);
}
