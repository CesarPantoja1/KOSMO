import { apiClient } from '@/shared/api';
import { Project } from '@/shared/types/project';

interface CreateProjectBody {
	name: string;
	description: string;
}

export const createProject = (body: CreateProjectBody) => {
	const token =
		localStorage.getItem('token') ||
		'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MzY2OGIyYi03OWFjLTQ2MDMtOWIyYi1jYzM4NWMxNTAyODUiLCJpc3MiOiJrb3NtbyIsImF1ZCI6Imtvc21vLWFwaSIsImlhdCI6MTc4MTcxNDY5MCwiZXhwIjoxNzgxNzE1NTkwLCJqdGkiOiI2ZjZjMjlkMWE1MjU0OGViYjE1Yjg5ZmM0MTE2NjliNiIsInR5cGUiOiJhY2Nlc3MiLCJzY29wZXMiOlsiYWdlbnQ6cnVuIiwicHJvZmlsZTpyZWFkIl0sImZhbSI6ImJmMGQ0MTg4M2M2NzQ2MTJiYmU0ZjVlZTBlMmUyNmJlIn0.YXcpWcZlyWTk0uceEXvCZXnrWxARr4vozrgXOki9bTaHZKZS933nntomQOSfnYTlzKDZhUgx2mGPGLn1OWW0oUK59HqIdnst51raVbuULMGcfELFYU1SMf9XD3V2u5j4Evtei_3d6NtpPaMfL9wJAEdM-mWvdKZJJuMF1xzMBOXLEJiBhchEcSV5rFeN2l7b-A3cyDrA_t29Ve6z9P1FBcMa850TmV-9w-tq9R5B9EmKiLRM5C3JVsZsCvJNKVIhkTh6PZFRlmTU0VjWu94LUpInMOSAVtwvg5vNFdqrnWTQxWgtcGsVMngeac_kFxB-C0qRlJK2dZ9yMPWoDW-DYg';

	return apiClient<Project>('/api/v1/projects', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(body),
	});
};
