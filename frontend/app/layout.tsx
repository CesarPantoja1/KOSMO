import './globals.css';
import { MSWProvider } from './providers/msw-provider';
import { ThemeProvider } from 'app/providers/theme-provider';

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
