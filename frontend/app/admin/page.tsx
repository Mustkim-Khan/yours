'use client';

import { BentoDashboard } from '@/components/ui';
import {
    AlertCircle,
    Search
} from 'lucide-react';
import { useEffect, useState } from 'react';

interface Medicine {
    medicine_id: string;
    id?: string;  // Backend may return either medicine_id or id
    medicine_name: string;  // Backend returns medicine_name, not name
    strength: string;
    form: string;
    stock_level: number;
    prescription_required: boolean;
    category: string;
    discontinued: boolean;
    controlled_substance: boolean;
}

interface InventoryStats {
    total_skus: number;
    unique_medicines: number;
    out_of_stock: number;
    low_stock: number;
    prescription_required: number;
    discontinued: number;
}

export default function AdminPage() {
    const [medicines, setMedicines] = useState<Medicine[]>([]);
    const [stats, setStats] = useState<InventoryStats | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [medicinesRes, statsRes] = await Promise.all([
                fetch('http://localhost:8000/inventory/medicines'),
                fetch('http://localhost:8000/inventory/stats'),
            ]);

            const medicinesData = await medicinesRes.json();
            const statsData = await statsRes.json();

            // Ensure medicines is always an array
            const medicinesList = medicinesData?.results || medicinesData || [];
            setMedicines(Array.isArray(medicinesList) ? medicinesList : []);
            setStats(statsData);
        } catch (error) {
            console.error('Failed to fetch inventory:', error);
            setMedicines([]);
        } finally {
            setLoading(false);
        }
    };


    const filteredMedicines = Array.isArray(medicines) ? medicines.filter(med =>
        (med.medicine_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (med.medicine_id || med.id || '').toLowerCase().includes(searchQuery.toLowerCase())
    ) : [];

    const getStockLabel = (level: number) => {
        if (level === 0) {
            return { text: `0 Out of Stock`, color: 'text-red-600 dark:text-red-400' };
        } else if (level <= 100) {
            return { text: `${level} Low Stock`, color: 'text-orange-600 dark:text-orange-400' };
        }
        return { text: `${level} High Stock`, color: 'text-gray-900 dark:text-white' };
    };

    return (
        <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-300">
            {/* Header */}
            <div className="mb-6 flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Inventory Dashboard</h1>
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                    <AlertCircle className="w-4 h-4" />
                    Inventory is managed autonomously by AI. Admin view is read-only.
                </div>
            </div>

            {/* Premium Bento Dashboard */}
            <div className="mb-6 -mx-4">
                <BentoDashboard
                    aiConfidence={92}
                    activeRefills={stats?.low_stock || 12}
                    safetyAlerts={stats?.out_of_stock || 3}
                    patientLoad={stats?.total_skus || 150}
                    avgProcessingTime="1.8s"
                />
            </div>

            {/* Search */}
            <div className="relative max-w-md mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                    type="text"
                    placeholder="Search medicine by name..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                />
            </div>

            {/* Medicine Inventory Table */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden transition-colors">
                <div className="p-4 border-b border-gray-100 dark:border-gray-700">
                    <h2 className="font-semibold text-gray-900 dark:text-white">Medicine Inventory</h2>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
                                <th className="px-6 py-3 font-medium">Medicine Name</th>
                                <th className="px-6 py-3 font-medium">Strength</th>
                                <th className="px-6 py-3 font-medium">Form</th>
                                <th className="px-6 py-3 font-medium">Stock Level</th>
                                <th className="px-6 py-3 font-medium">Prescription Required</th>
                                <th className="px-6 py-3 font-medium">Category</th>
                                <th className="px-6 py-3 font-medium">Discontinued</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {filteredMedicines.map((med) => {
                                const stockInfo = getStockLabel(med.stock_level);

                                return (
                                    <tr key={med.medicine_id} className="border-b border-gray-50 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                                        <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                                            {med.medicine_name}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                                            {med.strength}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                                            {med.form}
                                        </td>
                                        <td className="px-6 py-4 text-sm">
                                            <span className={stockInfo.color}>
                                                {stockInfo.text}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            {med.prescription_required ? (
                                                <span className="px-2 py-1 bg-indigo-50 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs font-medium rounded">
                                                    Rx Required
                                                </span>
                                            ) : (
                                                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs font-medium rounded">
                                                    OTC
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="px-2 py-1 bg-purple-50 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 text-xs font-medium rounded">
                                                {med.category}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            {med.discontinued ? (
                                                <span className="px-2 py-1 bg-red-50 dark:bg-red-900/40 text-red-700 dark:text-red-300 text-xs font-medium rounded">
                                                    Discontinued
                                                </span>
                                            ) : (
                                                <span className="px-2 py-1 bg-green-50 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs font-medium rounded">
                                                    Active
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}