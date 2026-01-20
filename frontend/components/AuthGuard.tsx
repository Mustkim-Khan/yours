/**
 * Auth Guard Component with Role-Based Routing
 * ==============================================
 * Protects routes from unauthenticated access and enforces role-based access.
 * 
 * Routing Rules:
 * - Unauthenticated → /login
 * - Customer → / (chat only), blocked from /admin and /refills
 * - Admin → /admin (default), can access /refills, blocked from / (chat)
 */

'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';

interface AuthGuardProps {
    children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
    const { user, loading, userRole } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        // Don't redirect while loading
        if (loading) return;

        // Public routes that don't require auth
        const isLoginPage = pathname === '/login';

        // If not authenticated and not on login page, redirect to login
        if (!user && !isLoginPage) {
            router.push('/login');
            return;
        }

        // If authenticated, handle role-based routing
        if (user && userRole) {
            // Define route ownership
            const isAdminRoute = pathname.startsWith('/admin');
            const isRefillsRoute = pathname.startsWith('/refills');
            const isChatRoute = pathname === '/'; // Chat is at root

            if (userRole === 'customer') {
                // Customer can ONLY access / (chat)
                // Block /admin and /refills
                if (isAdminRoute || isRefillsRoute) {
                    router.push('/');
                    return;
                }
            } else if (userRole === 'admin') {
                // Admin can access /admin and /refills
                // Block / (chat)
                if (isChatRoute) {
                    router.push('/admin');
                    return;
                }
            }

            // If on login page and authenticated, redirect to appropriate default
            if (isLoginPage) {
                if (userRole === 'admin') {
                    router.push('/admin');
                } else {
                    router.push('/');
                }
                return;
            }
        }
    }, [user, loading, userRole, router, pathname]);

    // Show loading spinner while checking auth
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-emerald-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-500 dark:text-gray-400">Loading...</p>
                </div>
            </div>
        );
    }

    // If on login page, show children regardless of auth state
    if (pathname === '/login') {
        return <>{children}</>;
    }

    // If not authenticated, show redirect message
    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-emerald-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-500 dark:text-gray-400">Redirecting to login...</p>
                </div>
            </div>
        );
    }

    // Role-based access check for render blocking
    if (userRole) {
        const isAdminRoute = pathname.startsWith('/admin');
        const isRefillsRoute = pathname.startsWith('/refills');
        const isChatRoute = pathname === '/';

        // Customer trying to access admin or refills routes
        if (userRole === 'customer' && (isAdminRoute || isRefillsRoute)) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-emerald-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
                    <div className="text-center">
                        <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <h2 className="text-xl font-semibold text-slate-800 dark:text-white mb-2">Access Denied</h2>
                        <p className="text-slate-500 dark:text-gray-400">Redirecting to chat...</p>
                    </div>
                </div>
            );
        }

        // Admin trying to access chat route
        if (userRole === 'admin' && isChatRoute) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-emerald-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
                    <div className="text-center">
                        <p className="text-slate-500 dark:text-gray-400">Redirecting to admin dashboard...</p>
                    </div>
                </div>
            );
        }
    }

    // Authenticated and authorized - render children
    return <>{children}</>;
}
