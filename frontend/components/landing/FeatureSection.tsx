'use client';

import { motion, useInView } from 'framer-motion';
import { ReactNode, useRef } from 'react';

interface FeatureSectionProps {
  title: string;
  description: string;
  visual: ReactNode;
  index: number;
  reversed?: boolean;
}

export default function FeatureSection({ 
  title, 
  description, 
  visual, 
  index,
  reversed = false 
}: FeatureSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.1,
      },
    },
  };

  const textVariants = {
    hidden: { 
      opacity: 0, 
      x: reversed ? 50 : -50 
    },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: {
        duration: 0.8,
        ease: [0.25, 0.46, 0.45, 0.94],
      },
    },
  };

  const visualVariants = {
    hidden: { 
      opacity: 0, 
      x: reversed ? -50 : 50,
      scale: 0.9,
    },
    visible: { 
      opacity: 1, 
      x: 0,
      scale: 1,
      transition: {
        duration: 0.8,
        ease: [0.25, 0.46, 0.45, 0.94],
      },
    },
  };

  const featureNumber = String(index + 1).padStart(2, '0');

  return (
    <motion.div
      ref={ref}
      variants={containerVariants}
      initial="hidden"
      animate={isInView ? 'visible' : 'hidden'}
      className={`flex flex-col ${reversed ? 'lg:flex-row-reverse' : 'lg:flex-row'} items-center gap-12 lg:gap-20 py-24 lg:py-32`}
    >
      {/* Text Content */}
      <motion.div 
        variants={textVariants}
        className="flex-1 max-w-xl"
      >
        <span className="text-violet-400/50 font-mono text-sm tracking-widest mb-4 block">
          {featureNumber}
        </span>
        <h3 className="text-3xl md:text-4xl lg:text-5xl font-semibold text-white mb-6 leading-tight">
          {title}
        </h3>
        <p className="text-lg md:text-xl text-slate-400 leading-relaxed">
          {description}
        </p>
      </motion.div>

      {/* Visual Content */}
      <motion.div 
        variants={visualVariants}
        className="flex-1 w-full max-w-xl"
      >
        <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 p-8">
          {/* Ambient glow */}
          <div className="absolute -top-20 -right-20 w-40 h-40 bg-violet-500/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-cyan-500/20 rounded-full blur-3xl" />
          
          <div className="relative z-10">
            {visual}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
