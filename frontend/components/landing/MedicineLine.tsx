'use client';

import { gsap } from 'gsap';
import { useEffect, useRef, useState } from 'react';

// ============================================
// PERFORMANCE GUARDRAILS:
// - Animation paused when offscreen (IntersectionObserver)
// - Respects prefers-reduced-motion
// - GPU-accelerated transforms only
// - No blocking JS on initial load
// ============================================

// Medicine icons as SVG components
const PillIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <ellipse cx="12" cy="12" rx="10" ry="5" transform="rotate(-45 12 12)" />
  </svg>
);

const CapsuleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="2" width="12" height="20" rx="6" />
    <rect x="6" y="12" width="12" height="10" rx="6" fill="currentColor" opacity="0.6" />
  </svg>
);

const TabletIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="2" x2="12" y2="22" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
  </svg>
);

const SyringeIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M19.5 4.5L18 6M18 6L15 3M18 6L12.75 11.25M4.5 19.5L6 18M6 18L9 21M6 18L11.25 12.75M12.75 11.25L11.25 12.75M12.75 11.25L17.25 15.75L15.75 17.25L11.25 12.75" />
  </svg>
);

const RxIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <text x="4" y="18" fontSize="14" fontFamily="serif" fontWeight="bold">Rx</text>
  </svg>
);

const ChatBubbleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
  </svg>
);

const AINodeIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <circle cx="12" cy="12" r="4" />
    <circle cx="12" cy="3" r="2" />
    <circle cx="12" cy="21" r="2" />
    <circle cx="3" cy="12" r="2" />
    <circle cx="21" cy="12" r="2" />
    <line x1="12" y1="7" x2="12" y2="5" stroke="currentColor" strokeWidth="1" />
    <line x1="12" y1="19" x2="12" y2="17" stroke="currentColor" strokeWidth="1" />
    <line x1="7" y1="12" x2="5" y2="12" stroke="currentColor" strokeWidth="1" />
    <line x1="19" y1="12" x2="17" y2="12" stroke="currentColor" strokeWidth="1" />
  </svg>
);

const MedicalCrossIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3z" />
  </svg>
);

const icons = [PillIcon, CapsuleIcon, TabletIcon, SyringeIcon, RxIcon, ChatBubbleIcon, AINodeIcon, MedicalCrossIcon];
const colors = [
  'text-violet-400',
  'text-cyan-400',
  'text-blue-400',
  'text-indigo-400',
  'text-purple-400',
  'text-teal-400',
  'text-sky-400',
  'text-fuchsia-400',
];

interface MedicineLineProps {
  className?: string;
  direction?: 'left' | 'right';
  speed?: number;
  opacity?: number;
}

export default function MedicineLine({ 
  className = '', 
  direction = 'left', 
  speed = 30,
  opacity = 0.6 
}: MedicineLineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const iconTweensRef = useRef<gsap.core.Tween[]>([]);
  const [isVisible, setIsVisible] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // Check for reduced motion preference
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Intersection Observer for pause/resume when offscreen
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          setIsVisible(entry.isIntersecting);
        });
      },
      { threshold: 0.1 }
    );

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Pause/resume animation based on visibility
  useEffect(() => {
    if (prefersReducedMotion) return;

    if (isVisible) {
      timelineRef.current?.resume();
      iconTweensRef.current.forEach(tween => tween.resume());
    } else {
      timelineRef.current?.pause();
      iconTweensRef.current.forEach(tween => tween.pause());
    }
  }, [isVisible, prefersReducedMotion]);

  // Main animation setup
  useEffect(() => {
    if (!itemsRef.current || !containerRef.current || prefersReducedMotion) return;

    const items = itemsRef.current;
    const totalWidth = items.scrollWidth / 2;
    
    // Create seamless loop animation
    const tl = gsap.timeline({ repeat: -1, paused: !isVisible });
    timelineRef.current = tl;
    
    if (direction === 'left') {
      tl.fromTo(items, 
        { x: 0 },
        { x: -totalWidth, duration: speed, ease: 'none' }
      );
    } else {
      tl.fromTo(items,
        { x: -totalWidth },
        { x: 0, duration: speed, ease: 'none' }
      );
    }

    // Add subtle floating animation to individual items
    const iconElements = items.querySelectorAll('.medicine-icon');
    const tweens: gsap.core.Tween[] = [];
    
    iconElements.forEach((icon, index) => {
      const floatTween = gsap.to(icon, {
        y: gsap.utils.random(-8, 8),
        rotation: gsap.utils.random(-15, 15),
        duration: gsap.utils.random(2, 4),
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        delay: index * 0.1,
        paused: !isVisible,
      });
      tweens.push(floatTween);

      // Add pulsing glow
      const glowTween = gsap.to(icon, {
        filter: 'drop-shadow(0 0 12px currentColor)',
        duration: gsap.utils.random(1.5, 3),
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        delay: index * 0.15,
        paused: !isVisible,
      });
      tweens.push(glowTween);
    });
    
    iconTweensRef.current = tweens;

    return () => {
      tl.kill();
      tweens.forEach(tween => tween.kill());
    };
  }, [direction, speed, prefersReducedMotion]);

  // Generate items for seamless loop (duplicate for smooth scroll)
  const generateItems = () => {
    const items = [];
    for (let i = 0; i < 40; i++) {
      const IconComponent = icons[i % icons.length];
      const colorClass = colors[i % colors.length];
      const size = 16 + (i % 4) * 8; // Varying sizes: 16, 24, 32, 40
      
      items.push(
        <div
          key={i}
          className={`medicine-icon ${colorClass} flex-shrink-0 mx-4 md:mx-6 lg:mx-8`}
          style={{ 
            width: size, 
            height: size,
            filter: 'drop-shadow(0 0 6px currentColor)',
          }}
        >
          <IconComponent className="w-full h-full" />
        </div>
      );
    }
    return items;
  };

  const items = generateItems();

  // If reduced motion is preferred, show static version
  if (prefersReducedMotion) {
    return (
      <div 
        ref={containerRef}
        className={`relative overflow-hidden ${className}`}
        style={{ opacity }}
      >
        <div className="absolute left-0 top-0 bottom-0 w-32 z-10 bg-gradient-to-r from-slate-950 to-transparent pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-32 z-10 bg-gradient-to-l from-slate-950 to-transparent pointer-events-none" />
        <div className="flex items-center whitespace-nowrap justify-center">
          {items.slice(0, 10)}
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`relative overflow-hidden ${className}`}
      style={{ opacity }}
    >
      {/* Gradient fade on edges */}
      <div className="absolute left-0 top-0 bottom-0 w-32 z-10 bg-gradient-to-r from-slate-950 to-transparent pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-32 z-10 bg-gradient-to-l from-slate-950 to-transparent pointer-events-none" />
      
      <div 
        ref={itemsRef}
        className="flex items-center whitespace-nowrap"
      >
        {items}
        {items} {/* Duplicate for seamless loop */}
      </div>
    </div>
  );
}
