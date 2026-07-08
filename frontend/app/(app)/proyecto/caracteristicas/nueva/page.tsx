'use client';

import { useRouter } from 'next/navigation';
import CreateCharacteristic from '@/pages/project/CharacteristicsPage/ui/CreateCharacteristic';

export default function NuevaCaracteristicaPage() {
	const router = useRouter();

	return (
		<div className='page-container'>
			<CreateCharacteristic onCreated={() => router.push('/proyecto/caracteristicas')} />
		</div>
	);
}
