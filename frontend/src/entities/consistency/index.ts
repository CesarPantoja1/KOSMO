export { useConsistencyStore, clearConsistencyStore } from './model/store';
export { checkConsistency, applyConsistencyImpacts } from './api/api';
export { useConsistencyStream } from './api/useConsistencyStream';
export { ConsistencyProgress } from '@/shared/ui';
export type {
	ConsistencyCheck,
	ConsistencyReportResponse,
	YourChange,
	DownstreamProposal,
	ConsistencyTargetPhase,
	ConsistencyEvaluationStatus,
	PhaseConsistencyStatus,
	ConsistencyStatusResponse,
	ReviewCard,
	ConsistencyReviewResponse,
	EvaluationActionResult,
	BulkResolveRequest,
	BulkResolveResult,
	ConsistencyActivityItem,
	ConsistencyActivityResponse,
} from './model/types';
