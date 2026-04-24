import './globals.css';
import { MSWProvider } from './providers/msw-provider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html lang='es'>
			<body>
				<MSWProvider>{children}</MSWProvider>
			</body>
		</html>
	);
}
