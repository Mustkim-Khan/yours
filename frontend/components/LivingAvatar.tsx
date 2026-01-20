import React from 'react';
import { User, Mic, BrainCircuit, CheckCircle2 } from 'lucide-react';

export type AvatarState = 'idle' | 'listening' | 'thinking' | 'confident';

interface LivingAvatarProps {
    state: AvatarState;
    className?: string;
    size?: 'sm' | 'md' | 'lg';
}

export default function LivingAvatar({ state, className = '', size = 'md' }: LivingAvatarProps) {

    // State-based visuals
    const getStateConfig = () => {
        switch (state) {
            case 'listening':
                return {
                    borderColor: 'border-indigo-500',
                    shadowColor: 'shadow-indigo-500/50',
                    icon: <Mic className="w-5 h-5 text-indigo-100 animate-pulse" />,
                    bg: 'bg-indigo-600',
                    ring: 'ring-indigo-400',
                    animation: 'animate-pulse' // Pulsing efffect
                };
            case 'thinking':
                return {
                    borderColor: 'border-amber-500',
                    shadowColor: 'shadow-amber-500/50',
                    icon: <BrainCircuit className="w-5 h-5 text-amber-100 animate-spin-slow" />,
                    bg: 'bg-amber-600',
                    ring: 'ring-amber-400',
                    animation: 'animate-pulse' // Gentle pulse for thinking
                };
            case 'confident':
                return {
                    borderColor: 'border-emerald-500',
                    shadowColor: 'shadow-emerald-500/50',
                    icon: <CheckCircle2 className="w-5 h-5 text-emerald-100" />,
                    bg: 'bg-emerald-600',
                    ring: 'ring-emerald-400',
                    animation: 'animate-bounce-short' // Short bounce/nod
                };
            case 'idle':
            default:
                return {
                    borderColor: 'border-gray-200 dark:border-gray-700',
                    shadowColor: 'shadow-transparent',
                    icon: <User className="w-5 h-5 text-gray-400 dark:text-gray-300" />,
                    bg: 'bg-gray-100 dark:bg-gray-800',
                    ring: 'ring-transparent',
                    animation: 'animate-breathe' // Subtle breathing
                };
        }
    };

    const config = getStateConfig();

    const sizeClasses = {
        sm: 'w-10 h-10',
        md: 'w-16 h-16',
        lg: 'w-24 h-24'
    };

    // We use a professional "Pharmacist" style avatar as the base
    // But overlay state indicators
    return (
        <div className={`relative ${className}`}>
            {/* Main Avatar Container with Status Ring */}
            <div
                className={`
                    ${sizeClasses[size]} rounded-full overflow-hidden 
                    border-4 transition-all duration-500 ease-in-out
                    flex items-center justify-center
                    ${config.borderColor} ${config.bg}
                    ${state === 'listening' ? 'ring-4 ring-opacity-30 ' + config.ring : ''}
                    shadow-lg ${config.shadowColor}
                `}
            >
                {/* Fallback Icon or Image */}
                {/* Ideally we would have a real image here, but for now we use the icon/color state to represent the "System" */}
                <div className="absolute inset-0 flex items-center justify-center">
                    {config.icon}
                </div>

                {/* Ripple Effect for Listening */}
                {state === 'listening' && (
                    <>
                        <span className="absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-20 animate-ping"></span>
                    </>
                )}
            </div>

            {/* Status Badge (Bottom Right) */}
            <div className={`
                absolute -bottom-1 -right-1 
                px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider text-white
                transition-all duration-300 transform
                ${state === 'idle' ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}
                ${config.bg}
            `}>
                {state}
            </div>
        </div>
    );
}
