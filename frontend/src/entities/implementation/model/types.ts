export type ImplementationStatus = 'idle' | 'generating' | 'completed' | 'failed';

export interface ImplementationMetric {
	value: string;
	label: string;
	icon: 'screens' | 'entities' | 'rules' | 'integrations' | 'validations' | 'actions';
	iconBg: string;
	iconColor: string;
}

export interface ImplementationSummary {
	featureId: string;
	featureTitle: string;
	featureDisplayId: string;
	status: ImplementationStatus;
	metrics: ImplementationMetric[];
	technologies: string[];
	nextSteps: string[];
	generatedAt: string | null;
}
