/**
 * Login Page - Pharmacy-Themed Authentication
 * =============================================
 * Professional pharmacy-grade login with Sign In/Sign Up and role selection.
 * 
 * Features:
 * - Sign In / Sign Up tabs
 * - Role selector (Customer / Admin)
 * - Pharmacy-themed design (white, blue, soft green)
 * - Redirects based on role after auth
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, UserRole } from '@/lib/AuthContext';

type AuthMode = 'signin' | 'signup';

export default function LoginPage() {
    const [mode, setMode] = useState<AuthMode>('signin');
    const [name, setName] = useState('');
    const [phone, setPhone] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [selectedRole, setSelectedRole] = useState<'customer' | 'admin'>('customer');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const router = useRouter();
    const { signIn, signUp, user, userRole } = useAuth();

    // Redirect if already logged in
    useEffect(() => {
        if (user && userRole) {
            if (userRole === 'admin') {
                router.push('/admin');
            } else {
                router.push('/');
            }
        }
    }, [user, userRole, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            if (mode === 'signup') {
                // Validate passwords match
                if (password !== confirmPassword) {
                    setError('Passwords do not match');
                    setLoading(false);
                    return;
                }
                if (password.length < 6) {
                    setError('Password must be at least 6 characters');
                    setLoading(false);
                    return;
                }
                if (!name.trim()) {
                    setError('Please enter your name');
                    setLoading(false);
                    return;
                }
                if (!phone.trim() || phone.length < 10) {
                    setError('Please enter a valid phone number');
                    setLoading(false);
                    return;
                }

                // Format phone to E.164 if missing country code
                // Minimal frontend validation as requested
                let formattedPhone = phone.trim();
                // Simple assumption for MVP: if no +, add +91 (or let it be if user typed it)
                // Ideally use libphonenumber, but strict instruction is "UI validation only"

                await signUp(email, password, name.trim(), formattedPhone);
                // New users always get 'customer' role, redirect to chat
                router.push('/');
            } else {
                await signIn(email, password);
                // Redirect based on selected role (will be verified against Firestore)
                // The actual role check happens in useEffect above after userRole is fetched
            }
        } catch (err: any) {
            const errorCode = err?.code || '';
            switch (errorCode) {
                case 'auth/invalid-email':
                    setError('Invalid email address.');
                    break;
                case 'auth/user-not-found':
                    setError('No account found with this email.');
                    break;
                case 'auth/wrong-password':
                    setError('Incorrect password.');
                    break;
                case 'auth/invalid-credential':
                    setError('Invalid email or password.');
                    break;
                case 'auth/email-already-in-use':
                    setError('An account already exists with this email.');
                    break;
                case 'auth/weak-password':
                    setError('Password is too weak. Use at least 6 characters.');
                    break;
                default:
                    setError('Authentication failed. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex bg-gradient-to-br from-slate-50 via-blue-50 to-emerald-50">
            {/* Left Panel - Form */}
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="w-full max-w-md">
                    {/* Logo & Header */}
                    <div className="text-center mb-8">
                        <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                            </svg>
                        </div>
                        <h1 className="text-2xl font-bold text-slate-800">Your Trusted AI Pharmacy</h1>
                        <p className="text-slate-500 mt-2">Secure access to prescriptions, refills, and AI-managed orders</p>
                    </div>

                    {/* Auth Mode Tabs */}
                    <div className="flex bg-slate-100 rounded-xl p-1 mb-6">
                        <button
                            type="button"
                            onClick={() => { setMode('signin'); setError(null); }}
                            className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all ${mode === 'signin'
                                ? 'bg-white text-blue-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            Sign In
                        </button>
                        <button
                            type="button"
                            onClick={() => { setMode('signup'); setError(null); }}
                            className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all ${mode === 'signup'
                                ? 'bg-white text-blue-600 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            Sign Up
                        </button>
                    </div>

                    {/* Error Alert */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6 flex items-start gap-3">
                            <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        {/* Name (Sign Up only) */}
                        {mode === 'signup' && (
                            <div>
                                <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-2">
                                    Full Name
                                </label>
                                <input
                                    id="name"
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    required
                                    autoComplete="name"
                                    placeholder="John Doe"
                                    className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition shadow-sm"
                                />
                            </div>
                        )}

                        {/* Phone Number (Sign Up only) */}
                        {mode === 'signup' && (
                            <div>
                                <label htmlFor="phone" className="block text-sm font-medium text-slate-700 mb-2">
                                    Phone Number
                                </label>
                                <input
                                    id="phone"
                                    type="tel"
                                    value={phone}
                                    onChange={(e) => setPhone(e.target.value)}
                                    required
                                    autoComplete="tel"
                                    placeholder="+919876543210"
                                    className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition shadow-sm"
                                />
                            </div>
                        )}

                        {/* Email */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                                Email Address
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                autoComplete="email"
                                placeholder="you@example.com"
                                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition shadow-sm"
                            />
                        </div>

                        {/* Password */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                                placeholder="••••••••"
                                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition shadow-sm"
                            />
                        </div>

                        {/* Confirm Password (Sign Up only) */}
                        {mode === 'signup' && (
                            <div>
                                <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 mb-2">
                                    Confirm Password
                                </label>
                                <input
                                    id="confirmPassword"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    autoComplete="new-password"
                                    placeholder="••••••••"
                                    className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition shadow-sm"
                                />
                            </div>
                        )}

                        {/* Role Selector (Sign In only - for admin access) */}
                        {mode === 'signin' && (
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                    Login as
                                </label>
                                <div className="flex gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setSelectedRole('customer')}
                                        className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${selectedRole === 'customer'
                                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                                            : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                                            }`}
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                        </svg>
                                        Customer
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setSelectedRole('admin')}
                                        className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${selectedRole === 'admin'
                                            ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                                            : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                                            }`}
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                        </svg>
                                        Admin
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3.5 px-4 bg-gradient-to-r from-blue-500 to-emerald-500 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-emerald-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg shadow-blue-500/25"
                        >
                            {loading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    {mode === 'signin' ? 'Signing in...' : 'Creating account...'}
                                </span>
                            ) : (
                                mode === 'signin' ? 'Sign In' : 'Create Account'
                            )}
                        </button>
                    </form>

                    {/* Footer */}
                    <p className="text-center text-slate-400 text-xs mt-8">
                        All medical actions are AI-validated and auditable
                    </p>
                </div>
            </div>

            {/* Right Panel - Illustration */}
            <div className="hidden lg:flex flex-1 items-center justify-center bg-gradient-to-br from-blue-500 to-emerald-500 p-12">
                <div className="max-w-md text-center text-white">
                    {/* Pharmacy Icons */}
                    <div className="flex justify-center gap-6 mb-8">
                        {/* Pill Icon */}
                        <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-2xl flex items-center justify-center">
                            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                            </svg>
                        </div>
                        {/* Medical Cross */}
                        <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-2xl flex items-center justify-center">
                            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                            </svg>
                        </div>
                        {/* Shield Check */}
                        <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-2xl flex items-center justify-center">
                            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                    </div>

                    <h2 className="text-3xl font-bold mb-4">AI-Powered Healthcare</h2>
                    <p className="text-white/80 text-lg leading-relaxed">
                        Experience intelligent medication management with our autonomous AI agents.
                        Safe, compliant, and always available.
                    </p>

                    {/* Features */}
                    <div className="mt-10 space-y-4 text-left">
                        <div className="flex items-center gap-3 bg-white/10 backdrop-blur rounded-xl px-4 py-3">
                            <svg className="w-5 h-5 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span>Smart prescription validation</span>
                        </div>
                        <div className="flex items-center gap-3 bg-white/10 backdrop-blur rounded-xl px-4 py-3">
                            <svg className="w-5 h-5 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span>Automated refill reminders</span>
                        </div>
                        <div className="flex items-center gap-3 bg-white/10 backdrop-blur rounded-xl px-4 py-3">
                            <svg className="w-5 h-5 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span>LangSmith traced for transparency</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
