'use client';

import { useState, useEffect } from 'react';
import {
    RefreshCw, Clock, AlertTriangle, CheckCircle,
    Search, ChevronDown, ChevronLeft, ChevronRight,
    TrendingUp, Shield, Package, Info
} from 'lucide-react';

interface RefillAlert {
    patient_name: string;
    patient_id: string;
    medicine: string;
    days_remaining: number;
    status: string;
    last_updated: string;
    refill_date: string;
    dosage?: string;
    last_order_date?: string;
    triggered_agent?: string;
    ai_reason?: string;
}

export default function RefillsPage() {
    const [refills, setRefills] = useState<RefillAlert[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [medicineFilter, setMedicineFilter] = useState('all');
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    useEffect(() => {
        fetchRefills();
    }, []);

    const fetchRefills = async () => {
        try {
            const res = await fetch('http://localhost:8000/admin/refills');
            const data = await res.json();
            const refillsList = data?.alerts || [];
            setRefills(Array.isArray(refillsList) ? refillsList : []);
        } catch (error) {
            console.error('Failed to fetch refills:', error);
            setRefills([]);
        } finally {
            setLoading(false);
        }
    };

    const filteredRefills = Array.isArray(refills) ? refills.filter(refill => {
        const matchesSearch = (refill.patient_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
            (refill.medicine || '').toLowerCase().includes(searchQuery.toLowerCase());

        if (!matchesSearch) return false;

        if (statusFilter !== 'all') {
            if (statusFilter === 'due_soon' && refill.status === 'REMIND') return true;
            if (statusFilter === 'overdue' && refill.days_remaining <= 0) return true;
            if (statusFilter === 'scheduled' && refill.status === 'AUTO_REFILL') return true;
            if (statusFilter === 'blocked' && refill.status === 'BLOCK') return true;
            // If filter applies and no match above
            if (['due_soon', 'overdue', 'scheduled', 'blocked'].includes(statusFilter)) {
                // Check logical matches
                if (statusFilter === 'due_soon' && refill.days_remaining <= 3 && refill.days_remaining > 0) return true;
                return false;
            }
        }

        if (medicineFilter !== 'all' && refill.medicine !== medicineFilter) return false;

        return true;
    }) : [];

    const paginatedRefills = filteredRefills.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    const totalPages = Math.ceil(filteredRefills.length / itemsPerPage);

    const getStatusBadge = (status: string, days: number) => {
        if (status === 'BLOCK') {
            return { label: 'Blocked: Rx Required', color: 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800' };
        }
        if (status === 'AUTO_REFILL') {
            return { label: 'Auto-Refill Scheduled', color: 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' };
        }
        if (days <= 0) {
            return { label: 'Overdue', color: 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800' };
        }
        return { label: 'Reminder Sent', color: 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800' };
    };

    return (
        <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen transition-colors duration-300">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Proactive Refill Alerts</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        Detailed operational view of AI-driven refill decisions.
                    </p>
                </div>
                <div className="text-right">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                        Read-Only View
                    </span>
                    <p className="text-xs text-gray-400 mt-1">No manual overrides allowed</p>
                </div>
            </div>

            {/* Agent Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 flex items-center justify-between transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-white">Refill Prediction Agent</span>
                    </div>
                    <span className="px-2 py-0.5 bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs font-medium rounded-full flex items-center gap-1">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> Active
                    </span>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 flex items-center justify-between transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center">
                            <Shield className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-white">Safety Policy Agent</span>
                    </div>
                    <span className="px-2 py-0.5 bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs font-medium rounded-full flex items-center gap-1">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> Active
                    </span>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 flex items-center justify-between transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center">
                            <Package className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-white">Inventory Agent</span>
                    </div>
                    <span className="px-2 py-0.5 bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs font-medium rounded-full flex items-center gap-1">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> Active
                    </span>
                </div>
            </div>

            {/* Filters Row */}
            <div className="flex gap-4 mb-6">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search patients or medicine..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                    />
                </div>
                <div className="relative">
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="appearance-none px-4 py-2 pr-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-gray-900 dark:text-white"
                    >
                        <option value="all">Any Status</option>
                        <option value="scheduled">Auto-Refill Scheduled</option>
                        <option value="due_soon">Reminder Sent</option>
                        <option value="blocked">Blocked</option>
                        <option value="overdue">Overdue</option>
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>
                <div className="relative">
                    <select
                        value={medicineFilter}
                        onChange={(e) => setMedicineFilter(e.target.value)}
                        className="appearance-none px-4 py-2 pr-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-gray-900 dark:text-white"
                    >
                        <option value="all">All Medicines</option>
                        {Array.from(new Set(refills.map(r => r.medicine))).map(med => (
                            <option key={med} value={med}>{med}</option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>
            </div>

            {/* Refill Alerts Table */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden transition-colors">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 dark:bg-gray-700/50">
                            <tr className="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-100 dark:border-gray-700">
                                <th className="px-6 py-3 font-medium">Patient Name</th>
                                <th className="px-6 py-3 font-medium">Medicine</th>
                                <th className="px-6 py-3 font-medium">Dosage</th>
                                <th className="px-6 py-3 font-medium">Last Order</th>
                                <th className="px-6 py-3 font-medium">Predicted Refill</th>
                                <th className="px-6 py-3 font-medium">Triggered Agent</th>
                                <th className="px-6 py-3 font-medium">Days Limit</th>
                                <th className="px-6 py-3 font-medium">Status / Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {loading ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-8">
                                        <RefreshCw className="w-6 h-6 text-gray-400 mx-auto animate-spin" />
                                        <p className="text-gray-500 dark:text-gray-400 mt-2">Syncing with Agents...</p>
                                    </td>
                                </tr>
                            ) : paginatedRefills.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-8">
                                        <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
                                        <p className="text-gray-600 dark:text-gray-400 font-medium">No proactive alerts pending.</p>
                                    </td>
                                </tr>
                            ) : (
                                paginatedRefills.map((refill, index) => {
                                    const badge = getStatusBadge(refill.status, refill.days_remaining);

                                    return (
                                        <tr key={index} className="border-b border-gray-50 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                                            <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                                                {refill.patient_name}
                                                <div className="text-xs text-gray-400 font-normal">{refill.patient_id}</div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                                                {refill.medicine}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                                                {refill.dosage || '1 tablet/day'}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                                                {refill.last_order_date ? new Date(refill.last_order_date).toLocaleDateString() : '-'}
                                            </td>
                                            <td className="px-6 py-4 text-sm font-medium text-indigo-600 dark:text-indigo-400">
                                                {refill.refill_date ? new Date(refill.refill_date).toLocaleDateString() : 'Pending'}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                                                <div className="flex items-center gap-2">
                                                    <span>{refill.triggered_agent || 'RefillPredictionAgent'}</span>
                                                    {refill.ai_reason && (
                                                        <div className="group relative">
                                                            <Info className="w-4 h-4 text-gray-400 hover:text-indigo-500 cursor-help" />
                                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none shadow-lg">
                                                                {refill.ai_reason}
                                                                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm">
                                                <span className={refill.days_remaining < 0 ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-600 dark:text-gray-300'}>
                                                    {refill.days_remaining < 0
                                                        ? `${Math.abs(refill.days_remaining)}d overdue`
                                                        : `${refill.days_remaining}d remaining`
                                                    }
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`px-3 py-1 text-xs font-medium rounded-full border ${badge.color}`}>
                                                    {badge.label}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="px-6 py-4 flex items-center justify-between border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 transition-colors">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Showing {((currentPage - 1) * itemsPerPage) + 1}-{Math.min(currentPage * itemsPerPage, filteredRefills.length)} of {filteredRefills.length} results
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                            disabled={currentPage === 1}
                            className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                        >
                            <ChevronLeft className="w-4 h-4" />
                            Previous
                        </button>
                        <button
                            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                            disabled={currentPage === totalPages}
                            className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                        >
                            Next
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
