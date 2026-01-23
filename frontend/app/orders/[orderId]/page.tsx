'use client';

import { useAuth } from '@/lib/AuthContext';
import { ArrowLeft, Check, CheckCircle, Clock, Package, ShieldCheck, Truck } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface OrderDetails {
    orderId: string;
    medicine: string;
    status: string;
    orderedAt: string;
    quantity: number;
    dosage?: string;
    supplyDays?: number;
    priceBreakdown?: {
        subtotal: number;
        tax: number;
        delivery: number;
        total: number;
    };
    metadata?: any;
}

export default function OrderDetailsPage({ params }: { params: { orderId: string } }) {
    const { user, loading } = useAuth();
    const router = useRouter();
    const [order, setOrder] = useState<OrderDetails | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!loading && user) {
            fetchOrderDetails();
        }
    }, [user, loading, params.orderId]);

    const fetchOrderDetails = async () => {
        try {
            const token = await user?.getIdToken();
            const response = await fetch(`http://localhost:8000/orders/${params.orderId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setOrder(data);
            } else {
                setError('Order not found');
            }
        } catch (error) {
            console.error('Error fetching order details:', error);
            setError('Failed to load order');
        } finally {
            setIsLoading(false);
        }
    };

    // Timeline Steps Logic
    const getTimelineSteps = (status: string) => {
        const s = status ? status.toUpperCase() : '';
        const steps = [
            { id: 1, label: 'Order Requested', icon: Clock, desc: 'Agent received request' },
            { id: 2, label: 'Safety Check', icon: ShieldCheck, desc: 'Policy validation passed' },
            { id: 3, label: 'Confirmed', icon: CheckCircle, desc: 'Order confirmed by user' },
            { id: 4, label: 'Shipped', icon: Truck, desc: 'Out for delivery' },
            { id: 5, label: 'Delivered', icon: Package, desc: 'Arrived at destination' },
        ];

        // Determine current step index based on status
        let currentStepIndex = 2; // Default to Confirmed since we only save confirmed orders
        if (s === 'SHIPPED') currentStepIndex = 3;
        if (s === 'DELIVERED') currentStepIndex = 4;

        return steps.map((step, index) => ({
            ...step,
            completed: index <= currentStepIndex,
            current: index === currentStepIndex
        }));
    };

    if (loading || isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-20 px-4 sm:px-6">
                <div className="max-w-3xl mx-auto h-96 bg-white dark:bg-gray-800 rounded-xl animate-pulse" />
            </div>
        );
    }

    if (error || !order) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-24 px-4 text-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Order not found</h2>
                <Link href="/orders" className="text-indigo-600 mt-4 inline-block hover:underline">
                    Back to Orders
                </Link>
            </div>
        );
    }

    const timeline = getTimelineSteps(order.status);
    const price = order.priceBreakdown || {
        // Fallback based on typical unit price (₹10) if breakdown missing
        subtotal: order.quantity * 10,
        tax: order.quantity * 10 * 0.05,
        delivery: 40.00,
        total: (order.quantity * 10) * 1.05 + 40.00
    };

    return (
        <main className="min-h-screen bg-gray-50 dark:bg-gray-900 pt-24 px-4 sm:px-6 pb-12">
            <div className="max-w-3xl mx-auto">
                <Link
                    href="/orders"
                    className="inline-flex items-center text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white mb-6"
                >
                    <ArrowLeft className="w-4 h-4 mr-1" />
                    Back to Orders
                </Link>

                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    {/* Header */}
                    <div className="p-6 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                            <div>
                                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                                    Order #{order.orderId}
                                </h1>
                                <p className="text-sm text-gray-500 mt-1">
                                    Placed on {new Date(order.orderedAt).toLocaleString()}
                                </p>
                            </div>
                            <div className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-full text-sm font-medium">
                                {order.status}
                            </div>
                        </div>
                    </div>

                    <div className="p-6 space-y-8">
                        {/* Timeline */}
                        <div className="relative">
                            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-100 dark:bg-gray-700" />
                            <div className="space-y-8 relative">
                                {timeline.map((step) => (
                                    <div key={step.id} className="flex gap-4">
                                        <div className={`relative z-10 w-16 flex-none flex flex-col items-center`}>
                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors ${step.completed
                                                    ? 'bg-emerald-500 border-emerald-500 text-white'
                                                    : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-300'
                                                }`}>
                                                {step.completed ? <Check className="w-4 h-4" /> : <step.icon className="w-4 h-4" />}
                                            </div>
                                        </div>
                                        <div className={`pt-1 ${step.completed ? 'opacity-100' : 'opacity-40'}`}>
                                            <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                                                {step.label}
                                            </h3>
                                            <p className="text-xs text-gray-500 mt-0.5">
                                                {step.desc}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <hr className="border-gray-100 dark:border-gray-700" />

                        {/* Order Items */}
                        <div>
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Items Ordered</h3>
                            <div className="flex items-center gap-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                                <div className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                                    <Package className="w-6 h-6 text-indigo-600" />
                                </div>
                                <div>
                                    <div className="font-medium text-gray-900 dark:text-white">
                                        {order.medicine}
                                    </div>
                                    <div className="text-sm text-gray-500">
                                        {order.quantity} units {order.dosage && `• ${order.dosage}`}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Price Breakdown */}
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6">
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Payment Summary</h3>
                            <div className="space-y-3 text-sm">
                                <div className="flex justify-between text-gray-600 dark:text-gray-300">
                                    <span>Subtotal</span>
                                    <span>₹{price.subtotal.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-gray-600 dark:text-gray-300">
                                    <span>Tax</span>
                                    <span>₹{price.tax.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-gray-600 dark:text-gray-300">
                                    <span>Delivery</span>
                                    <span>₹{price.delivery.toFixed(2)}</span>
                                </div>
                                <div className="border-t border-gray-200 dark:border-gray-700 pt-3 flex justify-between font-bold text-gray-900 dark:text-white text-base">
                                    <span>Total</span>
                                    <span>₹{price.total.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
