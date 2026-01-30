'use client';

import { HolographicCard, InteractionWeb } from '@/components/ui';
import {
    addToCabinet,
    CabinetMedicine,
    getCabinetMedicines,
    removeFromCabinet,
    scanMedicine,
    ScanResult
} from '@/lib/cabinetService';
import { auth } from '@/lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import {
    AlertTriangle,
    Camera,
    CheckCircle2,
    Clock,
    Home,
    Loader2,
    Package,
    Plus,
    ShoppingCart,
    Sparkles,
    Trash2,
    X,
    XCircle
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

// Mock drug interactions for demo (would be computed from real data)
const MOCK_INTERACTIONS = [
    { drug1: 'Paracetamol', drug2: 'Aspirin', severity: 'warning' as const },
    { drug1: 'Omeprazole', drug2: 'Clopidogrel', severity: 'danger' as const },
    { drug1: 'Cetirizine', drug2: 'Vitamin D3', severity: 'safe' as const },
    { drug1: 'Montelukast', drug2: 'Ibuprofen', severity: 'warning' as const },
];

export default function CabinetPage() {
    const [medicines, setMedicines] = useState<CabinetMedicine[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isScanning, setIsScanning] = useState(false);
    const [scanResult, setScanResult] = useState<ScanResult | null>(null);
    const [showScanModal, setShowScanModal] = useState(false);
    const [filter, setFilter] = useState<'all' | 'safe' | 'expiring' | 'expired'>('all');
    const [showInteractionModal, setShowInteractionModal] = useState(false);
    const [selectedMedicine, setSelectedMedicine] = useState<CabinetMedicine | null>(null);
    const [userId, setUserId] = useState<string | null>(null);
    const [editQuantity, setEditQuantity] = useState<number>(1);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Auth state
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                setUserId(user.uid);
            } else {
                setUserId(null);
                setMedicines([]);
            }
        });
        return () => unsubscribe();
    }, []);

    // Load medicines from Firestore
    useEffect(() => {
        if (userId) {
            loadMedicines();
        }
    }, [userId]);

    const loadMedicines = async () => {
        if (!userId) return;
        setIsLoading(true);
        try {
            const meds = await getCabinetMedicines(userId);
            setMedicines(meds);
        } catch (e) {
            console.error('Failed to load medicines:', e);
        } finally {
            setIsLoading(false);
        }
    };

    // Handle image selection
    const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsScanning(true);
        setShowScanModal(true);
        setScanResult(null);

        try {
            const result = await scanMedicine(file);
            setScanResult(result);
            if (result.success && result.medicine) {
                setEditQuantity(1); // Default quantity
            }
        } catch (error) {
            console.error('Scan error:', error);
            setScanResult({ success: false, error: 'Scan failed' });
        } finally {
            setIsScanning(false);
            // Reset file input
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    // Add scanned medicine to cabinet
    const handleAddToCabinet = async () => {
        if (!userId || !scanResult?.medicine) return;

        try {
            const result = await addToCabinet(userId, {
                name: scanResult.medicine.name,
                strength: scanResult.medicine.strength,
                form: scanResult.medicine.form,
                expiry_date: scanResult.medicine.expiry_date,
                expiry_status: scanResult.medicine.expiry_status,
                quantity: editQuantity,
                ai_confidence: scanResult.medicine.ai_confidence,
                manufacturer: scanResult.medicine.manufacturer,
            });

            if (result.success && result.medicine) {
                setMedicines(prev => [...prev, result.medicine!]);
                setShowScanModal(false);
                setScanResult(null);
            }
        } catch (e) {
            console.error('Failed to add medicine:', e);
        }
    };

    // Remove medicine from cabinet
    const handleRemove = async (medicineId: string) => {
        if (!userId) return;
        
        try {
            const result = await removeFromCabinet(userId, medicineId);
            if (result.success) {
                setMedicines(prev => prev.filter(m => m.id !== medicineId));
            }
        } catch (e) {
            console.error('Failed to remove medicine:', e);
        }
    };

    // Filter medicines
    const filteredMedicines = filter === 'all' 
        ? medicines 
        : medicines.filter(m => m.expiryStatus === filter);

    // Stats
    const stats = {
        total: medicines.length,
        safe: medicines.filter(m => m.expiryStatus === 'safe').length,
        expiring: medicines.filter(m => m.expiryStatus === 'expiring').length,
        expired: medicines.filter(m => m.expiryStatus === 'expired').length
    };

    // Get expiry status color
    const getExpiryColor = (status: string) => {
        switch (status) {
            case 'safe': return 'border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20';
            case 'expiring': return 'border-amber-400 bg-amber-50 dark:bg-amber-900/20';
            case 'expired': return 'border-red-400 bg-red-50 dark:bg-red-900/20';
            default: return 'border-gray-200';
        }
    };

    const getExpiryBadge = (status: string, date?: string) => {
        const formattedDate = date 
            ? new Date(date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
            : 'Unknown';
        
        switch (status) {
            case 'safe':
                return (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400">
                        <CheckCircle2 className="w-3 h-3" />
                        Expires {formattedDate}
                    </span>
                );
            case 'expiring':
                return (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 animate-pulse">
                        <Clock className="w-3 h-3" />
                        Expiring {formattedDate}
                    </span>
                );
            case 'expired':
                return (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400">
                        <XCircle className="w-3 h-3" />
                        Expired
                    </span>
                );
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-300">
            {/* Header */}
            <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10">
                <div className="max-w-6xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                                <Home className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                            </Link>
                            <div>
                                <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                    <Package className="w-6 h-6 text-indigo-600" />
                                    My Medicine Cabinet
                                </h1>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Track what you have at home • Avoid waste & duplicates
                                </p>
                            </div>
                        </div>
                        
                        {/* Add Medicine CTA */}
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium rounded-xl shadow-lg shadow-indigo-500/25 transition-all"
                        >
                            <Camera className="w-5 h-5" />
                            Scan Medicine
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-4 py-6">
                {/* Stats Overview */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <button
                        onClick={() => setFilter('all')}
                        className={`p-4 rounded-xl border-2 transition-all ${
                            filter === 'all' 
                                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20' 
                                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                        }`}
                    >
                        <p className="text-3xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Total Medicines</p>
                    </button>
                    <button
                        onClick={() => setFilter('safe')}
                        className={`p-4 rounded-xl border-2 transition-all ${
                            filter === 'safe' 
                                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' 
                                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                        }`}
                    >
                        <p className="text-3xl font-bold text-emerald-600">{stats.safe}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Safe</p>
                    </button>
                    <button
                        onClick={() => setFilter('expiring')}
                        className={`p-4 rounded-xl border-2 transition-all ${
                            filter === 'expiring' 
                                ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20' 
                                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                        }`}
                    >
                        <p className="text-3xl font-bold text-amber-600">{stats.expiring}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Expiring Soon</p>
                    </button>
                    <button
                        onClick={() => setFilter('expired')}
                        className={`p-4 rounded-xl border-2 transition-all ${
                            filter === 'expired' 
                                ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                        }`}
                    >
                        <p className="text-3xl font-bold text-red-600">{stats.expired}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Expired</p>
                    </button>
                </div>

                {/* AI Intelligence Banner */}
                <div className="mb-6 p-4 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 dark:from-indigo-500/5 dark:via-purple-500/5 dark:to-pink-500/5 border border-indigo-200/50 dark:border-indigo-800/50 rounded-xl">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1">
                            <p className="font-medium text-gray-900 dark:text-white">AI-Powered Cabinet Intelligence</p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                Take a photo of any medicine • AI extracts name, strength, expiry • Stored securely in your account
                            </p>
                        </div>
                        <button
                            onClick={() => setShowInteractionModal(true)}
                            className="ml-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
                        >
                            View Interactions
                        </button>
                    </div>
                </div>

                {/* Loading State */}
                {isLoading ? (
                    <div className="text-center py-16">
                        <Loader2 className="w-10 h-10 mx-auto mb-4 animate-spin text-indigo-600" />
                        <p className="text-gray-500">Loading your medicines...</p>
                    </div>
                ) : filteredMedicines.length === 0 ? (
                    /* Empty State */
                    <div className="text-center py-16">
                        <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                            <Package className="w-10 h-10 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                            Your cabinet is empty
                        </h3>
                        <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                            Take a photo of your medicines to add them to your cabinet. 
                            AI will extract the details automatically.
                        </p>
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-colors"
                        >
                            <Camera className="w-5 h-5" />
                            Scan Your First Medicine
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredMedicines.map((medicine) => (
                            <div
                                key={medicine.id}
                                onClick={() => setSelectedMedicine(medicine)}
                                className={`relative bg-white dark:bg-gray-800 rounded-xl border-2 overflow-hidden transition-all hover:shadow-lg cursor-pointer hover:scale-[1.02] ${getExpiryColor(medicine.expiryStatus)}`}
                            >
                                {/* Medicine Header */}
                                <div className="h-32 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center relative">
                                    <div className="text-4xl">💊</div>
                                    {/* AI Confidence Badge */}
                                    <div className="absolute top-2 right-2 px-2 py-0.5 bg-white/80 dark:bg-gray-900/80 rounded-full text-xs font-medium text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                                        <Sparkles className="w-3 h-3" />
                                        {Math.round(medicine.aiConfidence * 100)}% AI
                                    </div>
                                </div>

                                {/* Content */}
                                <div className="p-4">
                                    <div className="flex items-start justify-between mb-2">
                                        <div>
                                            <h3 className="font-semibold text-gray-900 dark:text-white">
                                                {medicine.name}
                                            </h3>
                                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                                {medicine.strength} • {medicine.form}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Expiry Badge */}
                                    <div className="mb-3">
                                        {getExpiryBadge(medicine.expiryStatus, medicine.expiryDate)}
                                    </div>

                                    {/* Quantity Progress */}
                                    <div className="mb-3">
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-gray-600 dark:text-gray-400">Remaining</span>
                                            <span className="font-medium text-gray-900 dark:text-white">
                                                {medicine.estimatedRemaining} of {medicine.quantity}
                                            </span>
                                        </div>
                                        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                            <div 
                                                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
                                                style={{ width: `${(medicine.estimatedRemaining / medicine.quantity) * 100}%` }}
                                            />
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex gap-2">
                                        {medicine.estimatedRemaining < 5 && medicine.expiryStatus !== 'expired' && (
                                            <Link
                                                href="/"
                                                className="flex-1 flex items-center justify-center gap-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
                                            >
                                                <ShoppingCart className="w-4 h-4" />
                                                Reorder
                                            </Link>
                                        )}
                                        <button 
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleRemove(medicine.id);
                                            }}
                                            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}

                        {/* Add New Card */}
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            className="h-full min-h-[280px] border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl flex flex-col items-center justify-center gap-3 text-gray-500 dark:text-gray-400 hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                        >
                            <div className="w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                                <Plus className="w-6 h-6" />
                            </div>
                            <span className="font-medium">Add Medicine</span>
                            <span className="text-sm">Take a photo</span>
                        </button>
                    </div>
                )}

                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={handleImageSelect}
                />
            </main>

            {/* Scan Modal */}
            {showScanModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full mx-4 animate-in zoom-in-95">
                        {isScanning ? (
                            <>
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                                    <Camera className="w-8 h-8 text-indigo-600 animate-pulse" />
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 text-center">
                                    Analyzing Medicine
                                </h3>
                                <p className="text-gray-500 dark:text-gray-400 mb-4 text-center">
                                    AI is reading the label and extracting details...
                                </p>
                                <div className="flex justify-center gap-1">
                                    <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                            </>
                        ) : scanResult?.success ? (
                            <>
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                        Medicine Detected
                                    </h3>
                                    <button
                                        onClick={() => setShowScanModal(false)}
                                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                                    >
                                        <X className="w-5 h-5 text-gray-500" />
                                    </button>
                                </div>
                                
                                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 mb-4">
                                    {/* Show uploaded image */}
                                    {scanResult.medicine?.image_base64 && (
                                        <div className="mb-3 flex justify-center">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img 
                                                src={`data:image/jpeg;base64,${scanResult.medicine.image_base64}`}
                                                alt="Scanned medicine"
                                                className="w-24 h-24 object-cover rounded-lg border-2 border-indigo-200"
                                            />
                                        </div>
                                    )}
                                    <div className="flex items-center gap-2 mb-2">
                                        <Sparkles className="w-4 h-4 text-indigo-500" />
                                        <span className="text-sm text-indigo-600 dark:text-indigo-400">
                                            {Math.round((scanResult.medicine?.ai_confidence || 0) * 100)}% confidence
                                        </span>
                                    </div>
                                    <h4 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                                        {scanResult.medicine?.name}
                                    </h4>
                                    <p className="text-gray-600 dark:text-gray-300">
                                        {scanResult.medicine?.strength} • {scanResult.medicine?.form}
                                    </p>
                                    {scanResult.medicine?.manufacturer && (
                                        <p className="text-sm text-gray-500 mt-1">
                                            by {scanResult.medicine.manufacturer}
                                        </p>
                                    )}
                                    {scanResult.medicine?.expiry_date && (
                                        <div className="mt-2">
                                            {getExpiryBadge(
                                                scanResult.medicine.expiry_status || 'safe',
                                                scanResult.medicine.expiry_date
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Quantity
                                    </label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={editQuantity}
                                        onChange={(e) => setEditQuantity(parseInt(e.target.value) || 1)}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                                    />
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setShowScanModal(false)}
                                        className="flex-1 px-4 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleAddToCabinet}
                                        className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg"
                                    >
                                        Add to Cabinet
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                {/* Show the uploaded image that failed */}
                                {scanResult?.is_medicine === false ? (
                                    <>
                                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
                                            <AlertTriangle className="w-8 h-8 text-amber-600" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 text-center">
                                            Not a Medicine Image
                                        </h3>
                                        <p className="text-gray-500 dark:text-gray-400 mb-4 text-center">
                                            Please upload a clear photo of medicine packaging, pill strip, bottle label, or prescription.
                                        </p>
                                        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 mb-4">
                                            <p className="text-sm text-amber-800 dark:text-amber-300 text-center">
                                                📸 Tip: Make sure the medicine name and details are clearly visible in the photo.
                                            </p>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
                                            <XCircle className="w-8 h-8 text-red-600" />
                                        </div>
                                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 text-center">
                                            Scan Failed
                                        </h3>
                                        <p className="text-gray-500 dark:text-gray-400 mb-4 text-center">
                                            {scanResult?.error || 'Could not read the medicine label. Please try again with a clearer photo.'}
                                        </p>
                                    </>
                                )}
                                <button
                                    onClick={() => {
                                        setShowScanModal(false);
                                        fileInputRef.current?.click();
                                    }}
                                    className="w-full px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg"
                                >
                                    Upload Another Image
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Drug Interactions Modal */}
            {showInteractionModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto animate-in zoom-in-95">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Drug Interaction Analysis
                            </h3>
                            <button
                                onClick={() => setShowInteractionModal(false)}
                                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-gray-500" />
                            </button>
                        </div>
                        
                        {/* Interaction Web Visualization */}
                        <div className="mb-4">
                            <InteractionWeb
                                currentMeds={medicines.map(m => m.name)}
                                interactions={MOCK_INTERACTIONS}
                                width={550}
                                height={350}
                            />
                        </div>
                        
                        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                            <div className="flex items-start gap-2">
                                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-amber-800 dark:text-amber-300">
                                    This visualization shows potential drug interactions between your cabinet medicines. 
                                    Always consult your pharmacist or doctor before combining medications.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Featured Medicine with HolographicCard */}
            {selectedMedicine && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="relative">
                        <button
                            onClick={() => setSelectedMedicine(null)}
                            className="absolute -top-3 -right-3 z-10 p-2 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full shadow-lg transition-colors"
                        >
                            <X className="w-5 h-5 text-gray-500" />
                        </button>
                        <HolographicCard
                            medicineName={selectedMedicine.name}
                            strength={selectedMedicine.strength}
                            interactionWarning={
                                MOCK_INTERACTIONS.find(i => i.drug1 === selectedMedicine.name && i.severity !== 'safe')
                                    ? `Interacts with ${MOCK_INTERACTIONS.find(i => i.drug1 === selectedMedicine.name)?.drug2}`
                                    : undefined
                            }
                            onViewInteractions={() => {
                                setSelectedMedicine(null);
                                setShowInteractionModal(true);
                            }}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
