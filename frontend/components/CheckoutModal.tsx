import { Check, Loader2, MapPin, ScanLine, Truck, X } from 'lucide-react';
import { useState } from 'react';
import QRCode from 'react-qr-code';

interface CheckoutModalProps {
    isOpen: boolean;
    onClose: () => void;
    items: any[];
    total: number;
    onConfirm: (method: string) => Promise<void>;
}

export default function CheckoutModal({ isOpen, onClose, items, total, onConfirm }: CheckoutModalProps) {
    const [step, setStep] = useState<'review' | 'payment'>('review');
    const [paymentMethod, setPaymentMethod] = useState<'cod' | 'upi'>('cod');
    const [processing, setProcessing] = useState(false);

    if (!isOpen) return null;

    const handleConfirm = async () => {
        setProcessing(true);
        await onConfirm(paymentMethod);
        setProcessing(false);
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
            
            <div className="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50 dark:bg-gray-800/50">
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                        {step === 'review' ? 'Order Summary' : 'Secure Payment'}
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition-colors">
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    {step === 'review' ? (
                        <div className="space-y-6">
                            {/* Address Mock */}
                            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
                                <div className="flex items-start gap-3">
                                    <MapPin className="w-5 h-5 text-indigo-600 mt-0.5" />
                                    <div>
                                        <h3 className="font-semibold text-gray-900 dark:text-white">Delivery Address</h3>
                                        <p className="text-sm text-gray-500 mt-1">102, Galaxy Apartments, Cyber City<br/>Gurugram, HR 122002</p>
                                        <button className="text-xs text-indigo-600 font-medium mt-2 hover:underline">Change</button>
                                    </div>
                                </div>
                            </div>

                            {/* Items Summary */}
                            <div className="space-y-3">
                                <h3 className="font-semibold text-sm text-gray-900 dark:text-white uppercase tracking-wider">Items</h3>
                                <div className="max-h-48 overflow-y-auto space-y-2">
                                    {items.map((item, i) => (
                                        <div key={i} className="flex justify-between text-sm">
                                            <span className="text-gray-600 dark:text-gray-300">{item.medicine_name} x{item.quantity}</span>
                                            <span className="font-medium">₹{(item.unit_price * item.quantity).toFixed(2)}</span>
                                        </div>
                                    ))}
                                </div>
                                <div className="pt-3 border-t border-dashed border-gray-300 dark:border-gray-700 flex justify-between font-bold text-lg text-indigo-600">
                                    <span>Total Payable</span>
                                    <span>₹{total.toFixed(2)}</span>
                                </div>
                            </div>

                            <button 
                                onClick={() => setStep('payment')}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg shadow-indigo-200 dark:shadow-none transition-all"
                            >
                                Proceed to Payment
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Method Selection */}
                            <div className="grid grid-cols-2 gap-4">
                                <button 
                                    onClick={() => setPaymentMethod('cod')}
                                    className={`p-4 rounded-xl border-2 flex flex-col items-center gap-2 transition-all ${
                                        paymentMethod === 'cod' 
                                        ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300' 
                                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 text-gray-700 dark:text-gray-200'
                                    }`}
                                >
                                    <Truck className="w-6 h-6" />
                                    <span className="font-semibold text-sm">Cash on Delivery</span>
                                </button>
                                <button 
                                    onClick={() => setPaymentMethod('upi')}
                                    className={`p-4 rounded-xl border-2 flex flex-col items-center gap-2 transition-all ${
                                        paymentMethod === 'upi' 
                                        ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300' 
                                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 text-gray-700 dark:text-gray-200'
                                    }`}
                                >
                                    <ScanLine className="w-6 h-6" />
                                    <span className="font-semibold text-sm">UPI / QR</span>
                                </button>
                            </div>

                            {/* Dynamic Content */}
                            <div className="min-h-[200px] flex flex-col items-center justify-center p-4 bg-gray-50 dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                                {paymentMethod === 'upi' ? (
                                    <div className="text-center space-y-4 w-full">
                                        <div className="bg-white p-3 rounded-lg inline-block shadow-sm">
                                            <QRCode 
                                                value={`upi://pay?pa=8208516765@upi&pn=PharmAgent&am=${total.toFixed(2)}&tr=ORDER-${Date.now()}&cu=INR`}
                                                size={160}
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <div className="flex items-center justify-center gap-2 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded cursor-pointer hover:bg-gray-200 transition-colors"
                                                 title="Click to copy"
                                                 onClick={() => navigator.clipboard.writeText("8208516765@upi")}>
                                                <p className="font-mono text-sm">8208516765@upi</p>
                                                <span className="text-[10px] text-indigo-500">COPY</span>
                                            </div>
                                            <p className="text-xs text-gray-500 pt-1">Scan with GPay, PhonePe, Paytm</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center space-y-2 text-gray-600 dark:text-gray-300">
                                        <Truck className="w-12 h-12 mx-auto text-gray-400" />
                                        <p>Pay cash when your order arrives.</p>
                                        <p className="text-xs text-indigo-600">Verified for immediate dispatch.</p>
                                    </div>
                                )}
                            </div>

                            <button 
                                onClick={handleConfirm}
                                disabled={processing}
                                className={`w-full py-3.5 rounded-xl font-bold shadow-lg transition-all flex items-center justify-center gap-2 ${
                                    paymentMethod === 'upi'
                                    ? 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-green-200'
                                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-200'
                                }`}
                            >
                                {processing ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        {paymentMethod === 'upi' ? (
                                            <>
                                                <Check className="w-5 h-5" />
                                                I have completed the payment
                                            </>
                                        ) : (
                                            "Confirm Order"
                                        )}
                                    </>
                                )}
                            </button>
                            
                            {paymentMethod === 'upi' && (
                                <p className="text-[10px] text-center text-gray-400 uppercase tracking-wide">
                                    Demo Mode: Payment verification simulated for prototype
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
