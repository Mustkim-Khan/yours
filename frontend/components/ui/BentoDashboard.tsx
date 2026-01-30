'use client';

import { motion } from 'framer-motion';
import {
    Brain,
    Minus,
    RefreshCw,
    ShieldAlert,
    TrendingDown,
    TrendingUp,
    Users
} from 'lucide-react';

interface BentoCardData {
    id: string;
    title: string;
    value: string | number;
    label: string;
    trend: 'up' | 'down' | 'neutral';
    trendValue: string;
    icon: React.ReactNode;
    accentColor: 'amber' | 'blue' | 'red' | 'purple' | 'emerald';
    span?: number;
    isUrgent?: boolean;
}

interface BentoDashboardProps {
    aiConfidence: number;
    activeRefills: number;
    safetyAlerts: number;
    patientLoad: number;
    avgProcessingTime?: string;
}

const accentColors = {
    amber: {
        bg: 'bg-amber-500/10 dark:bg-amber-500/20',
        border: 'border-amber-500/30',
        icon: 'text-amber-500',
        gradient: 'from-amber-500/20 to-transparent',
    },
    blue: {
        bg: 'bg-blue-500/10 dark:bg-blue-500/20',
        border: 'border-blue-500/30',
        icon: 'text-blue-500',
        gradient: 'from-blue-500/20 to-transparent',
    },
    red: {
        bg: 'bg-red-500/10 dark:bg-red-500/20',
        border: 'border-red-500/30',
        icon: 'text-red-500',
        gradient: 'from-red-500/20 to-transparent',
    },
    purple: {
        bg: 'bg-purple-500/10 dark:bg-purple-500/20',
        border: 'border-purple-500/30',
        icon: 'text-purple-500',
        gradient: 'from-purple-500/20 to-transparent',
    },
    emerald: {
        bg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
        border: 'border-emerald-500/30',
        icon: 'text-emerald-500',
        gradient: 'from-emerald-500/20 to-transparent',
    },
};

function TrendIndicator({ trend, value }: { trend: 'up' | 'down' | 'neutral'; value: string }) {
    const icons = {
        up: <TrendingUp className="w-3 h-3" />,
        down: <TrendingDown className="w-3 h-3" />,
        neutral: <Minus className="w-3 h-3" />,
    };

    const colors = {
        up: 'text-emerald-500',
        down: 'text-red-500',
        neutral: 'text-gray-500',
    };

    return (
        <span className={`flex items-center gap-1 text-xs font-medium ${colors[trend]}`}>
            {icons[trend]}
            {value}
        </span>
    );
}

function BentoCard({ card }: { card: BentoCardData }) {
    const colors = accentColors[card.accentColor];

    return (
        <motion.div
            className={`relative overflow-hidden rounded-2xl p-6 
                bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm
                border border-gray-200/50 dark:border-gray-700/50
                transition-all duration-300 cursor-default
                hover:scale-[1.02] hover:shadow-xl
                ${card.span === 2 ? 'col-span-2' : 'col-span-1'}
                ${card.isUrgent ? 'ring-2 ring-red-500/50 ring-offset-2 ring-offset-gray-50 dark:ring-offset-gray-950' : ''}
            `}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ y: -2 }}
            transition={{ duration: 0.3 }}
            role="article"
            aria-label={`${card.title}: ${card.value} ${card.label}`}
        >
            {/* Corner Gradient Reveal on Hover */}
            <div 
                className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl ${colors.gradient} opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none`}
            />

            {/* Urgent Pulse Animation */}
            {card.isUrgent && (
                <motion.div
                    className="absolute top-4 right-4 w-3 h-3 rounded-full bg-red-500"
                    animate={{ scale: [1, 1.2, 1], opacity: [1, 0.7, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    aria-label="Urgent attention required"
                />
            )}

            {/* Icon */}
            <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl ${colors.bg} ${colors.border} border mb-4`}>
                <span className={colors.icon}>{card.icon}</span>
            </div>

            {/* Value */}
            <div className="flex items-baseline gap-2 mb-1">
                <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    {card.value}
                </span>
                <TrendIndicator trend={card.trend} value={card.trendValue} />
            </div>

            {/* Label */}
            <p className="text-sm text-gray-600 dark:text-gray-400">
                {card.label}
            </p>

            {/* Title */}
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider mt-3">
                {card.title}
            </h3>
        </motion.div>
    );
}

/**
 * BentoGridDashboard - Admin analytics overview
 * 3-column grid with glassmorphic cards
 * Each card has unique accent colors and hover effects
 */
export default function BentoDashboard({
    aiConfidence,
    activeRefills,
    safetyAlerts,
    patientLoad,
    avgProcessingTime = '2.3s'
}: BentoDashboardProps) {
    const cards: BentoCardData[] = [
        {
            id: 'ai-confidence',
            title: 'AI Confidence',
            value: `${aiConfidence}%`,
            label: 'Average decision confidence across all agents',
            trend: aiConfidence >= 90 ? 'up' : aiConfidence >= 75 ? 'neutral' : 'down',
            trendValue: aiConfidence >= 90 ? 'Excellent' : aiConfidence >= 75 ? 'Good' : 'Review needed',
            icon: <Brain className="w-6 h-6" />,
            accentColor: 'purple',
            span: 2,
        },
        {
            id: 'active-refills',
            title: 'Active Refills',
            value: activeRefills,
            label: 'Pending refill requests',
            trend: 'up',
            trendValue: '+12%',
            icon: <RefreshCw className="w-6 h-6" />,
            accentColor: 'blue',
        },
        {
            id: 'safety-alerts',
            title: 'Safety Alerts',
            value: safetyAlerts,
            label: 'Drug interactions detected',
            trend: safetyAlerts > 0 ? 'up' : 'neutral',
            trendValue: safetyAlerts > 0 ? 'Action needed' : 'All clear',
            icon: <ShieldAlert className="w-6 h-6" />,
            accentColor: 'red',
            isUrgent: safetyAlerts > 0,
        },
        {
            id: 'patient-load',
            title: 'Patient Load',
            value: patientLoad,
            label: 'Active patients today',
            trend: 'up',
            trendValue: '+8%',
            icon: <Users className="w-6 h-6" />,
            accentColor: 'emerald',
        },
        {
            id: 'processing-time',
            title: 'Avg Processing',
            value: avgProcessingTime,
            label: 'Order to confirmation time',
            trend: 'down',
            trendValue: '-15%',
            icon: <TrendingDown className="w-6 h-6" />,
            accentColor: 'amber',
        },
    ];

    return (
        <div 
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4"
            role="region"
            aria-label="Admin Dashboard Analytics"
        >
            {cards.map((card) => (
                <BentoCard key={card.id} card={card} />
            ))}
        </div>
    );
}
