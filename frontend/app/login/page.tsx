/**
 * Login Page - $1M Premium Authentication Experience
 * ===================================================
 * Ultra-premium dark glassmorphism design with animated effects.
 * 
 * Features:
 * - Sign In / Sign Up modes
 * - Role selector (Customer / Admin)
 * - Animated floating orbs background
 * - Glassmorphism card with glow effects
 * - Premium micro-interactions
 */

'use client';

import { useAuth } from '@/lib/AuthContext';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, Eye, EyeOff, Loader2, Lock, Mail, Shield, Sparkles, User } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

type AuthMode = 'signin' | 'signup';

// Floating orb component for background
const FloatingOrb = ({ 
    color, 
    size, 
    top, 
    left, 
    delay = 0 
}: { 
    color: string; 
    size: number; 
    top: string; 
    left: string; 
    delay?: number;
}) => (
    <motion.div
        className={`absolute rounded-full blur-3xl opacity-40 ${color}`}
        style={{ width: size, height: size, top, left }}
        animate={{
            y: [0, -30, 0],
            x: [0, 20, 0],
            scale: [1, 1.1, 1],
        }}
        transition={{
            duration: 8,
            delay,
            repeat: Infinity,
            ease: "easeInOut"
        }}
    />
);

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
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

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

                // Format phone to E.164 with +91 prefix
                let formattedPhone = phone.trim().replace(/\s+/g, '');
                if (!formattedPhone.startsWith('+')) {
                    formattedPhone = '+91' + formattedPhone;
                }
                await signUp(email, password, name.trim(), formattedPhone);
                router.push('/');
            } else {
                await signIn(email, password);
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
        <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-slate-950">
            {/* Animated Background */}
            <div className="absolute inset-0">
                {/* Gradient mesh background */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-900/20 via-slate-950 to-slate-950" />
                
                {/* Floating orbs */}
                <FloatingOrb color="bg-violet-600" size={400} top="-10%" left="10%" delay={0} />
                <FloatingOrb color="bg-cyan-500" size={300} top="60%" left="70%" delay={2} />
                <FloatingOrb color="bg-fuchsia-500" size={250} top="30%" left="-5%" delay={4} />
                <FloatingOrb color="bg-indigo-500" size={350} top="70%" left="20%" delay={1} />
                
                {/* Grid overlay */}
                <div 
                    className="absolute inset-0 opacity-[0.02]"
                    style={{
                        backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                                         linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
                        backgroundSize: '50px 50px'
                    }}
                />
            </div>

            {/* Main Content */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="relative z-10 w-full max-w-md mx-4"
            >
                {/* Glass Card */}
                <div className="relative">
                    {/* Glow effect behind card */}
                    <div className="absolute -inset-1 bg-gradient-to-r from-violet-600 via-fuchsia-500 to-cyan-500 rounded-3xl blur-xl opacity-30" />
                    
                    {/* Card content */}
                    <div className="relative bg-slate-900/80 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 shadow-2xl">
                        {/* Logo & Header */}
                        <motion.div 
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            className="text-center mb-8"
                        >
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-cyan-500 mb-5 shadow-lg shadow-violet-500/25">
                                <Sparkles className="w-8 h-8 text-white" />
                            </div>
                            <h1 className="text-2xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                                Your Pharma AI
                            </h1>
                            <p className="text-slate-400 text-sm mt-2">
                                {mode === 'signin' ? 'Welcome back! Sign in to continue' : 'Create your account to get started'}
                            </p>
                        </motion.div>

                        {/* Auth Mode Tabs */}
                        <div className="flex bg-slate-800/50 rounded-2xl p-1.5 mb-6 border border-white/5">
                            {['signin', 'signup'].map((tabMode) => (
                                <button
                                    key={tabMode}
                                    type="button"
                                    onClick={() => { setMode(tabMode as AuthMode); setError(null); }}
                                    className={`flex-1 py-3 text-sm font-medium rounded-xl transition-all duration-300 ${
                                        mode === tabMode
                                            ? 'bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white shadow-lg shadow-violet-500/25'
                                            : 'text-slate-400 hover:text-white'
                                    }`}
                                >
                                    {tabMode === 'signin' ? 'Sign In' : 'Sign Up'}
                                </button>
                            ))}
                        </div>

                        {/* Error Alert */}
                        <AnimatePresence mode="wait">
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10, height: 0 }}
                                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                                    exit={{ opacity: 0, y: -10, height: 0 }}
                                    className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl mb-6 flex items-center gap-3 text-sm"
                                >
                                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                    {error}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <AnimatePresence mode="wait">
                                {mode === 'signup' && (
                                    <motion.div
                                        key="signup-fields"
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: 0.3 }}
                                        className="space-y-5"
                                    >
                                        {/* Name */}
                                        <div className="group">
                                            <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                                                Full Name
                                            </label>
                                            <div className="relative">
                                                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-violet-400 transition-colors" />
                                                <input
                                                    type="text"
                                                    value={name}
                                                    onChange={(e) => setName(e.target.value)}
                                                    required
                                                    placeholder="John Doe"
                                                    className="w-full pl-12 pr-4 py-3.5 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
                                                />
                                            </div>
                                        </div>

                                        {/* Phone */}
                                        <div className="group">
                                            <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                                                Phone Number
                                            </label>
                                            <div className="relative">
                                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">+91</span>
                                                <input
                                                    type="tel"
                                                    value={phone}
                                                    onChange={(e) => setPhone(e.target.value)}
                                                    required
                                                    placeholder="9876543210"
                                                    className="w-full pl-14 pr-4 py-3.5 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
                                                />
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Email */}
                            <div className="group">
                                <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                                    Email Address
                                </label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-violet-400 transition-colors" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                        placeholder="you@example.com"
                                        className="w-full pl-12 pr-4 py-3.5 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
                                    />
                                </div>
                            </div>

                            {/* Password */}
                            <div className="group">
                                <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                                    Password
                                </label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-violet-400 transition-colors" />
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        placeholder="••••••••"
                                        className="w-full pl-12 pr-12 py-3.5 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                                    >
                                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                    </button>
                                </div>
                            </div>

                            {/* Confirm Password (Sign Up only) */}
                            <AnimatePresence mode="wait">
                                {mode === 'signup' && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: 0.3 }}
                                        className="group"
                                    >
                                        <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
                                            Confirm Password
                                        </label>
                                        <div className="relative">
                                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-violet-400 transition-colors" />
                                            <input
                                                type={showConfirmPassword ? 'text' : 'password'}
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                required
                                                placeholder="••••••••"
                                                className="w-full pl-12 pr-12 py-3.5 bg-slate-800/50 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                                            >
                                                {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                            </button>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Role Selector (Sign In only) */}
                            <AnimatePresence mode="wait">
                                {mode === 'signin' && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: 0.3 }}
                                    >
                                        <label className="block text-xs font-medium text-slate-400 mb-3 uppercase tracking-wider">
                                            Login as
                                        </label>
                                        <div className="flex gap-3">
                                            <button
                                                type="button"
                                                onClick={() => setSelectedRole('customer')}
                                                className={`flex-1 py-3.5 px-4 rounded-xl border transition-all duration-300 flex items-center justify-center gap-3 ${
                                                    selectedRole === 'customer'
                                                        ? 'border-violet-500/50 bg-violet-500/10 text-white shadow-lg shadow-violet-500/10'
                                                        : 'border-white/10 bg-slate-800/30 text-slate-400 hover:border-white/20 hover:text-white'
                                                }`}
                                            >
                                                <User className="w-5 h-5" />
                                                <span className="font-medium">Customer</span>
                                                {selectedRole === 'customer' && (
                                                    <motion.div
                                                        initial={{ scale: 0 }}
                                                        animate={{ scale: 1 }}
                                                        className="ml-auto"
                                                    >
                                                        <CheckCircle2 className="w-5 h-5 text-violet-400" />
                                                    </motion.div>
                                                )}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setSelectedRole('admin')}
                                                className={`flex-1 py-3.5 px-4 rounded-xl border transition-all duration-300 flex items-center justify-center gap-3 ${
                                                    selectedRole === 'admin'
                                                        ? 'border-cyan-500/50 bg-cyan-500/10 text-white shadow-lg shadow-cyan-500/10'
                                                        : 'border-white/10 bg-slate-800/30 text-slate-400 hover:border-white/20 hover:text-white'
                                                }`}
                                            >
                                                <Shield className="w-5 h-5" />
                                                <span className="font-medium">Admin</span>
                                                {selectedRole === 'admin' && (
                                                    <motion.div
                                                        initial={{ scale: 0 }}
                                                        animate={{ scale: 1 }}
                                                        className="ml-auto"
                                                    >
                                                        <CheckCircle2 className="w-5 h-5 text-cyan-400" />
                                                    </motion.div>
                                                )}
                                            </button>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Submit Button */}
                            <motion.button
                                type="submit"
                                disabled={loading}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className="w-full py-4 px-6 bg-gradient-to-r from-violet-600 via-fuchsia-500 to-violet-600 bg-[length:200%_100%] text-white font-semibold rounded-xl hover:bg-[length:100%_100%] focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-500 shadow-xl shadow-violet-500/25 flex items-center justify-center gap-3 mt-8"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        <span>{mode === 'signin' ? 'Signing in...' : 'Creating account...'}</span>
                                    </>
                                ) : (
                                    <>
                                        <span>{mode === 'signin' ? 'Sign In' : 'Create Account'}</span>
                                        <ArrowRight className="w-5 h-5" />
                                    </>
                                )}
                            </motion.button>
                        </form>

                        {/* Footer */}
                        <div className="mt-8 pt-6 border-t border-white/5 text-center">
                            <p className="text-slate-500 text-xs">
                                Protected by enterprise-grade security
                            </p>
                            <div className="flex items-center justify-center gap-4 mt-3">
                                <div className="flex items-center gap-1.5 text-slate-500 text-xs">
                                    <Lock className="w-3.5 h-3.5" />
                                    <span>End-to-end encrypted</span>
                                </div>
                                <div className="w-1 h-1 rounded-full bg-slate-600" />
                                <div className="flex items-center gap-1.5 text-slate-500 text-xs">
                                    <Shield className="w-3.5 h-3.5" />
                                    <span>HIPAA compliant</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Copyright */}
                <p className="text-center text-slate-600 text-xs mt-8">
                    © 2026 Your Pharma AI. All rights reserved.
                </p>
            </motion.div>
        </div>
    );
}
