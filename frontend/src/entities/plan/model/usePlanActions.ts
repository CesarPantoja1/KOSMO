import { useCallback } from 'react';
import { usePlanStore } from './store';
import { addPlanChange, deletePlanChange } from '../api/api';
import type { ChangeSuggestion } from '@/feature/chatbot/types/chatbot';
import type { PlanChange } from './types';

export function usePlanActions(projectId: string | null, phase: string, contextId: string | null) {
	const addToPlan = usePlanStore((s) => s.addToPlan);
	const removeFromPlan = usePlanStore((s) => s.removeFromPlan);

	const handlePlanAction = useCallback(
		(
			action: 'add' | 'remove' | 'discard',
			suggestion: ChangeSuggestion,
			_messageId: string,
		) => {
			if (!projectId || !contextId) return;

			if (action === 'add') {
				const change: PlanChange = {
					id: suggestion.id,
					section: suggestion.section,
					description: suggestion.description ?? suggestion.section,
					diff: { before: suggestion.diff_before, after: suggestion.diff_after },
					status: 'pending',
					origin: 'chat',
					phase,
					context: contextId,
					rationale: suggestion.rationale ?? undefined,
					created_at: new Date().toISOString(),
				};
				addToPlan(phase, change);
				addPlanChange(projectId, phase, change).catch(() => {});
			}

			if (action === 'remove') {
				removeFromPlan(phase, suggestion.id);
				deletePlanChange(projectId, phase, suggestion.id).catch(() => {});
			}
		},
		[projectId, phase, contextId, addToPlan, removeFromPlan],
	);

	return handlePlanAction;
}
