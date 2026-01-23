'use client';

import { useAuth } from '@/lib/AuthContext';
import { CheckCircle, Package, Truck } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface OrderItem {
    medicine_name: string;
    quantity: number;
    strength?: string;
    unit_price?: number;
}

interface Order {
    orderId: string;
    medicine: string;       // Backward-compatible (first item name)
    items?: OrderItem[];    // Full items array for multi-item orders
    itemCount?: number;     // Quick count of items
    status: string;
    orderedAt: string;
    quantity: number;
    dosage?: string;
    totalAmount?: number;
}

export default function MyOrdersPage() {
    const { user, userRole, loading } = useAuth();
    const router = useRouter();
    const [orders, setOrders] = useState<Order[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!loading && user) {
            if (userRole !== 'customer') {
                // Double check protection (handled by AuthGuard but good to have)
                return;
            }
            fetchOrders();
        }
    }, [user, userRole, loading]);

    const fetchOrders = async () => {
        try {
            const token = await user?.getIdToken();
            const response = await fetch('http://localhost:8000/orders', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setOrders(data.orders || []);
            }
        } catch (error) {
            console.error('Error fetching orders:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        const s = status.toUpperCase();
        if (s === 'DELIVERED') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
        if (s === 'SHIPPED') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
        if (s === 'CONFIRMED') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'; // Processing/Ordered
    };

    const getStatusIcon = (status: string) => {
        const s = status.toUpperCase();
        if (s === 'DELIVERED') return <CheckCircle className="w-4 h-4" />;
        if (s === 'SHIPPED') return <Truck className="w-4 h-4" />;
        return <Package className="w-4 h-4" />;
    };

    if (loading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-20 px-4 sm:px-6">
                <div className="max-w-4xl mx-auto space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-32 bg-white dark:bg-gray-800 rounded-xl animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-24 px-4 sm:px-6 pb-12">
            <div className="max-w-4xl mx-auto">
                <header className="mb-8">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">My Orders</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">Track and manage your medicine orders</p>
                </header>

                <div className="space-y-4">
                    {orders.length === 0 ? (
                        <div className="text-center py-20 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                            <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white">No orders yet</h3>
                            <p className="text-gray-500 dark:text-gray-400 mt-1">Start a conversation to place your first order.</p>
                            <Link
                                href="/"
                                className="inline-block mt-6 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
                            >
                                Go to Chat
                            </Link>
                        </div>
                    ) : (
                        orders.map((order) => (
                            <div
                                key={order.orderId}
                                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow"
                            >
                                <div className="p-6">
                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
                                            <div className="flex items-center gap-3">
                                            <div className="w-12 h-12 rounded-lg overflow-hidden bg-white flex-shrink-0 shadow-sm border border-gray-200 dark:border-gray-600">
                                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                                <img
                                                    src={(() => {
                                                        // Get form from first item if available
                                                        const firstItem = order.items?.[0];
                                                        const form = ((firstItem as any)?.form || 'tablet').toLowerCase();
                                                        if (form.includes('capsule')) return '/medicines/capsule.png';
                                                        if (form.includes('inhaler')) return '/medicines/inhaler.png';
                                                        if (form.includes('pen') || form.includes('insulin')) return '/medicines/pen.png';
                                                        if (form.includes('softgel') || form.includes('gel')) return '/medicines/softgel.png';
                                                        return '/medicines/tablet.png';
                                                    })()}
                                                    alt={order.medicine}
                                                    className="w-full h-full object-cover"
                                                />
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-gray-900 dark:text-white">
                                                    {order.medicine}
                                                    {(order.itemCount && order.itemCount > 1) && (
                                                        <span className="ml-2 text-xs font-normal text-gray-500">
                                                            +{order.itemCount - 1} more
                                                        </span>
                                                    )}
                                                </h3>
                                                <p className="text-sm text-gray-500">
                                                    Order #{order.orderId} • {new Date(order.orderedAt).toLocaleDateString()}
                                                </p>
                                            </div>
                                        </div>
                                        <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${getStatusColor(order.status)}`}>
                                            {getStatusIcon(order.status)}
                                            {order.status}
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between border-t border-gray-100 dark:border-gray-700 pt-4 mt-4">
                                        <div className="text-sm text-gray-600 dark:text-gray-300">
                                            {order.items && order.items.length > 1
                                                ? `${order.items.length} items`
                                                : `${order.quantity} units`
                                            }
                                            {order.dosage && ` • ${order.dosage}`}
                                            {order.totalAmount && ` • ₹${order.totalAmount.toFixed(2)}`}
                                        </div>
                                        <Link
                                            href={`/orders/${order.orderId}`}
                                            className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 hover:underline"
                                        >
                                            View Details →
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </main>
    );
}
