'use client';

import { motion, useScroll, useTransform } from 'framer-motion';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import {
    ArrowRight,
    Award,
    BookOpen,
    Building2,
    ChevronDown,
    Cpu,
    Database,
    FileCheck,
    Lock,
    MessageSquare,
    Package,
    Shield,
    Sparkles,
    Stethoscope,
    User
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

import ArchitectureDiagram from '@/components/landing/ArchitectureDiagram';
import FeatureSection from '@/components/landing/FeatureSection';
import MedicineLine from '@/components/landing/MedicineLine';

// Register GSAP plugins
if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

// ============================================
// ARCHITECTURE NOTE:
// This landing page lives at app/landing/page.tsx
// Isolated from the core app for clean separation
// of marketing vs application concerns.
// ============================================

// Feature Visual Components
const ConversationalOrderingVisual = () => (
  <div className="space-y-4">
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.2 }}
      className="flex items-start gap-3"
    >
      <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center flex-shrink-0">
        <span className="text-cyan-400 text-sm">👤</span>
      </div>
      <div className="bg-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3 max-w-xs">
        <p className="text-slate-300 text-sm">I need my usual blood pressure medication</p>
      </div>
    </motion.div>
    
    <motion.div 
      initial={{ opacity: 0, x: 20 }}
      whileInView={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.5 }}
      className="flex items-start gap-3 justify-end"
    >
      <div className="bg-gradient-to-r from-violet-500/20 to-indigo-500/20 border border-violet-500/30 rounded-2xl rounded-tr-sm px-4 py-3 max-w-xs">
        <p className="text-slate-200 text-sm">I found Amlodipine 5mg in your history. Would you like me to prepare a refill order?</p>
      </div>
      <div className="w-8 h-8 rounded-full bg-violet-500/20 flex items-center justify-center flex-shrink-0">
        <Sparkles className="w-4 h-4 text-violet-400" />
      </div>
    </motion.div>
    
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.8 }}
      className="mt-6 p-4 rounded-xl bg-slate-800/80 border border-slate-600/50"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500 uppercase tracking-wider">Order Preview</span>
        <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full">Ready</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center">
          <Package className="w-5 h-5 text-violet-400" />
        </div>
        <div>
          <p className="text-white font-medium text-sm">Amlodipine 5mg</p>
          <p className="text-slate-400 text-xs">30 tablets · Monthly refill</p>
        </div>
      </div>
    </motion.div>
  </div>
);

const MedicineCabinetVisual = () => (
  <div className="grid grid-cols-2 gap-4">
    {[
      { name: 'Metformin', qty: '60 tablets', status: 'good', icon: '💊' },
      { name: 'Lisinopril', qty: '28 tablets', status: 'low', icon: '💉' },
      { name: 'Paracetamol', qty: '12 tablets', status: 'expiring', icon: '🩹' },
      { name: 'Vitamin D', qty: '90 capsules', status: 'good', icon: '☀️' },
    ].map((med, index) => (
      <motion.div
        key={med.name}
        initial={{ opacity: 0, y: 30, rotateX: -15 }}
        whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ delay: index * 0.15, duration: 0.5 }}
        whileHover={{ scale: 1.05, y: -5 }}
        className={`
          p-4 rounded-xl border backdrop-blur-sm cursor-pointer transition-all
          ${med.status === 'good' ? 'bg-slate-800/50 border-slate-600/50' :
            med.status === 'low' ? 'bg-amber-500/10 border-amber-500/30' :
            'bg-rose-500/10 border-rose-500/30'}
        `}
      >
        <div className="text-2xl mb-2">{med.icon}</div>
        <p className="text-white font-medium text-sm">{med.name}</p>
        <p className="text-slate-400 text-xs">{med.qty}</p>
        {med.status === 'expiring' && (
          <span className="text-xs text-rose-400 mt-2 block">Expires soon</span>
        )}
        {med.status === 'low' && (
          <span className="text-xs text-amber-400 mt-2 block">Running low</span>
        )}
      </motion.div>
    ))}
  </div>
);

