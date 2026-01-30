'use client';

import { UIAction, useRealtimeVoice } from '@/lib/useRealtimeVoice';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, Loader2, Mic, Phone, PhoneOff, Volume2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface RealtimeVoiceButtonProps {
    conversationId?: string;
    onUIAction?: (action: UIAction) => void;
    onOrderPreview?: (preview: Record<string, unknown>) => void;
    onCartUpdate?: (cartData: Record<string, unknown>) => void;
    onOrderConfirmed?: (orderData: Record<string, unknown>) => void;
    className?: string;
}

/**
 * RealtimeVoiceButton - Push-to-talk voice interface
 * 
 * Uses GPT-4o-realtime-preview for action-based voice interactions.
 * When pressed and held, captures audio and sends to AI.
 * AI can trigger visual UI actions (cart updates, order previews).
 */
export default function RealtimeVoiceButton({
    conversationId,
    onUIAction,
    onOrderPreview,
    onCartUpdate,
    onOrderConfirmed,
    className = ''
}: RealtimeVoiceButtonProps) {
    const [isHolding, setIsHolding] = useState(false);
    const [showTooltip, setShowTooltip] = useState(false);
    
    // Handle UI actions from voice
    const handleUIAction = useCallback((action: UIAction) => {
        console.log('🎯 UI Action received:', action);
        
        // Call generic handler
        onUIAction?.(action);
        
        // Call specific handlers
        switch (action.action) {
            case 'show_order_preview':
                onOrderPreview?.(action.data);
                break;
            case 'update_cart':
                onCartUpdate?.(action.data);
                break;
            case 'order_confirmed':
                onOrderConfirmed?.(action.data);
                break;
        }
    }, [onUIAction, onOrderPreview, onCartUpdate, onOrderConfirmed]);
    
    const {
        isConnected,
        isConnecting,
        isListening,
        isSpeaking,
        error,
        sessionId,
        connect,
        disconnect,
        startListening,
        stopListening,
        cancelResponse
    } = useRealtimeVoice(handleUIAction);
    
    // Connect when component mounts or conversationId changes
    useEffect(() => {
        // Auto-connect is disabled - user must click to connect
    }, []);
    
    // Handle button press (start voice)
    const handlePress = useCallback(async () => {
        if (!isConnected) {
            // First press connects
            await connect(conversationId);
            return;
        }
        
        if (isSpeaking) {
            // Cancel AI response
            cancelResponse();
            return;
        }
        
        // Start listening
        setIsHolding(true);
        startListening();
    }, [isConnected, isSpeaking, connect, conversationId, cancelResponse, startListening]);
    
    // Handle button release (stop voice)
    const handleRelease = useCallback(() => {
        if (isListening) {
            setIsHolding(false);
            stopListening();
        }
    }, [isListening, stopListening]);
    
    // Handle disconnect
    const handleDisconnect = useCallback(() => {
        disconnect();
    }, [disconnect]);
    
    // Determine button state and styling
    const getButtonState = () => {
        if (isConnecting) {
            return {
                icon: <Loader2 className="w-6 h-6 animate-spin" />,
                label: 'Connecting...',
                bgClass: 'bg-yellow-500',
                pulseClass: ''
            };
        }
        
        if (!isConnected) {
            return {
                icon: <Phone className="w-6 h-6" />,
                label: 'Start Voice',
                bgClass: 'bg-indigo-600 hover:bg-indigo-700',
                pulseClass: ''
            };
        }
        
        if (isListening) {
            return {
                icon: <Mic className="w-6 h-6 text-white" />,
                label: 'Listening...',
                bgClass: 'bg-red-500',
                pulseClass: 'animate-pulse'
            };
        }
        
        if (isSpeaking) {
            return {
                icon: <Volume2 className="w-6 h-6" />,
                label: 'AI Speaking',
                bgClass: 'bg-purple-600',
                pulseClass: 'animate-pulse'
            };
        }
        
        return {
            icon: <Mic className="w-6 h-6" />,
            label: 'Hold to Speak',
            bgClass: 'bg-green-600 hover:bg-green-700',
            pulseClass: ''
        };
    };
    
    const buttonState = getButtonState();
    
    return (
        <div className={`relative inline-flex items-center gap-2 ${className}`}>
            {/* Error display */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 
                            bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 
                            px-3 py-1.5 rounded-lg text-sm whitespace-nowrap
                            flex items-center gap-2 shadow-lg"
                    >
                        <AlertCircle className="w-4 h-4" />
                        {error}
                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Main voice button */}
            <motion.button
                onMouseDown={handlePress}
                onMouseUp={handleRelease}
                onMouseLeave={handleRelease}
                onTouchStart={handlePress}
                onTouchEnd={handleRelease}
                onMouseEnter={() => setShowTooltip(true)}
                onMouseOut={() => setShowTooltip(false)}
                disabled={isConnecting}
                className={`
                    relative flex items-center justify-center
                    w-14 h-14 rounded-full
                    ${buttonState.bgClass}
                    ${buttonState.pulseClass}
                    text-white shadow-lg
                    transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed
                    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500
                `}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
            >
                {buttonState.icon}
                
                {/* Listening indicator ring */}
                {isListening && (
                    <motion.div
                        className="absolute inset-0 rounded-full border-4 border-red-300"
                        initial={{ scale: 1, opacity: 0.5 }}
                        animate={{ scale: 1.3, opacity: 0 }}
                        transition={{ duration: 1, repeat: Infinity }}
                    />
                )}
                
                {/* Speaking indicator */}
                {isSpeaking && (
                    <motion.div
                        className="absolute inset-0 rounded-full border-4 border-purple-300"
                        initial={{ scale: 1, opacity: 0.5 }}
                        animate={{ scale: 1.2, opacity: 0 }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                    />
                )}
            </motion.button>
            
            {/* Disconnect button (when connected) */}
            {isConnected && !isListening && (
                <motion.button
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    onClick={handleDisconnect}
                    className="flex items-center justify-center w-10 h-10 rounded-full
                        bg-gray-200 dark:bg-gray-700 hover:bg-red-100 dark:hover:bg-red-900/50
                        text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400
                        transition-colors shadow"
                    title="End voice session"
                >
                    <PhoneOff className="w-5 h-5" />
                </motion.button>
            )}
            
            {/* Tooltip */}
            <AnimatePresence>
                {showTooltip && !isListening && !isSpeaking && !error && (
                    <motion.div
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 5 }}
                        className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2
                            bg-gray-900 dark:bg-gray-700 text-white
                            px-3 py-1.5 rounded-lg text-sm whitespace-nowrap
                            shadow-lg"
                    >
                        {buttonState.label}
                        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1
                            border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
                    </motion.div>
                )}
            </AnimatePresence>
            
            {/* Session indicator */}
            {isConnected && (
                <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span>Voice Active</span>
                </div>
            )}
        </div>
    );
}
