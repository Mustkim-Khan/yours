'use client';

import confetti from 'canvas-confetti';
import { useCallback, useEffect, useRef } from 'react';

interface OrderCelebrationProps {
    orderStatus: 'PENDING' | 'CONFIRMED' | 'CANCELLED' | null;
    onComplete?: () => void;
}

/**
 * OrderCelebration - Dopamine feedback on successful order
 * Uses canvas-confetti for dual-origin explosion effect
 * Gold and Emerald color palette for premium feel
 */
export default function OrderCelebration({ 
    orderStatus, 
    onComplete 
}: OrderCelebrationProps) {
    const hasTriggeredRef = useRef(false);
    const animationFrameRef = useRef<number | null>(null);

    const fireConfetti = useCallback(() => {
        // Check for reduced motion preference
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            onComplete?.();
            return;
        }

        const duration = 3000;
        const animationEnd = Date.now() + duration;

        // Gold and Emerald color palette
        const colors = ['#F59E0B', '#FCD34D', '#10B981', '#34D399', '#FBBF24'];

        const frame = () => {
            const timeLeft = animationEnd - Date.now();

            if (timeLeft <= 0) {
                onComplete?.();
                return;
            }

            const particleCount = 3;

            // Left side explosion
            confetti({
                particleCount,
                angle: 60,
                spread: 55,
                origin: { x: 0, y: 0.6 },
                colors,
                ticks: 200,
                gravity: 0.8,
                scalar: 1.2,
                drift: 0.5,
            });

            // Right side explosion
            confetti({
                particleCount,
                angle: 120,
                spread: 55,
                origin: { x: 1, y: 0.6 },
                colors,
                ticks: 200,
                gravity: 0.8,
                scalar: 1.2,
                drift: -0.5,
            });

            animationFrameRef.current = requestAnimationFrame(frame);
        };

        // Initial burst
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { x: 0.5, y: 0.5 },
            colors,
            ticks: 300,
            gravity: 0.6,
            scalar: 1.5,
        });

        frame();
    }, [onComplete]);

    useEffect(() => {
        if (orderStatus === 'CONFIRMED' && !hasTriggeredRef.current) {
            hasTriggeredRef.current = true;
            fireConfetti();
        }

        // Reset when status changes away from CONFIRMED
        if (orderStatus !== 'CONFIRMED') {
            hasTriggeredRef.current = false;
        }

        // Cleanup
        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, [orderStatus, fireConfetti]);

    // This is a visual effect only, no DOM elements needed
    return null;
}
