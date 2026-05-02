import './globals.css';
import { MSWProvider } from './providers/msw-provider';
import { ThemeProvider } from '@/shared/ui/ThemeProvider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html lang='es'>
			<body>
				<ThemeProvider>
					<MSWProvider>{children}</MSWProvider>
				</ThemeProvider>
			</body>
		</html>
	);
}