const ExplainMedicineVisual = () => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    whileInView={{ opacity: 1, scale: 1 }}
    className="space-y-4"
  >
    <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-600/50">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-cyan-500/20 flex items-center justify-center">
          <span className="text-2xl">💊</span>
        </div>
        <div>
          <p className="text-white font-semibold">Metformin 500mg</p>
          <p className="text-slate-400 text-sm">Anti-diabetic medication</p>
        </div>
      </div>
      
      <motion.div 
        initial={{ height: 0, opacity: 0 }}
        whileInView={{ height: 'auto', opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="space-y-3 overflow-hidden"
      >
        <div className="p-3 rounded-lg bg-slate-700/50">
          <div className="flex items-center gap-2 mb-1">
            <BookOpen className="w-4 h-4 text-cyan-400" />
            <span className="text-cyan-400 text-xs font-medium">How it works</span>
          </div>
          <p className="text-slate-300 text-sm">Helps control blood sugar levels by reducing glucose production in the liver.</p>
        </div>
        
        <div className="p-3 rounded-lg bg-slate-700/50">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-amber-400 text-xs">⏰</span>
            <span className="text-amber-400 text-xs font-medium">Best time to take</span>
          </div>
          <p className="text-slate-300 text-sm">With meals to reduce stomach upset.</p>
        </div>
      </motion.div>
    </div>
  </motion.div>
);

const PrescriptionAwareVisual = () => (
  <div className="space-y-4">
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-slate-800/80 border border-slate-600/50"
    >
      <div className="flex items-center gap-3 mb-4">
        <FileCheck className="w-5 h-5 text-slate-400" />
        <span className="text-slate-400 text-sm">Prescription Analysis</span>
      </div>
      
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-violet-500/20 to-cyan-500/20 rounded-lg animate-pulse" />
        <div className="relative p-4 rounded-lg border border-dashed border-slate-500/50">
          <div className="space-y-2">
            <div className="h-2 bg-slate-600/50 rounded w-3/4" />
            <div className="h-2 bg-slate-600/50 rounded w-1/2" />
            <div className="h-2 bg-slate-600/50 rounded w-2/3" />
          </div>
        </div>
      </div>
    </motion.div>
    
    <motion.div
      initial={{ opacity: 0, scale: 0 }}
      whileInView={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.5, type: 'spring' }}
      className="flex items-center justify-center gap-3"
    >
      <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center">
        <motion.div
          initial={{ scale: 0 }}
          whileInView={{ scale: 1 }}
          transition={{ delay: 0.7, type: 'spring' }}
        >
          <Shield className="w-6 h-6 text-emerald-400" />
        </motion.div>
      </div>
      <div>
        <p className="text-emerald-400 font-medium">Prescription Verified</p>
        <p className="text-slate-400 text-xs">Valid until Dec 2026</p>
      </div>
    </motion.div>
  </div>
);

// Comparison data
const comparisonData = [
  { others: 'Order medicines', ours: 'Understands your health context' },
  { others: 'Static descriptions', ours: 'Contextual AI explanations' },
  { others: 'Purchase history', ours: 'Living medicine intelligence' },
  { others: 'Manual refill reminders', ours: 'Proactive health assistance' },
];

// Audience data
const audienceData = [
  { 
    icon: User, 
    title: 'For Patients', 
    description: 'Manage medications effortlessly with conversational AI that understands your needs.' 
  },
  { 
    icon: Stethoscope, 
    title: 'For Pharmacists', 
    description: 'Augment your practice with AI that handles routine queries and order preparation.' 
  },
  { 
    icon: Building2, 
    title: 'For Healthcare Systems', 
    description: 'Scale pharmacy services with intelligent automation and compliance built-in.' 
  },
];

// Smart CTA Component with auth-awareness
// CTA Behavior:
// - Authenticated user → redirects to /chat (main app)
// - Unauthenticated user → redirects to /login
// For this demo, we link to "/" which handles auth routing
const SmartCTA = ({ 
  children, 
  className = '',
  size = 'default'
}: { 
  children: React.ReactNode; 
  className?: string;
  size?: 'default' | 'large';
}) => {
  // In production, this would check auth state
  // const { user } = useAuth();
  // const href = user ? '/' : '/login';
  const href = '/'; // Main app handles auth routing
  
  const sizeClasses = size === 'large' 
    ? 'px-10 py-5 text-xl' 
    : 'px-8 py-4 text-lg';

  return (
    <Link
      href={href}
      className={`group inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-500 to-cyan-500 text-white font-medium hover:shadow-lg hover:shadow-violet-500/25 transition-all hover:scale-105 ${sizeClasses} ${className}`}
    >
      {children}
    </Link>
  );
};

