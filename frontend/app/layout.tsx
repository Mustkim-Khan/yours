import AuthGuard from '@/components/AuthGuard';
import LayoutWrapper from '@/components/LayoutWrapper';
import Providers from '@/components/Providers';
import { AuthProvider } from '@/lib/AuthContext';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
    title: 'Your Pharma AI - Agentic Pharmacy System',
    description: 'Autonomous AI-powered pharmacy with multi-agent architecture',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="h-full">
            <body className={`${inter.className} h-full flex flex-col bg-gray-50 dark:bg-gray-900 transition-colors duration-300`}>
                <AuthProvider>
                    <AuthGuard>
                        <Providers>
                            <LayoutWrapper>
                                {children}
                            </LayoutWrapper>
                        </Providers>
                    </AuthGuard>
                </AuthProvider>
            </body>
        </html>
    );
}
