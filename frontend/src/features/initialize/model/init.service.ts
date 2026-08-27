import { useDiscoveryStore } from '@/entities/discovery';
import { getDiscovery } from '@/entities/discovery/api/api';
import { useCharacteristicStore } from '@/entities/characteristic';
import { getCharacteristics } from '@/entities/characteristic/api/api';
import { useModelingStore } from '@/entities/modeling';
import { getDiagram } from '@/entities/modeling/api/api';
import { useRequirementsStore } from '@/entities/requirements';
import { getRequirements } from '@/entities/requirements/api/api';
import { ApiError } from '@/shared/api';

export const initializeProject = async (projectId: string): Promise<void> => {
	try {
		// El 404 es el caso normal cuando aún no existe el documento de descubrimiento
		try {
			const discovery = await getDiscovery(projectId);
			if (discovery) {
				useDiscoveryStore.getState().setCurrentDiscovery(discovery);
			}
		} catch (error) {
			if (!(error instanceof ApiError && error.status === 404)) {
				throw error;
			}
		}

		const characteristics = await getCharacteristics(projectId);
		if (!characteristics || characteristics.length === 0) return;
		useCharacteristicStore.getState().setCurrentCharacteristics(characteristics);

		await Promise.allSettled(
			characteristics.map(async (c) => {
				const [reqResult, diagramResult] = await Promise.allSettled([
					getRequirements(projectId, c.id),
					getDiagram(projectId, c.id),
				]);

				if (reqResult.status === 'fulfilled') {
					const content = reqResult.value?.document_markdown ?? '';
					useRequirementsStore.getState().setHasRequirements(c.id, !!content);
					if (content) {
						useRequirementsStore.getState().setCurrentRequirements(c.id, content);
					}
				}
				if (diagramResult.status === 'fulfilled') {
					useModelingStore.getState().setHasDiagram(c.id, !!diagramResult.value);
				}
			}),
		);
	} catch (error) {
		console.error('[initializeProject] Error:', error);
	}
};
