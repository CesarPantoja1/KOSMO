import { clearAuthStore } from '@/entities/user/model/store';
import { clearProjectStore } from '@/entities/project';
import { clearDiscoveryStore } from '@/entities/discovery';
import { clearCharacteristicStore } from '@/entities/characteristic';
import { clearModelingStore } from '@/entities/modeling';
import { clearRequirementsStore } from '@/entities/requirements';
import { clearImplementationStore } from '@/entities/implementation';
import { useChatSessionsStore } from '@/entities/chat';
import { useConsistencyGateStore } from '@/entities/consistency';
import { clearAppStore } from 'app/store/app.store';

export const clearAllStores = () => {
	clearAuthStore();
	clearProjectStore();
	clearDiscoveryStore();
	clearCharacteristicStore();
	clearModelingStore();
	clearRequirementsStore();
	clearImplementationStore();
	useChatSessionsStore.getState().reset();
	useConsistencyGateStore.getState().reset();
	clearAppStore();
};
