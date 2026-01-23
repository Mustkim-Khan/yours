'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Bot, Moon, Sun, LogOut } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { useAuth, UserRole } from '@/lib/AuthContext';

// Navigation items with role-based visibility
// Customer: Chat only ("/")
// Admin: Refills + Admin Dashboard
const navItems = [
    { href: '/', label: 'Conversational Chat', roles: ['customer'] },
    { href: '/orders', label: 'My Orders', roles: ['customer'] },
    { href: '/admin', label: 'Admin Inventory Dashboard', roles: ['admin'] },
    { href: '/admin/refills', label: 'Proactive Refill Alerts', roles: ['admin'] },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { theme, setTheme } = useTheme();
    const { user, userRole, loading, signOut } = useAuth();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const toggleTheme = () => {
        setTheme(theme === 'dark' ? 'light' : 'dark');
    };

    // Handle logout
    const handleLogout = async () => {
        await signOut();
        router.push('/login');
    };

    // Don't show nav on login page
    if (pathname === '/login') {
        return null;
    }

    // CRITICAL: Don't render navigation until loading is complete AND role is resolved
    // This prevents the flash of wrong navigation tabs
    if (loading || !userRole) {
        return (
            <header className="fixed left-0 top-0 right-0 h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center px-6 z-50 transition-colors duration-300">
                {/* Logo */}
                <div className="flex items-center gap-2 mr-8">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                        <Bot className="w-5 h-5 text-white" />
                    </div>
                    <h1 className="font-semibold text-gray-900 dark:text-white transition-colors">Your Pharma Ai</h1>
                </div>
                {/* Loading placeholder for navigation */}
                <nav className="flex items-center gap-1 mx-auto">
                    <div className="h-8 w-32 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"></div>
                </nav>
            </header>
        );
    }

    // Filter navigation items based on user role (role is now guaranteed to be resolved)
    const visibleNavItems = navItems.filter(item => {
        return item.roles.includes(userRole);
    });

    return (
        <header className="fixed left-0 top-0 right-0 h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center px-6 z-50 transition-colors duration-300">
            {/* Logo */}
            <div className="flex items-center gap-2 mr-8">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                </div>
                <h1 className="font-semibold text-gray-900 dark:text-white transition-colors">Your Pharma Ai</h1>
            </div>

            {/* Navigation - Role-based filtering (role is guaranteed to be resolved here) */}
            <nav className="flex items-center gap-1 mx-auto">
                {visibleNavItems.map((item) => {
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${isActive
                                ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800'
                                : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'
                                }`}
                        >
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Right side: User info, Theme Toggle, Logout */}
            <div className="flex items-center gap-3">
                {/* User email badge */}
                {user && (
                    <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-full text-xs text-gray-600 dark:text-gray-300">
                        <span>{user.email}</span>
                        {userRole === 'admin' && (
                            <span className="px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 rounded text-xs font-medium">
                                Admin
                            </span>
                        )}
                    </div>
                )}

                {/* Theme Toggle */}
                {mounted && (
                    <button
                        onClick={toggleTheme}
                        className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors"
                        aria-label="Toggle Dark Mode"
                    >
                        {theme === 'dark' ? (
                            <Sun className="w-5 h-5" />
                        ) : (
                            <Moon className="w-5 h-5" />
                        )}
                    </button>
                )}

                {/* Logout Button */}
                {user && (
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        aria-label="Logout"
                    >
                        <LogOut className="w-4 h-4" />
                        <span className="hidden sm:inline">Logout</span>
                    </button>
                )}
            </div>
        </header>
    );
}
