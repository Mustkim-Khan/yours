'use client';

import {
    AlertTriangle,
    ChevronDown,
    ChevronUp,
    Clock,
    Loader2,
    MessageCircle,
    Pill,
    Shield,
    Sparkles
} from 'lucide-react';
import { useState } from 'react';

interface MedicineExplanation {
    medicine_name: string;
    strength: string;
    purpose: string;
    onset: string;
    common_mistakes: string;
    precautions: string;
    closing: string;
}

interface ExplainMedicineCardProps {
    medicines: Array<{
        medicine_name: string;
        strength: string;
        quantity: number;
    }>;
    onLoadExplanation?: (medicineName: string) => Promise<MedicineExplanation>;
}

export default function ExplainMedicineCard({ 
    medicines, 
    onLoadExplanation 
}: ExplainMedicineCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [loading, setLoading] = useState(false);
    const [explanations, setExplanations] = useState<Record<string, MedicineExplanation>>({});
    const [activeTab, setActiveTab] = useState(0);

    const handleExpand = async () => {
        if (!isExpanded && Object.keys(explanations).length === 0) {
            setLoading(true);
            try {
                // Load explanations for all medicines
                const newExplanations: Record<string, MedicineExplanation> = {};
                for (const med of medicines) {
                    if (onLoadExplanation) {
                        const explanation = await onLoadExplanation(med.medicine_name);
                        newExplanations[med.medicine_name] = explanation;
                    } else {
                        // Fallback static explanation
                        newExplanations[med.medicine_name] = {
                            medicine_name: med.medicine_name,
                            strength: med.strength,
                            purpose: `${med.medicine_name} has been prescribed based on your healthcare provider's assessment of your needs.`,
                            onset: "Effects typically begin within a few hours to a few days, depending on the individual.",
                            common_mistakes: "• Skipping doses or stopping early\n• Taking more than prescribed\n• Not completing the full course",
                            precautions: "• Take with or without food as directed\n• Avoid alcohol unless cleared by your doctor\n• Store at room temperature",
                            closing: "We're here to help! Ask your pharmacist if you have any questions."
                        };
                    }
                }
                setExplanations(newExplanations);
            } catch (error) {
                console.error('Error loading explanations:', error);
            }
            setLoading(false);
        }
        setIsExpanded(!isExpanded);
    };

    const currentMedicine = medicines[activeTab];
    const currentExplanation = explanations[currentMedicine?.medicine_name];

    // Parse bullet points from string
    const parseBullets = (text: string): string[] => {
        if (!text) return [];
        return text.split('\n').filter(line => line.trim().startsWith('•') || line.trim().startsWith('-'));
    };

    return (
        <div className="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 dark:from-indigo-950/30 dark:via-purple-950/30 dark:to-pink-950/30 rounded-xl border border-indigo-200/50 dark:border-indigo-800/50 overflow-hidden mt-4 transition-all duration-300">
            {/* Header - Always visible */}
            <button
                onClick={handleExpand}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/30 dark:hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="text-left">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                            Explain My Medicine
                        </h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                            AI-powered guidance • Tap to learn more
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {loading && <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />}
                    {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                </div>
            </button>

            {/* Expanded Content */}
            {isExpanded && (
                <div className="px-4 pb-4 animate-in slide-in-from-top-2 duration-200">
                    {/* Medicine Tabs (if multiple) */}
                    {medicines.length > 1 && (
                        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
                            {medicines.map((med, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setActiveTab(idx)}
                                    className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                                        activeTab === idx
                                            ? 'bg-indigo-600 text-white'
                                            : 'bg-white/60 dark:bg-gray-800/60 text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700'
                                    }`}
                                >
                                    {med.medicine_name}
                                </button>
                            ))}
                        </div>
                    )}

                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="text-center">
                                <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mx-auto mb-2" />
                                <p className="text-sm text-gray-500">Preparing your explanation...</p>
                            </div>
                        </div>
                    ) : currentExplanation ? (
                        <div className="space-y-4">
                            {/* Medicine Header */}
                            <div className="flex items-center gap-2 p-2 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                                <Pill className="w-5 h-5 text-indigo-600" />
                                <span className="font-medium text-gray-900 dark:text-white">
                                    {currentExplanation.medicine_name}
                                </span>
                                <span className="text-sm text-gray-500">{currentExplanation.strength}</span>
                            </div>

                            {/* Purpose Section */}
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-400">
                                    <Sparkles className="w-4 h-4" />
                                    <span className="text-xs font-semibold uppercase tracking-wide">Why this was prescribed</span>
                                </div>
                                <p className="text-sm text-gray-700 dark:text-gray-300 pl-6">
                                    {currentExplanation.purpose}
                                </p>
                            </div>

                            {/* Onset Section */}
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400">
                                    <Clock className="w-4 h-4" />
                                    <span className="text-xs font-semibold uppercase tracking-wide">When it starts working</span>
                                </div>
                                <p className="text-sm text-gray-700 dark:text-gray-300 pl-6">
                                    {currentExplanation.onset}
                                </p>
                            </div>

                            {/* Common Mistakes */}
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                                    <AlertTriangle className="w-4 h-4" />
                                    <span className="text-xs font-semibold uppercase tracking-wide">Common mistakes to avoid</span>
                                </div>
                                <div className="pl-6 space-y-1">
                                    {parseBullets(currentExplanation.common_mistakes).map((item, idx) => (
                                        <p key={idx} className="text-sm text-gray-700 dark:text-gray-300">
                                            {item}
                                        </p>
                                    ))}
                                    {parseBullets(currentExplanation.common_mistakes).length === 0 && (
                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                            {currentExplanation.common_mistakes}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Precautions */}
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                                    <Shield className="w-4 h-4" />
                                    <span className="text-xs font-semibold uppercase tracking-wide">Important precautions</span>
                                </div>
                                <div className="pl-6 space-y-1">
                                    {parseBullets(currentExplanation.precautions).map((item, idx) => (
                                        <p key={idx} className="text-sm text-gray-700 dark:text-gray-300">
                                            {item}
                                        </p>
                                    ))}
                                    {parseBullets(currentExplanation.precautions).length === 0 && (
                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                            {currentExplanation.precautions}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Closing */}
                            <div className="p-3 bg-gradient-to-r from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 rounded-lg">
                                <div className="flex items-start gap-2">
                                    <MessageCircle className="w-4 h-4 text-indigo-600 dark:text-indigo-400 mt-0.5" />
                                    <p className="text-sm text-indigo-800 dark:text-indigo-300 italic">
                                        {currentExplanation.closing}
                                    </p>
                                </div>
                            </div>

                            {/* Disclaimer */}
                            <p className="text-xs text-gray-400 text-center pt-2">
                                This information is for general guidance only. Always follow your doctor's instructions.
                            </p>
                        </div>
                    ) : (
                        <div className="text-center py-6 text-gray-500">
                            <p>No explanation available</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