export default function LandingPage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.2], [1, 0.95]);
  
  // Check for reduced motion preference
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Smooth scroll to section
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    }
  };

  return (
    <main className="bg-slate-950 text-white min-h-screen overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-semibold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              Your Pharma AI
            </span>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="hidden md:flex items-center gap-8"
          >
            <button 
              onClick={() => scrollToSection('features')}
              className="text-slate-400 hover:text-white transition-colors text-sm"
            >
              Features
            </button>
            <button 
              onClick={() => scrollToSection('audience')}
              className="text-slate-400 hover:text-white transition-colors text-sm"
            >
              Who It's For
            </button>
            <button 
              onClick={() => scrollToSection('architecture')}
              className="text-slate-400 hover:text-white transition-colors text-sm"
            >
              Technology
            </button>
            <button 
              onClick={() => scrollToSection('security')}
              className="text-slate-400 hover:text-white transition-colors text-sm"
            >
              Security
            </button>
            <Link 
              href="/"
              className="px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white text-sm font-medium transition-all hover:scale-105"
            >
              Launch App
            </Link>
          </motion.div>
        </div>
      </nav>

      {/* Hero Section */}
      <section 
        ref={heroRef}
        className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24"
      >
        {/* Background Effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-500/20 rounded-full blur-[128px]" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[128px]" />
        </div>

        {/* Content - Split Layout */}
        <div className="relative z-10 max-w-7xl mx-auto w-full">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left - Text Content */}
            <div className="text-center lg:text-left">
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
              >
                <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-sm mb-8">
                  <Sparkles className="w-4 h-4" />
                  AI-Powered Healthcare
                </span>
              </motion.div>

              <motion.h1 
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-semibold leading-tight mb-8"
              >
                <span className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  Your Intelligent Pharmacy,
                </span>
                <br />
                <span className="bg-gradient-to-r from-violet-400 via-cyan-400 to-violet-400 bg-clip-text text-transparent">
                  Reimagined
                </span>
              </motion.h1>

              <motion.p 
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="text-lg md:text-xl lg:text-2xl text-slate-400 max-w-xl mx-auto lg:mx-0 mb-10 leading-relaxed"
              >
                Conversational AI that understands prescriptions, manages medicines,
                and assists patients like a real pharmacist.
              </motion.p>

              <motion.div 
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="flex flex-col sm:flex-row items-center lg:items-start justify-center lg:justify-start gap-4"
              >
                <SmartCTA>
                  Start Conversation
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </SmartCTA>
                <button
                  onClick={() => scrollToSection('features')}
                  className="px-8 py-4 rounded-full bg-white/5 border border-white/10 text-white font-medium text-lg hover:bg-white/10 transition-all flex items-center gap-2"
                >
                  View How It Works
                  <ChevronDown className="w-5 h-5" />
                </button>
              </motion.div>
            </div>

            {/* Right - Hero Image */}
            <motion.div
              initial={{ opacity: 0, x: 50, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              transition={{ duration: 1, delay: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="relative flex justify-center lg:justify-end"
            >
              <div className="relative">
                {/* Glow effect behind image */}
                <div className="absolute -inset-4 bg-gradient-to-r from-violet-500/30 to-cyan-500/30 rounded-3xl blur-2xl opacity-60" />
                
                {/* Image container with premium styling */}
                <div className="relative rounded-3xl overflow-hidden border border-white/10 shadow-2xl shadow-violet-500/10">
                  <img 
                    src="/hero-pharmacist.png" 
                    alt="AI-powered pharmacy assistant"
                    className="w-full max-w-md lg:max-w-lg xl:max-w-xl h-auto object-cover"
                  />
                  
                  {/* Overlay gradient */}
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-transparent" />
                  
                  {/* Floating badge */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1, duration: 0.6 }}
                    className="absolute bottom-4 left-4 right-4 p-4 rounded-xl bg-slate-900/80 backdrop-blur-md border border-white/10"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="text-white font-medium text-sm">AI Assistant Ready</p>
                        <p className="text-slate-400 text-xs">Intelligent pharmacy support 24/7</p>
                      </div>
                    </div>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        {/* Medicine Line Animation - respects reduced motion */}
        {!prefersReducedMotion && (
          <div className="absolute bottom-0 left-0 right-0">
            <MedicineLine speed={40} opacity={0.4} />
          </div>
        )}

        {/* Scroll indicator */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={prefersReducedMotion ? {} : { y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center p-2"
          >
            <motion.div 
              animate={prefersReducedMotion ? {} : { opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-1 h-2 bg-white/50 rounded-full" 
            />
          </motion.div>
        </motion.div>
      </section>

      {/* Social Proof Strip */}
      <section className="relative py-16 px-6 border-y border-slate-800">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-center gap-8 md:gap-16">
            {[
              { icon: Shield, label: 'Built for modern healthcare' },
              { icon: Lock, label: 'Designed for safety' },
              { icon: Cpu, label: 'Powered by AI' },
            ].map((item, index) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center gap-3 text-slate-400"
              >
                <item.icon className="w-5 h-5 text-violet-400" />
                <span className="text-sm font-medium">{item.label}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-center mb-20"
          >
            <span className="text-violet-400 text-sm font-medium tracking-wider uppercase mb-4 block">
              Capabilities
            </span>
            <h2 className="text-4xl md:text-5xl font-semibold text-white mb-6">
              Intelligent by Design
            </h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Every feature is crafted to deliver pharmacy-grade assistance with AI precision.
            </p>
          </motion.div>

          <FeatureSection
            index={0}
            title="Conversational Ordering"
            description="Users speak or type naturally. The AI understands intent and converts conversation into structured medical orders—no forms, no friction."
            visual={<ConversationalOrderingVisual />}
          />

          <FeatureSection
            index={1}
            title="Digital Medicine Cabinet"
            description="Tracks what patients already have at home. Prevents duplicate purchases and monitors expiry dates intelligently."
            visual={<MedicineCabinetVisual />}
            reversed
          />

          <FeatureSection
            index={2}
            title="Explain My Medicine"
            description="AI explains medicines like a real pharmacist—contextual, safe, and non-diagnostic. Understand your medications better."
            visual={<ExplainMedicineVisual />}
          />

          <FeatureSection
            index={3}
            title="Prescription-Aware AI"
            description="Understands prescriptions, validates medicines, and assists without overriding doctors. Healthcare-compliant by design."
            visual={<PrescriptionAwareVisual />}
            reversed
          />
        </div>
      </section>

      {/* Who This Is For Section */}
      <section id="audience" className="relative py-24 px-6 bg-slate-900/50">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-center mb-16"
          >
            <span className="text-emerald-400 text-sm font-medium tracking-wider uppercase mb-4 block">
              Designed For
            </span>
            <h2 className="text-4xl md:text-5xl font-semibold text-white mb-6">
              Who This Is For
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {audienceData.map((item, index) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.15 }}
                className="p-8 rounded-2xl bg-slate-800/50 border border-slate-700/50 text-center hover:border-violet-500/30 transition-colors"
              >
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500/20 to-cyan-500/20 flex items-center justify-center mx-auto mb-6">
                  <item.icon className="w-8 h-8 text-violet-400" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{item.title}</h3>
                <p className="text-slate-400">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section id="architecture" className="relative py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-center mb-16"
          >
            <span className="text-cyan-400 text-sm font-medium tracking-wider uppercase mb-4 block">
              Architecture
            </span>
            <h2 className="text-4xl md:text-5xl font-semibold text-white mb-6">
              Built Like a Real System—<br />Not a Demo
            </h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-4">
              Agentic AI architecture with secure data handling, persistent conversations, and real-time inventory awareness.
            </p>
            {/* Clarification note for technical reviewers */}
            <p className="text-sm text-slate-500 italic">
              Diagram is illustrative—meant to communicate system intelligence, not implementation specifics.
            </p>
          </motion.div>

          <ArchitectureDiagram />

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-16">
            {[
              { icon: Cpu, label: 'Agentic AI', desc: 'Multi-agent orchestration' },
              { icon: Lock, label: 'Secure', desc: 'End-to-end encryption' },
              { icon: MessageSquare, label: 'Persistent', desc: 'Conversation memory' },
              { icon: Database, label: 'Real-time', desc: 'Inventory sync' },
            ].map((item, index) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 text-center"
              >
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-cyan-500/20 flex items-center justify-center mx-auto mb-4">
                  <item.icon className="w-6 h-6 text-violet-400" />
                </div>
                <p className="text-white font-medium mb-1">{item.label}</p>
                <p className="text-slate-400 text-sm">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Different Section */}
      <section className="relative py-24 px-6 bg-slate-900/50">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-semibold text-white mb-6">
              Why This Is Different
            </h2>
          </motion.div>

          <div className="space-y-4">
            {comparisonData.map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center gap-6 p-6 rounded-xl bg-slate-800/30 border border-slate-700/30"
              >
                <div className="flex-1">
                  <span className="text-slate-500 text-sm">Others:</span>
                  <p className="text-slate-400">{item.others}</p>
                </div>
                <ArrowRight className="w-5 h-5 text-violet-400 flex-shrink-0" />
                <div className="flex-1">
                  <span className="text-violet-400 text-sm">This:</span>
                  <p className="text-white font-medium">{item.ours}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className="relative py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-4xl md:text-5xl font-semibold text-white mb-8">
              Security & Responsibility
            </h2>
            <p className="text-xl text-slate-400 mb-12">
              Healthcare-grade safety. Always.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: Shield, label: 'Informational AI', desc: 'Never provides medical diagnosis' },
              { icon: FileCheck, label: 'Prescription-Respecting', desc: 'Validates doctor prescriptions' },
              { icon: Award, label: 'Safety-First', desc: 'Designed for healthcare compliance' },
            ].map((item, index) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="p-8 rounded-2xl bg-slate-800/50 border border-slate-700/50"
              >
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center mx-auto mb-6">
                  <item.icon className="w-7 h-7 text-emerald-400" />
                </div>
                <p className="text-white font-semibold text-lg mb-2">{item.label}</p>
                <p className="text-slate-400">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="relative py-32 px-6 overflow-hidden bg-slate-900/50">
        {/* Background Effects */}
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[128px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[128px]" />
        </div>

        {/* Medicine Line at top - respects reduced motion */}
        {!prefersReducedMotion && (
          <div className="absolute top-0 left-0 right-0">
            <MedicineLine direction="right" speed={50} opacity={0.3} />
          </div>
        )}

        <div className="relative z-10 max-w-3xl mx-auto text-center">
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-5xl lg:text-6xl font-semibold text-white mb-8"
          >
            Experience a smarter way to manage medicines.
          </motion.h2>
          
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <SmartCTA size="large" className="font-semibold">
              Start a Conversation
              <ArrowRight className="w-6 h-6" />
            </SmartCTA>
          </motion.div>
        </div>

        {/* Medicine Line at bottom - respects reduced motion */}
        {!prefersReducedMotion && (
          <div className="absolute bottom-0 left-0 right-0">
            <MedicineLine speed={45} opacity={0.3} />
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="relative py-16 px-6 border-t border-slate-800 bg-slate-950">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <span className="text-lg font-semibold text-white">Your Pharma AI</span>
              </div>
              <p className="text-slate-400 text-sm">
                Intelligent pharmacy assistance for modern healthcare.
              </p>
            </div>

            <div>
              <h4 className="text-white font-medium mb-4">Product</h4>
              <ul className="space-y-2">
                <li><button onClick={() => scrollToSection('features')} className="text-slate-400 hover:text-white text-sm transition-colors">Features</button></li>
                <li><button onClick={() => scrollToSection('audience')} className="text-slate-400 hover:text-white text-sm transition-colors">Who It's For</button></li>
                <li><Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">Launch App</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-medium mb-4">Technology</h4>
              <ul className="space-y-2">
                <li><button onClick={() => scrollToSection('architecture')} className="text-slate-400 hover:text-white text-sm transition-colors">Architecture</button></li>
                <li><button onClick={() => scrollToSection('security')} className="text-slate-400 hover:text-white text-sm transition-colors">Security</button></li>
                <li><span className="text-slate-400 text-sm">API (Coming Soon)</span></li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-medium mb-4">Legal</h4>
              <ul className="space-y-2">
                <li><span className="text-slate-400 text-sm">Privacy Policy</span></li>
                <li><span className="text-slate-400 text-sm">Terms of Service</span></li>
                <li><span className="text-slate-400 text-sm">Medical Disclaimer</span></li>
              </ul>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-slate-500 text-sm">
              © 2026 Your Pharma AI. All rights reserved.
            </p>
            <p className="text-slate-500 text-sm">
              Built with ❤️ for better healthcare
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
