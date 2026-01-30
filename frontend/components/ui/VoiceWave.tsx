'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useCallback, useEffect, useRef } from 'react';

interface VoiceWaveProps {
    isListening: boolean;
    subtitle?: string;
}

/**
 * VoiceWaveVisualizer - Real-time voice input feedback
 * Canvas-based animated bars simulating audio visualization
 * Apple Health meets clinical precision aesthetic
 */
export default function VoiceWave({ 
    isListening, 
    subtitle = "Listening to your symptoms..." 
}: VoiceWaveProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<number>(0);
    const barsRef = useRef<number[]>(Array(20).fill(0.3));

    const animate = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const { width, height } = canvas;
        ctx.clearRect(0, 0, width, height);

        const barCount = 20;
        const barWidth = (width - (barCount - 1) * 4) / barCount;
        const maxBarHeight = height * 0.8;

        // Create gradient
        const gradient = ctx.createLinearGradient(0, height, 0, 0);
        gradient.addColorStop(0, '#6366f1'); // Indigo-500
        gradient.addColorStop(1, '#9333ea'); // Purple-600

        // Update bar heights with smooth animation
        barsRef.current = barsRef.current.map((currentHeight) => {
            const targetHeight = 0.2 + Math.random() * 0.8;
            return currentHeight + (targetHeight - currentHeight) * 0.15;
        });

        // Draw bars
        barsRef.current.forEach((heightPercent, index) => {
            const x = index * (barWidth + 4);
            const barHeight = heightPercent * maxBarHeight;
            const y = (height - barHeight) / 2;

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.roundRect(x, y, barWidth, barHeight, 4);
            ctx.fill();
        });

        animationRef.current = requestAnimationFrame(animate);
    }, []);

    useEffect(() => {
        if (isListening) {
            // Check for reduced motion preference
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (!prefersReducedMotion) {
                animate();
            }
        }

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [isListening, animate]);

    // Handle canvas resize
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const resizeCanvas = () => {
            const container = canvas.parentElement;
            if (container) {
                canvas.width = container.clientWidth - 48; // Account for padding
                canvas.height = 60;
            }
        };

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        return () => window.removeEventListener('resize', resizeCanvas);
    }, []);

    return (
        <AnimatePresence>
            {isListening && (
                <motion.div
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.98 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    className="absolute bottom-24 left-1/2 -translate-x-1/2 z-20 w-[90%] max-w-md"
                    role="status"
                    aria-live="polite"
                    aria-label="Voice input active"
                >
                    <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-md rounded-2xl border border-gray-200/50 dark:border-gray-700/50 shadow-xl p-6">
                        {/* Canvas Visualization */}
                        <canvas 
                            ref={canvasRef}
                            className="w-full h-[60px] rounded-lg"
                            aria-hidden="true"
                        />

                        {/* Subtitle with pulsing animation */}
                        <motion.p
                            animate={{ opacity: [0.6, 1, 0.6] }}
                            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                            className="mt-4 text-center text-sm font-medium text-indigo-600 dark:text-indigo-400"
                        >
                            <span className="inline-flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                {subtitle}
                            </span>
                        </motion.p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
