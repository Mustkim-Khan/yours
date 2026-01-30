'use client';

import { motion, useInView } from 'framer-motion';
import { gsap } from 'gsap';
import { useEffect, useRef } from 'react';

const nodes = [
  { id: 'user', label: 'User', x: 10, y: 50 },
  { id: 'orchestrator', label: 'Orchestrator AI', x: 35, y: 30 },
  { id: 'pharmacist', label: 'Pharmacist Agent', x: 60, y: 20 },
  { id: 'policy', label: 'Policy Agent', x: 60, y: 50 },
  { id: 'inventory', label: 'Inventory Agent', x: 60, y: 80 },
  { id: 'data', label: 'Data Layer', x: 85, y: 50 },
];

const connections = [
  { from: 'user', to: 'orchestrator' },
  { from: 'orchestrator', to: 'pharmacist' },
  { from: 'orchestrator', to: 'policy' },
  { from: 'orchestrator', to: 'inventory' },
  { from: 'pharmacist', to: 'data' },
  { from: 'policy', to: 'data' },
  { from: 'inventory', to: 'data' },
];

export default function ArchitectureDiagram() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: '-100px' });
  const nodesRef = useRef<(HTMLDivElement | null)[]>([]);
  const connectionsRef = useRef<(SVGLineElement | null)[]>([]);

  useEffect(() => {
    if (!isInView) return;

    // Animate nodes appearing
    nodesRef.current.forEach((node, index) => {
      if (node) {
        gsap.fromTo(node,
          { scale: 0, opacity: 0 },
          { 
            scale: 1, 
            opacity: 1, 
            duration: 0.6,
            delay: index * 0.15,
            ease: 'back.out(1.7)',
          }
        );

        // Add subtle pulse
        gsap.to(node, {
          boxShadow: '0 0 30px rgba(139, 92, 246, 0.6)',
          duration: 2,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          delay: index * 0.2,
        });
      }
    });

    // Animate connections
    connectionsRef.current.forEach((line, index) => {
      if (line) {
        const length = line.getTotalLength();
        gsap.fromTo(line,
          { strokeDasharray: length, strokeDashoffset: length },
          {
            strokeDashoffset: 0,
            duration: 1,
            delay: 0.5 + index * 0.1,
            ease: 'power2.out',
          }
        );

        // Add flowing animation
        gsap.to(line, {
          strokeDashoffset: -length * 2,
          duration: 3,
          repeat: -1,
          ease: 'none',
          delay: 1.5 + index * 0.1,
        });
      }
    });
  }, [isInView]);

  const getNodePosition = (id: string) => {
    const node = nodes.find(n => n.id === id);
    return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
  };

  return (
    <div ref={containerRef} className="relative w-full aspect-[16/9] min-h-[400px]">
      {/* SVG for connections */}
      <svg className="absolute inset-0 w-full h-full">
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#06b6d4" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.3" />
          </linearGradient>
        </defs>
        {connections.map((conn, index) => {
          const from = getNodePosition(conn.from);
          const to = getNodePosition(conn.to);
          return (
            <line
              key={`${conn.from}-${conn.to}`}
              ref={el => { connectionsRef.current[index] = el; }}
              x1={`${from.x}%`}
              y1={`${from.y}%`}
              x2={`${to.x}%`}
              y2={`${to.y}%`}
              stroke="url(#lineGradient)"
              strokeWidth="2"
              strokeDasharray="8 4"
              opacity={isInView ? 1 : 0}
            />
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((node, index) => (
        <div
          key={node.id}
          ref={el => { nodesRef.current[index] = el; }}
          className="absolute transform -translate-x-1/2 -translate-y-1/2 z-10"
          style={{ left: `${node.x}%`, top: `${node.y}%` }}
        >
          <motion.div
            className={`
              px-4 py-3 rounded-xl border backdrop-blur-sm
              ${node.id === 'orchestrator' 
                ? 'bg-violet-500/20 border-violet-400/50 text-violet-300' 
                : node.id === 'user'
                  ? 'bg-cyan-500/20 border-cyan-400/50 text-cyan-300'
                  : node.id === 'data'
                    ? 'bg-emerald-500/20 border-emerald-400/50 text-emerald-300'
                    : 'bg-slate-700/50 border-slate-600/50 text-slate-300'
              }
            `}
            whileHover={{ scale: 1.1 }}
            transition={{ type: 'spring', stiffness: 400 }}
          >
            <span className="text-sm font-medium whitespace-nowrap">{node.label}</span>
          </motion.div>
        </div>
      ))}
    </div>
  );
}
