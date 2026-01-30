'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface DrugNode {
    id: string;
    name: string;
    type: 'current' | 'interaction' | 'safe';
    x: number;
    y: number;
    vx: number;
    vy: number;
}

interface DrugConnection {
    from: string;
    to: string;
    type: 'danger' | 'warning' | 'safe';
}

interface InteractionWebProps {
    currentMeds: string[];
    interactions: { drug1: string; drug2: string; severity: 'danger' | 'warning' | 'safe' }[];
    width?: number;
    height?: number;
}

const nodeColors = {
    current: { fill: '#6366f1', stroke: '#4f46e5', label: 'Current Meds' },     // Indigo
    interaction: { fill: '#ef4444', stroke: '#dc2626', label: 'Interactions' }, // Red
    safe: { fill: '#10b981', stroke: '#059669', label: 'Safe Combos' },         // Emerald
};

const connectionColors = {
    danger: 'rgba(239, 68, 68, 0.8)',
    warning: 'rgba(245, 158, 11, 0.8)',
    safe: 'rgba(16, 185, 129, 0.3)',
};

/**
 * DrugInteractionWeb - Force-directed network graph
 * Canvas-based visualization of drug interactions
 * Physics simulation with gentle floating and wall bouncing
 */
export default function InteractionWeb({
    currentMeds,
    interactions,
    width = 600,
    height = 400,
}: InteractionWebProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const nodesRef = useRef<DrugNode[]>([]);
    const connectionsRef = useRef<DrugConnection[]>([]);
    const animationRef = useRef<number>(0);
    const [isInitialized, setIsInitialized] = useState(false);

    // Initialize nodes and connections
    useEffect(() => {
        const nodes: DrugNode[] = [];
        const connections: DrugConnection[] = [];
        const nodeSet = new Set<string>();

        // Add current meds as nodes
        currentMeds.forEach((med, index) => {
            const angle = (index / currentMeds.length) * Math.PI * 2;
            const radius = Math.min(width, height) * 0.25;
            nodes.push({
                id: med,
                name: med,
                type: 'current',
                x: width / 2 + Math.cos(angle) * radius,
                y: height / 2 + Math.sin(angle) * radius,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
            });
            nodeSet.add(med);
        });

        // Add interaction nodes and connections
        interactions.forEach((interaction) => {
            // Add drug2 as interaction node if not already present
            if (!nodeSet.has(interaction.drug2)) {
                nodes.push({
                    id: interaction.drug2,
                    name: interaction.drug2,
                    type: interaction.severity === 'safe' ? 'safe' : 'interaction',
                    x: width / 2 + (Math.random() - 0.5) * 200,
                    y: height / 2 + (Math.random() - 0.5) * 200,
                    vx: (Math.random() - 0.5) * 0.5,
                    vy: (Math.random() - 0.5) * 0.5,
                });
                nodeSet.add(interaction.drug2);
            }

            connections.push({
                from: interaction.drug1,
                to: interaction.drug2,
                type: interaction.severity,
            });
        });

        nodesRef.current = nodes;
        connectionsRef.current = connections;
        setIsInitialized(true);
    }, [currentMeds, interactions, width, height]);

    const animate = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const nodes = nodesRef.current;
        const connections = connectionsRef.current;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Update physics
        nodes.forEach((node) => {
            // Apply gentle floating motion
            node.vx += (Math.random() - 0.5) * 0.02;
            node.vy += (Math.random() - 0.5) * 0.02;

            // Damping
            node.vx *= 0.99;
            node.vy *= 0.99;

            // Update position
            node.x += node.vx;
            node.y += node.vy;

            // Wall bouncing
            const nodeRadius = 25;
            if (node.x < nodeRadius) {
                node.x = nodeRadius;
                node.vx *= -0.8;
            }
            if (node.x > width - nodeRadius) {
                node.x = width - nodeRadius;
                node.vx *= -0.8;
            }
            if (node.y < nodeRadius + 20) { // Account for legend
                node.y = nodeRadius + 20;
                node.vy *= -0.8;
            }
            if (node.y > height - nodeRadius - 20) {
                node.y = height - nodeRadius - 20;
                node.vy *= -0.8;
            }
        });

        // Draw connections
        connections.forEach((conn) => {
            const fromNode = nodes.find((n) => n.id === conn.from);
            const toNode = nodes.find((n) => n.id === conn.to);

            if (fromNode && toNode) {
                const distance = Math.hypot(toNode.x - fromNode.x, toNode.y - fromNode.y);
                const maxDistance = 200;
                const opacity = Math.max(0.2, 1 - distance / maxDistance);

                ctx.beginPath();
                ctx.moveTo(fromNode.x, fromNode.y);
                ctx.lineTo(toNode.x, toNode.y);
                ctx.strokeStyle = connectionColors[conn.type].replace('0.8', String(opacity * 0.8));
                ctx.lineWidth = conn.type === 'danger' ? 3 : 2;
                ctx.setLineDash(conn.type === 'safe' ? [5, 5] : []);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        });

        // Draw nodes
        nodes.forEach((node) => {
            const colors = nodeColors[node.type];

            // Glow effect
            ctx.shadowColor = colors.fill;
            ctx.shadowBlur = 15;

            // Node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, 20, 0, Math.PI * 2);
            ctx.fillStyle = colors.fill;
            ctx.fill();
            ctx.strokeStyle = colors.stroke;
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.shadowBlur = 0;

            // Label
            ctx.font = '11px Inter, system-ui, sans-serif';
            ctx.fillStyle = '#fff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // Truncate long names
            const displayName = node.name.length > 10 ? node.name.substring(0, 8) + '...' : node.name;
            ctx.fillText(displayName, node.x, node.y + 32);
        });

        animationRef.current = requestAnimationFrame(animate);
    }, [width, height]);

    useEffect(() => {
        if (!isInitialized) return;

        // Check for reduced motion preference
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        
        if (prefersReducedMotion) {
            // Draw static frame
            const canvas = canvasRef.current;
            if (canvas) {
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    // Draw once without animation
                    animate();
                    cancelAnimationFrame(animationRef.current);
                }
            }
        } else {
            animate();
        }

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [isInitialized, animate]);

    return (
        <div 
            className="relative rounded-2xl bg-slate-900 dark:bg-slate-950 border border-slate-700/50 overflow-hidden"
            role="img"
            aria-label="Drug interaction network visualization"
        >
            {/* Legend */}
            <div className="absolute top-4 left-4 bg-slate-800/80 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50 z-10">
                <p className="text-xs font-semibold text-white mb-2">Legend</p>
                <div className="space-y-1.5">
                    {Object.entries(nodeColors).map(([type, colors]) => (
                        <div key={type} className="flex items-center gap-2">
                            <div 
                                className="w-3 h-3 rounded-full" 
                                style={{ backgroundColor: colors.fill }}
                            />
                            <span className="text-xs text-slate-300">{colors.label}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Canvas */}
            <canvas
                ref={canvasRef}
                width={width}
                height={height}
                className="w-full h-auto"
                style={{ maxWidth: width, maxHeight: height }}
            />

            {/* Empty State */}
            {currentMeds.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <p className="text-slate-500 text-sm">No medications to display</p>
                </div>
            )}
        </div>
    );
}
