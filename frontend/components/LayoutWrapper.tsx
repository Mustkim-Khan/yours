'use client';

import Sidebar from '@/components/Sidebar';
import { usePathname } from 'next/navigation';

interface LayoutWrapperProps {
    children: React.ReactNode;
}

/**
 * LayoutWrapper - Conditionally renders app chrome based on route
 * 
 * Landing page (/landing) gets a clean slate without Sidebar or footer.
 * All other routes get the standard app layout with Sidebar and footer.
 */
export default function LayoutWrapper({ children }: LayoutWrapperProps) {
    const pathname = usePathname();
    const isLandingPage = pathname === '/landing';

    // Landing page: render children only (no Sidebar, no footer)
    if (isLandingPage) {
        return <>{children}</>;
    }

    // Standard app layout with Sidebar and footer
    return (
        <>
            <Sidebar />
            <main className="pt-16 flex-1 flex flex-col min-h-0 overflow-auto">
                {children}
            </main>
            {/* Footer */}
            <footer className="flex-shrink-0 text-center py-4 text-sm text-gray-500 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 transition-colors duration-300">
                © 2026 Your Pharma AI. All rights reserved.
            </footer>
        </>
    );
}
