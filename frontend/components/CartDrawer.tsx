import { useAuth } from '@/lib/AuthContext';
import { removeFromCart } from '@/lib/firestoreService';
import { ShoppingCart, Trash2, X } from 'lucide-react';

interface CartItem {
    medicine_name: string;
    quantity: number;
    unit_price: number;
    strength?: string;
    form?: string;
}

interface CartDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    onCheckout: () => void;
    items: CartItem[]; // Received from parent
}

export default function CartDrawer({ isOpen, onClose, onCheckout, items }: CartDrawerProps) {
    const { user } = useAuth();
    
    const subtotal = items.reduce((sum, item) => sum + ((item.unit_price || 0) * (item.quantity || 1)), 0);

    const handleRemove = async (name: string) => {
        if (user) {
            await removeFromCart(user.uid, name);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
            
            {/* Drawer */}
            <div className="relative w-full max-w-md bg-white dark:bg-gray-900 h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
                <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <ShoppingCart className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        <h2 className="font-semibold text-lg text-gray-900 dark:text-white">Your Cart</h2>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors">
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                    {items.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                            <ShoppingCart className="w-12 h-12 opacity-20" />
                            <p>Your cart is empty</p>
                            <button onClick={onClose} className="text-indigo-600 hover:text-indigo-700 font-medium text-sm">
                                Continue Shopping
                            </button>
                        </div>
                    ) : (
                        items.map((item, idx) => (
                            <div key={idx} className="flex gap-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800">
                                {/* Image Placeholder */}
                                <div className="w-16 h-16 bg-white dark:bg-gray-800 rounded-lg flex items-center justify-center border border-gray-200 dark:border-gray-700">
                                    <span className="text-xl">💊</span>
                                </div>
                                
                                <div className="flex-1">
                                    <h3 className="font-medium text-gray-900 dark:text-white">{item.medicine_name}</h3>
                                    <p className="text-sm text-gray-500">{item.strength} • {item.form}</p>
                                    <div className="mt-2 flex items-center justify-between">
                                        <p className="font-semibold text-gray-900 dark:text-white">₹{item.unit_price.toFixed(2)}</p>
                                        <div className="flex items-center gap-3">
                                            <span className="text-sm text-gray-600 dark:text-gray-300">Qty: {item.quantity}</span>
                                            <button 
                                                onClick={() => handleRemove(item.medicine_name)}
                                                className="text-red-500 hover:text-red-700 p-1"
                                                title="Remove"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {items.length > 0 && (
                    <div className="p-5 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 space-y-4">
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                                <span>Subtotal</span>
                                <span>₹{subtotal.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                                <span>Delivery</span>
                                <span className="text-green-600">Free</span>
                            </div>
                            <div className="flex justify-between text-lg font-bold text-gray-900 dark:text-white pt-2 border-t border-gray-200 dark:border-gray-700">
                                <span>Total</span>
                                <span>₹{subtotal.toFixed(2)}</span>
                            </div>
                        </div>
                        <button 
                            onClick={onCheckout}
                            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold shadow-lg shadow-indigo-200 dark:shadow-none transition-all active:scale-[0.98]"
                        >
                            Proceed to Checkout
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
