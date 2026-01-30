'use client';

import { motion } from 'framer-motion';
import { AlertTriangle, ChevronRight, Pill } from 'lucide-react';
import { useCallback, useRef, useState } from 'react';

interface HolographicCardProps {
    medicineName: string;
    strength: string;
    interactionWarning?: string;
    onViewInteractions?: () => void;
}

/**
 * HolographicMedicineCard - 3D interactive medicine display
 * CSS 3D transforms with mouse-tracking tilt effect
 * Futuristic glassmorphic design with mesh gradient background
 */
export default function HolographicCard({
    medicineName,
    strength,
    interactionWarning,
    onViewInteractions
}: HolographicCardProps) {
    const cardRef = useRef<HTMLDivElement>(null);
    const [transform, setTransform] = useState({ rotateX: 0, rotateY: 0 });
    const [glarePosition, setGlarePosition] = useState({ x: 50, y: 50 });
    const [isHovered, setIsHovered] = useState(false);

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (!cardRef.current) return;

        const rect = cardRef.current.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        const mouseX = e.clientX - centerX;
        const mouseY = e.clientY - centerY;

        // Calculate rotation (max 15 degrees)
        const rotateY = (mouseX / (rect.width / 2)) * 15;
        const rotateX = -(mouseY / (rect.height / 2)) * 15;

        setTransform({ rotateX, rotateY });

        // Calculate glare position (0-100%)
        const glareX = ((e.clientX - rect.left) / rect.width) * 100;
        const glareY = ((e.clientY - rect.top) / rect.height) * 100;
        setGlarePosition({ x: glareX, y: glareY });
    }, []);

    const handleMouseLeave = useCallback(() => {
        setIsHovered(false);
        setTransform({ rotateX: 0, rotateY: 0 });
        setGlarePosition({ x: 50, y: 50 });
    }, []);

    return (
        <motion.div
            ref={cardRef}
            className="relative w-full max-w-sm perspective-1000"
            onMouseMove={handleMouseMove}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={handleMouseLeave}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <motion.div
                className="relative overflow-hidden rounded-2xl bg-gray-900 dark:bg-gray-950 p-6 border border-gray-700/50"
                animate={{
                    rotateX: transform.rotateX,
                    rotateY: transform.rotateY,
                    scale: isHovered ? 1.02 : 1,
                }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                style={{ transformStyle: 'preserve-3d' }}
                role="article"
                aria-label={`Medicine card for ${medicineName}`}
            >
                {/* Animated Mesh Gradient Background */}
                <div className="absolute inset-0 overflow-hidden">
                    <motion.div
                        className="absolute w-40 h-40 rounded-full bg-indigo-500/30 blur-3xl"
                        animate={{
                            x: [0, 100, 50, 0],
                            y: [0, 50, 100, 0],
                        }}
                        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                        style={{ top: '-20%', left: '-10%' }}
                    />
                    <motion.div
                        className="absolute w-32 h-32 rounded-full bg-purple-500/30 blur-3xl"
                        animate={{
                            x: [0, -80, -40, 0],
                            y: [0, 80, 40, 0],
                        }}
                        transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
                        style={{ bottom: '-15%', right: '-5%' }}
                    />
                </div>

                {/* Glare Overlay */}
                <div
                    className="absolute inset-0 pointer-events-none opacity-0 transition-opacity duration-300"
                    style={{
                        opacity: isHovered ? 0.15 : 0,
                        background: `radial-gradient(circle at ${glarePosition.x}% ${glarePosition.y}%, white, transparent 50%)`,
                    }}
                />

                {/* Content */}
                <div className="relative z-10">
                    {/* Medicine Icon with Glow */}
                    <div className="flex items-center justify-center w-16 h-16 mb-4 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30">
                        <Pill className="w-8 h-8 text-white" aria-hidden="true" />
                    </div>

                    {/* Medicine Name */}
                    <h3 className="text-xl font-bold text-white mb-1">
                        {medicineName}
                    </h3>

                    {/* Strength */}
                    <p className="text-gray-400 text-sm mb-4">
                        {strength}
                    </p>

                    {/* Interaction Warning Badge */}
                    {interactionWarning && (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 mb-4">
                            <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                            <span className="text-amber-400 text-xs font-medium">
                                {interactionWarning}
                            </span>
                        </div>
                    )}

                    {/* Glass Button */}
                    <button
                        onClick={onViewInteractions}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-medium transition-all duration-200 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900"
                        aria-label={`View interactions for ${medicineName}`}
                    >
                        <span>Tap to View Interactions</span>
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}
