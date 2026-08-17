export { useConsistencyGateStore } from './model/gate-store';
export {
	CONSISTENCY_PHASE_ORDER,
	CONSISTENCY_REVIEW_ROUTES,
	sumPhaseStatus,
	firstPhaseToReview,
} from './model/selectors';
export {
	getConsistencyStatus,
	getConsistencyReview,
	applyConsistencyEvaluation,
	discardConsistencyEvaluation,
	bulkResolveConsistency,
	getConsistencyActivity,
} from './api/api';
export type {
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
