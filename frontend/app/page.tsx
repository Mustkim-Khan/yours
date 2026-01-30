'use client';

import CartDrawer from '@/components/CartDrawer';
import CheckoutModal from '@/components/CheckoutModal';
import ExplainMedicineCard from '@/components/ExplainMedicineCard';
import PrescriptionUploadCard from '@/components/PrescriptionUploadCard';
import { OrderCelebration, VoiceWave } from '@/components/ui';
import RealtimeVoiceButton from '@/components/ui/RealtimeVoiceButton';
import { useAuth } from '@/lib/AuthContext';
import { createNewConversation, deleteConversation, getArchivedConversations, getConversationEntities, getOrCreateConversation, loadMessages, saveMessage, subscribeToCart, updateConversationEntities } from '@/lib/firestoreService';
import { ChevronRight, Clock, Loader2, Mic, Paperclip, Send, Settings, Trash2, Truck, User, Volume2, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface Patient {
    patient_id: string;
    patient_name: string;
    patient_email: string;
    patient_phone: string;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    extractedEntities?: any;
    safetyResult?: any;
    orderPreview?: any;
    order?: any;
    traceUrl?: string;
    aiAnnotation?: string;
    badges?: { label: string; color: string }[];
    expandable?: boolean;
    prescriptionUpload?: any;
}

// Helper function to format markdown content (bold, newlines)
const formatMarkdown = (text: string): string => {
    if (!text) return '';
    // Convert **bold** to <strong>bold</strong>
    let formatted = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
};

export default function ChatPage() {
    const [patients, setPatients] = useState<Patient[]>([]);
    const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [currentEntities, setCurrentEntities] = useState<any>(null);
    const [latestTraceUrl, setLatestTraceUrl] = useState<string | null>(null);
    const [autoSaveChats, setAutoSaveChats] = useState(true);
    const [desktopNotifications, setDesktopNotifications] = useState(false);
    const [prescriptionVerified, setPrescriptionVerified] = useState(false); // Track if prescription is verified
    const [conversationId, setConversationId] = useState<string | null>(null); // Firestore conversation ID
    const [pendingPillImage, setPendingPillImage] = useState<{file: File, base64: string} | null>(null); // Pending pill image for identification
    
    // Cart State
    const [isCartOpen, setIsCartOpen] = useState(false);
    const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
    const [cartItems, setCartItems] = useState<any[]>([]);

    // Archive State
    const [isArchiveExpanded, setIsArchiveExpanded] = useState(true);
    const [archivedConversations, setArchivedConversations] = useState<{
        id: string;
        title: string;
        lastMessagePreview: string;
        lastMessageAt: Date;
    }[]>([]);
    const [isLoadingArchive, setIsLoadingArchive] = useState(false);
    const [orderCelebrationStatus, setOrderCelebrationStatus] = useState<'PENDING' | 'CONFIRMED' | 'CANCELLED' | null>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const pillImageInputRef = useRef<HTMLInputElement>(null);  // Pill identification image input
    const prescriptionCalledRef = useRef<Set<string>>(new Set()); // Track which messages have had prescription API called
    const deletedConversationIdsRef = useRef<Set<string>>(new Set()); // Track deleted conversation IDs to filter out

    // Get authenticated user and name
    const { user, userName, idToken } = useAuth();

    // CRITICAL: Reset ALL state when user changes to prevent entity leakage between users
    useEffect(() => {
        // Reset extracted entities
        setCurrentEntities(null);
        // Reset messages
        setMessages([]);
        // Reset conversation
        setConversationId(null);
        // Reset prescription state
        setPrescriptionVerified(false);
        prescriptionCalledRef.current.clear();
        console.log('[Auth] User changed, reset all entity/conversation state');
    }, [user?.uid]);

    useEffect(() => {
        fetchPatients();
    }, []);

    // Load messages from Firestore when patient changes
    useEffect(() => {
        if (selectedPatient && user) {
            loadConversationHistory(user.uid, selectedPatient.patient_id);

            // Reset prescription state for new patient
            setPrescriptionVerified(false);
            prescriptionCalledRef.current.clear();
        }
    }, [selectedPatient?.patient_id, user?.uid]);

    // Cart Subscription
    useEffect(() => {
        if (user?.uid) {
            const unsubscribe = subscribeToCart(user.uid, (data) => {
                setCartItems(data.items || []);
            });
            return () => unsubscribe();
        }
    }, [user?.uid]);

    // Load archived conversations when user logs in
    useEffect(() => {
        const loadArchive = async () => {
            if (!user?.uid) {
                setArchivedConversations([]);
                return;
            }
            
            setIsLoadingArchive(true);
            try {
                const archived = await getArchivedConversations(user.uid);
                console.log('[Archive Load] Fetched from Firestore:', archived.map(c => c.id));
                console.log('[Archive Load] Deleted IDs to filter:', Array.from(deletedConversationIdsRef.current));
                
                // Filter out any deleted conversations that might come back due to eventual consistency
                const filtered = archived.filter(c => !deletedConversationIdsRef.current.has(c.id));
                console.log('[Archive Load] After filtering:', filtered.map(c => c.id));
                
                setArchivedConversations(filtered);
            } catch (err) {
                console.error('[Archive] Failed to load:', err);
            } finally {
                setIsLoadingArchive(false);
            }
        };
        
        loadArchive();
    }, [user?.uid]);

    // Refresh archive when conversation changes (to update titles/previews)
    useEffect(() => {
        const refreshArchive = async () => {
            if (!user?.uid) return;
            
            // Get current deleted IDs before async operation
            const deletedIds = new Set(deletedConversationIdsRef.current);
            console.log('[Archive Refresh] Deleted IDs to filter:', Array.from(deletedIds));
            
            // Small delay to allow Firestore writes to complete
            await new Promise(r => setTimeout(r, 500));
            const archived = await getArchivedConversations(user.uid);
            console.log('[Archive Refresh] Fetched from Firestore:', archived.map(c => c.id));
            
            // Filter out any deleted conversations that might come back due to eventual consistency
            const filtered = archived.filter(c => !deletedIds.has(c.id) && !deletedConversationIdsRef.current.has(c.id));
            console.log('[Archive Refresh] After filtering:', filtered.map(c => c.id));
            
            setArchivedConversations(filtered);
        };
        
        if (conversationId && messages.length > 0) {
            refreshArchive();
        }
    }, [conversationId, messages.length, user?.uid]);

    // Load conversation history from Firestore
    const loadConversationHistory = async (userId: string, patientId: string) => {
        setIsLoading(true);
        try {
            // 1. Get or create conversation (Simplifying to avoid complex index requirements)
            // previously getLatestConversation failed due to missing index for orderBy('updatedAt')
            const convId = await getOrCreateConversation(userId, patientId);

            if (!convId) throw new Error('Failed to obtain conversation ID');

            setConversationId(convId);
            console.log('[Firestore] Conversation ID set:', convId);

            // 2. Load messages
            const firestoreMessages = await loadMessages(convId);
            const formattedMessages: Message[] = firestoreMessages.map((msg, index) => ({
                id: `hist-${index}`,
                role: msg.sender === 'user' ? 'user' : 'assistant',
                content: msg.text,
                timestamp: msg.timestamp?.toDate() || new Date(),
                // Restore rich metadata if available
                ...(msg.metadata || {})
            }));
            setMessages(formattedMessages);
            console.log('[Firestore] Loaded', formattedMessages.length, 'messages');

            // 3. Load extracted entities state
            const persistedEntities = await getConversationEntities(convId);
            if (persistedEntities) {
                setCurrentEntities(persistedEntities);
            } else {
                setCurrentEntities(null); // Ensure clean state if none found
            }

        } catch (e: any) {
            console.error('[Firestore] Error loading history:', e);
            setMessages([]);
            setCurrentEntities(null);
        } finally {
            setIsLoading(false);
        }
    };

    // Save entities to localStorage whenever they change


    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Dropdown click outside effect removed
    /*
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsPatientDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);
    */

    // Listen for custom "send-message" events from components
    useEffect(() => {
        const handleSendMessage = (event: CustomEvent<string>) => {
            sendMessage(event.detail);
        };
        const handleOpenCart = () => {
             setIsCartOpen(true);
        };

        document.addEventListener('send-message', handleSendMessage as EventListener);
        document.addEventListener('open-cart', handleOpenCart);
        
        return () => {
            document.removeEventListener('send-message', handleSendMessage as EventListener);
            document.removeEventListener('open-cart', handleOpenCart);
        };
    }, [selectedPatient, isLoading]); // Re-bind when deps change

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchPatients = async () => {
        try {
            const res = await fetch('/api/patients');
            const data = await res.json();
            setPatients(data);

            // Try to restore previous selection
            const savedPatientId = localStorage.getItem('selected_patient_id');
            const savedPatient = data.find((p: Patient) => p.patient_id === savedPatientId);

            if (savedPatient) {
                setSelectedPatient(savedPatient);
            } else if (data.length > 0) {
                // Default to first patient if no save found
                setSelectedPatient(data[0]);
                localStorage.setItem('selected_patient_id', data[0].patient_id);
            }
        } catch (error) {
            console.error('Failed to fetch patients:', error);
        }
    };

    const handlePatientChange = (patient: Patient) => {
        setSelectedPatient(patient);
        localStorage.setItem('selected_patient_id', patient.patient_id);
        // Messages will be loaded from localStorage by the useEffect when selectedPatient changes
    };

    const sendMessage = async (text: string) => {
        if (!text.trim() || !selectedPatient || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);
        // setCurrentEntities(null); // Removed to persist entities across turns

        // Save user message to Firestore (only text, no agent data)
        if (conversationId) {
            console.log('[Firestore] Saving user message to:', conversationId);
            saveMessage(conversationId, { sender: 'user', text, type: 'chat' })
                .catch(err => console.error('[Firestore] Failed to save user message:', err));
        } else {
            console.error('[Firestore] CRITICAL: No conversationId set! Message will NOT be saved.');
        }

        try {
            // Build conversation history from previous messages
            const conversationHistory = messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {})
                },
                body: JSON.stringify({
                    patient_id: selectedPatient.patient_id,
                    message: text,
                    session_id: `session-${selectedPatient.patient_id}`,
                    conversation_history: conversationHistory,
                    user_name: userName || undefined, // Pass user name for agent greeting
                    conversation_id: conversationId || undefined, // Pass Firestore conversation ID for memory
                }),
            });


            const data = await res.json();

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response,
                timestamp: new Date(),
                extractedEntities: data.extracted_entities, // We store this in metadata
                safetyResult: data.safety_result,
                orderPreview: data.order_preview,
                order: data.order_confirmation, // Backend sends order_confirmation
                traceUrl: data.trace_url,
                aiAnnotation: data.ai_annotation,
                badges: data.badges,
                expandable: true,
                prescriptionUpload: data.prescription_upload,
            };

            setMessages(prev => [...prev, assistantMessage]);

            // Save assistant message to Firestore with RICH METADATA
            if (conversationId) {
                const messageType = data.order_confirmation ? 'order_summary' : 'chat';

                // Construct metadata strictly for UI reconstruction
                // Firestore throws if any value is 'undefined', so we must default to null
                const metadata = {
                    extractedEntities: data.extracted_entities || null,
                    safetyResult: data.safety_result || null,
                    orderPreview: data.order_preview || null,
                    order: data.order_confirmation || null, // Backend sends order_confirmation
                    traceUrl: data.trace_url || null,
                    aiAnnotation: data.ai_annotation || null,
                    badges: data.badges || null,
                    prescriptionUpload: data.prescription_upload || null,
                };

                saveMessage(conversationId, {
                    sender: 'assistant',
                    text: data.response,
                    type: messageType,
                    metadata: metadata // Persist rich data
                }).catch(err => console.error('[Firestore] Failed to save assistant message:', err));
            }

            // Logic to persist or update extracted entities
            // Priority: 1) extracted_entities, 2) order_preview items, 3) confirmed order items
            let newEntities = null;
            if (data.extracted_entities && data.extracted_entities.entities && data.extracted_entities.entities.length > 0) {
                // 1. If new entities are extracted directly, update the view
                newEntities = data.extracted_entities;
                setCurrentEntities(newEntities);
            } else if (data.order_preview && data.order_preview.items && data.order_preview.items.length > 0) {
                // 2. If order preview is returned, extract entities from preview items
                newEntities = {
                    entities: data.order_preview.items.map((item: any) => ({
                        medicine: item.medicine_name,
                        dosage: item.strength || '-',
                        quantity: item.quantity,
                        frequency: null,
                        duration: item.supply_days ? `${item.supply_days} days` : null,
                        prescription_required: item.prescription_required,
                        stock_status: 'OK'  // If we have a preview, stock is OK
                    }))
                };
                setCurrentEntities(newEntities);
            } else if (data.order) {
                // 3. If order is confirmed, persist the confirmed items as entities
                const confirmedEntities = {
                    entities: data.order.items.map((item: any) => ({
                        medicine: item.medicine_name,
                        dosage: item.strength || '-',
                        quantity: item.quantity,
                        frequency: null,
                        duration: null,
                        prescription_required: null,
                        stock_status: 'OK'
                    }))
                };
                newEntities = confirmedEntities;
                setCurrentEntities(confirmedEntities);
            }

            // PERSIST ENTITIES TO FIRESTORE IMMEDIATELY
            if (newEntities && conversationId) {
                updateConversationEntities(conversationId, newEntities)
                    .catch(err => console.error('[Firestore] Failed to persist entities:', err));
            }
            // 4. Otherwise, keep existing entities (Propagates persistence)

            // Trigger Order Celebration when order is confirmed
            if (data.order_confirmation) {
                setOrderCelebrationStatus('CONFIRMED');
            }

            if (data.trace_url) {
                setLatestTraceUrl(data.trace_url);
            }

        } catch (error) {
            console.error('Failed to send message:', error);
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                timestamp: new Date(),
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        sendMessage(inputValue);
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunksRef.current.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                const reader = new FileReader();
                reader.onloadend = async () => {
                    const base64Audio = (reader.result as string).split(',')[1];
                    await sendVoiceMessage(base64Audio);
                };
                reader.readAsDataURL(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const cancelRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.onstop = null; // Prevent sending
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            audioChunksRef.current = [];
        }
    };

    const sendVoiceMessage = async (audioBase64: string) => {
        if (!selectedPatient) return;
        setIsLoading(true);

        try {
            const res = await fetch('/api/voice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {})
                },
                body: JSON.stringify({
                    audio_base64: audioBase64,
                    patient_id: selectedPatient.patient_id,
                    session_id: `session-${selectedPatient.patient_id}`,
                }),
            });

            const data = await res.json();

            if (data.transcript) {
                setMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    role: 'user',
                    content: data.transcript,
                    timestamp: new Date(),
                }]);
            }

            const chatResponse = data.chat_response;
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: chatResponse.message,
                timestamp: new Date(),
                extractedEntities: chatResponse.extracted_entities,
                safetyResult: chatResponse.safety_result,
                orderPreview: chatResponse.order_preview,
                order: chatResponse.order,
                traceUrl: chatResponse.trace_url,
            }]);

            if (data.audio_response_base64) {
                const audio = new Audio(`data:audio/mp3;base64,${data.audio_response_base64}`);
                audio.play();
            }

        } catch (error) {
            console.error('Failed to process voice:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // Handle pill image selection (store for preview, don't send yet)
    const handlePillImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Reset file input for re-selection
        e.target.value = '';

        // Convert to base64 and store for preview
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64 = reader.result as string;
            setPendingPillImage({ file, base64 });
        };
        reader.readAsDataURL(file);
    };

    // Cancel pending pill image
    const cancelPillImage = () => {
        setPendingPillImage(null);
    };

    // Send message with optional pill image
    const sendMessageWithImage = async () => {
        if (!selectedPatient || isLoading) return;
        if (!inputValue.trim() && !pendingPillImage) return;

        const userText = inputValue.trim() || 'What is this pill?';
        const imageToSend = pendingPillImage;
        
        // Clear input and pending image
        setInputValue('');
        setPendingPillImage(null);

        // Show user message with image indicator
        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: imageToSend ? `📷 [Pill Image] ${userText}` : userText,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);

        // Save user message to Firestore
        if (conversationId) {
            saveMessage(conversationId, { sender: 'user', text: userMessage.content, type: 'chat' })
                .catch(err => console.error('[Firestore] Failed to save user message:', err));
        }

        try {
            if (imageToSend) {
                // Call pill identification API
                const res = await fetch('/api/pill/identify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {})
                    },
                    body: JSON.stringify({
                        image_base64: imageToSend.base64,
                        session_id: `session-${selectedPatient.patient_id}`,
                        patient_id: selectedPatient.patient_id,
                        user_question: userText,
                    }),
                });

                const data = await res.json();

                const resultMessage: Message = {
                    id: (Date.now() + 1).toString(),
                    role: 'assistant',
                    content: data.message + '\n\n' + data.disclaimer,
                    timestamp: new Date(),
                    aiAnnotation: data.pharmacist_message || undefined,
                    badges: data.success && data.top_match ? [
                        { label: `Confidence: ${data.top_match.confidence}`, color: data.top_match.confidence === 'high' ? 'green' : 'yellow' }
                    ] : undefined,
                };
                setMessages(prev => [...prev, resultMessage]);

                // If successful, inject into extracted entities
                if (data.success && data.top_match) {
                    const match = data.top_match;
                    setCurrentEntities({
                        entities: [{
                            medicine: match.name,
                            dosage: match.strength || '-',
                            quantity: null,
                            frequency: null,
                            duration: null,
                            prescription_required: null,
                            stock_status: 'Pending Check'
                        }]
                    });
                }

                // Save to Firestore
                if (conversationId) {
                    saveMessage(conversationId, {
                        sender: 'assistant',
                        text: resultMessage.content,
                        type: 'chat',
                        metadata: { pillIdentification: data }
                    }).catch(err => console.error('[Firestore] Failed to save pill ID message:', err));
                }
            } else {
                // Regular text message - use existing sendMessage logic
                await sendMessage(userText);
            }
        } catch (error) {
            console.error('Failed to process message:', error);
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: '❌ Failed to process your request. Please try again.',
                timestamp: new Date(),
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    // Mock extracted entities for display
    const displayEntities = currentEntities?.entities?.[0] || null;

    return (
        <div className="flex flex-1 h-full min-h-0 overflow-hidden">
            {/* Order Celebration Confetti */}
            <OrderCelebration 
                orderStatus={orderCelebrationStatus} 
                onComplete={() => setOrderCelebrationStatus(null)} 
            />
            {/* Left Panel - Patient Context */}
            <aside className="w-80 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col overflow-y-auto transition-colors duration-300">
                {/* Patient Context Section */}
                <div className="p-6 border-b border-gray-200 dark:border-gray-800">
                    <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 mb-1">
                        <User className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Patient Context</span>
                    </div>

                    {/* Patient Context Display (Static) */}
                    <div className="relative mt-2">
                        <div
                            className="w-full flex items-center gap-3 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                        >
                            <div className="w-10 h-10 rounded-full overflow-hidden bg-white flex-shrink-0 border border-gray-200 dark:border-gray-600">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                    src={(() => {
                                        const name = (userName || 'Guest').split(' ')[0].toLowerCase();
                                        if (['sh', 'h', 'n', 'k', 'r', 't'].some(end => name.endsWith(end))) return '/avatars/male.png';
                                        if (['a', 'i', 'y'].some(end => name.endsWith(end))) return '/avatars/female.png';
                                        return '/avatars/neutral.png';
                                    })()}
                                    alt="Patient avatar"
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <span className="flex-1 text-left text-sm font-medium text-gray-900 dark:text-white">
                                {userName || "Guest"}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Extracted Entities Section */}
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Extracted Entities</h3>

                    <div className="space-y-3">
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">Medicine:</p>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-200">
                                {displayEntities?.medicine || '-'}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">Dosage:</p>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-200">
                                {displayEntities?.dosage || '-'}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">Quantity:</p>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-200">
                                {displayEntities?.quantity ? `${displayEntities.quantity} tablets` : '-'}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">Supply Duration:</p>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-200">
                                {displayEntities?.duration || '-'}
                            </p>
                        </div>

                        {/* Badges - show empty state when no entities */}
                        <div className="flex gap-2 mt-2">
                            <span className="px-2 py-1 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs font-medium rounded">
                                Prescription: {displayEntities?.prescription_required ? 'Yes' : '-'}
                            </span>
                            <span className="px-2 py-1 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs font-medium rounded">
                                Stock: {displayEntities?.stock_status || '-'}
                            </span>
                        </div>
                    </div>
                </div>

            </aside>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-h-0 bg-gray-50 dark:bg-gray-950 transition-colors duration-300">
                {/* Chat Header */}
                <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-4 transition-colors duration-300 flex justify-between items-center">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Conversational Log</h2>
                    

                </div>

                {/* AI Prediction Banner */}
                {/* AI Prediction Banner Removed */}

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                    {messages.map((message) => (
                        <div key={message.id} className={`flex gap-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {/* AI Pharmacist Avatar - left side for assistant */}
                            {message.role === 'assistant' && (
                                <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden border-2 border-indigo-400 shadow-sm self-end">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                        src="/ai-pharmacist-smile.jpg"
                                        alt="AI Pharmacist"
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            )}
                            
                            {/* Message Content */}
                            <div className={`max-w-md`}>
                                {/* Message Bubble */}
                                <div className={`px-4 py-2 rounded-2xl ${message.role === 'user'
                                    ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-br-md shadow-md'
                                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-md shadow-sm'
                                    }`}>
                                    <p className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }} />
                                </div>

                                {/* AI Annotation */}
                                {message.role === 'assistant' && message.aiAnnotation && (
                                    <div className="mt-1 flex items-start gap-1 text-xs text-gray-500 dark:text-gray-400">
                                        <Volume2 className="w-3 h-3 mt-0.5" />
                                        <span>{message.aiAnnotation}</span>
                                    </div>
                                )}

                                {/* Badges */}
                                {message.badges && message.badges.length > 0 && (
                                    <div className="mt-2 flex gap-2">
                                        {message.badges.map((badge, idx) => (
                                            <span key={idx} className={`px-2 py-1 text-xs font-medium rounded ${badge.color === 'indigo' ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300' :
                                                badge.color === 'green' ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' :
                                                    badge.color === 'yellow' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400' :
                                                        'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                                                }`}>
                                                {badge.label}
                                            </span>
                                        ))}
                                    </div>
                                )}

                                {/* Standalone Prescription Upload Card - only show if NOT verified yet */}
                                {message.prescriptionUpload && !message.orderPreview && !prescriptionVerified && (
                                    <div className="mt-3">
                                        <PrescriptionUploadCard
                                            medicineName={message.prescriptionUpload.medicine_name || 'This medicine'}
                                            onUpload={async (file, base64) => {
                                                // Send prescription to backend for AI validation
                                                try {
                                                    const res = await fetch('/api/prescription/upload', {
                                                        method: 'POST',
                                                        headers: {
                                                            'Content-Type': 'application/json',
                                                            ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {})
                                                        },
                                                        body: JSON.stringify({
                                                            session_id: `session-${selectedPatient?.patient_id}`,
                                                            medicine_id: message.prescriptionUpload.medicine_id || '',
                                                            medicine_name: message.prescriptionUpload.medicine_name || '',
                                                            prescription_file: base64,  // Send base64 image
                                                        }),
                                                    });
                                                    const data = await res.json();
                                                    
                                                    if (!data.success) {
                                                        // Validation failed - return error to card
                                                        return {
                                                            success: false,
                                                            message: data.message || 'Invalid prescription'
                                                        };
                                                    }
                                                    
                                                    if (data.order_preview) {
                                                        // Validation passed - show order preview
                                                        setPrescriptionVerified(true);
                                                        const previewMsg: Message = {
                                                            id: Date.now().toString(),
                                                            role: 'assistant',
                                                            content: data.message || 'Prescription verified! Your order is ready for confirmation.',
                                                            timestamp: new Date(),
                                                            orderPreview: data.order_preview,
                                                        };
                                                        setMessages(prev => [...prev, previewMsg]);

                                                        // Persist to Firestore
                                                        if (conversationId) {
                                                            const metadata = {
                                                                orderPreview: data.order_preview,
                                                                extractedEntities: null,
                                                                safetyResult: null,
                                                                order: null,
                                                                traceUrl: null,
                                                                aiAnnotation: null,
                                                                badges: null,
                                                                prescriptionUpload: null,
                                                            };
                                                            saveMessage(conversationId, {
                                                                sender: 'assistant',
                                                                text: previewMsg.content,
                                                                type: 'order_summary',
                                                                metadata: metadata
                                                            }).catch(err => console.error('[Firestore] Failed to save preview message:', err));
                                                        }
                                                    }
                                                    
                                                    return { success: true };
                                                } catch (error) {
                                                    console.error('Prescription upload failed:', error);
                                                    return {
                                                        success: false,
                                                        message: 'Failed to validate prescription. Please try again.'
                                                    };
                                                }
                                            }}
                                            onSkip={() => sendMessage('cancel')}
                                        />
                                    </div>
                                )}

                                {/* Order Preview Card - always show Confirm/Cancel buttons */}
                                {message.orderPreview && (() => {
                                    const subtotal = message.orderPreview.total_amount || 0;
                                    // Use the total directly from backend (already includes tax/fees)
                                    const total = subtotal;
                                    const totalQuantity = message.orderPreview.items?.reduce((sum: number, item: any) => sum + (item.quantity || 0), 0) || 1;
                                    const pricePerUnit = totalQuantity > 0 ? subtotal / totalQuantity : 0;

                                    return (
                                        <div className="mt-3 space-y-3 max-w-sm">
                                            {/* Order Card with Left Accent Border - Always show with Confirm/Cancel */}
                                            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border-l-4 border-l-indigo-600 border border-gray-200 dark:border-gray-700 p-4 transition-colors duration-300">
                                                <div className="mb-3">
                                                    <h4 className="font-semibold text-gray-900 dark:text-white">
                                                        Confirm Your Order
                                                    </h4>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400">Review details before confirming home delivery</p>
                                                </div>

                                                <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-medium">Medicine Details</p>

                                                {message.orderPreview.items?.map((item: any, idx: number) => {
                                                    const itemTotal = item.unit_price ? item.unit_price * item.quantity : 0;
                                                    const supplyDays = item.supply_days || Math.round((item.quantity || 2) * 0.5) || 45;

                                                    return (
                                                        <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-2">
                                                            <div className="w-12 h-12 rounded-lg overflow-hidden bg-white flex-shrink-0 shadow-sm border border-gray-200 dark:border-gray-600">
                                                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                                                <img
                                                                    src={(() => {
                                                                        const form = (item.form || 'tablet').toLowerCase();
                                                                        if (form.includes('capsule')) return '/medicines/capsule.png';
                                                                        if (form.includes('inhaler')) return '/medicines/inhaler.png';
                                                                        if (form.includes('pen') || form.includes('insulin')) return '/medicines/pen.png';
                                                                        if (form.includes('softgel') || form.includes('gel')) return '/medicines/softgel.png';
                                                                        return '/medicines/tablet.png';
                                                                    })()}
                                                                    alt={item.medicine_name}
                                                                    className="w-full h-full object-cover"
                                                                />
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <div className="flex items-center justify-between gap-2">
                                                                    <p className="font-medium text-gray-900 dark:text-gray-100 text-sm">{item.medicine_name}</p>
                                                                    {item.unit_price && (
                                                                        <p className="text-sm font-semibold text-gray-700 dark:text-gray-200 whitespace-nowrap">
                                                                            ₹{itemTotal.toFixed(2)}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                                    {item.strength} • {item.quantity} units
                                                                </p>
                                                                <p className="text-xs text-cyan-600 dark:text-cyan-400 mt-1">
                                                                    Supply: ~{supplyDays} days
                                                                </p>
                                                            </div>
                                                        </div>
                                                    );
                                                })}

                                                {/* Price Breakdown */}
                                                <div className="border-t border-gray-100 dark:border-gray-600 pt-3 mt-3">
                                                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                                                        <span>Price per unit</span>
                                                        <span>₹{pricePerUnit.toFixed(2)}/unit</span>
                                                    </div>
                                                    <div className="flex justify-between items-baseline">
                                                        <div>
                                                            <p className="font-semibold text-gray-900 dark:text-white text-sm">Total Amount</p>
                                                            <p className="text-[10px] text-gray-400 dark:text-gray-500">Inclusive of all taxes</p>
                                                        </div>
                                                        <span className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
                                                            ₹{total.toFixed(2)}
                                                        </span>
                                                    </div>
                                                </div>

                                                {/* Home Delivery Section */}
                                                <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/40 rounded-lg flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0">
                                                        <Truck className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                                    </div>
                                                    <div>
                                                        <p className="font-medium text-gray-900 dark:text-white text-sm">Home Delivery</p>
                                                        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                                            <Clock className="w-3 h-3" />
                                                            Est. Tomorrow by 9:00 PM
                                                        </p>
                                                    </div>
                                                </div>

                                                {/* ALWAYS show Confirm/Cancel buttons */}
                                                <div className="flex gap-2 mt-4">
                                                    <button
                                                        onClick={() => sendMessage('cancel')}
                                                        className="flex-1 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 text-sm font-medium rounded-lg transition-colors"
                                                    >
                                                        Cancel
                                                    </button>
                                                    <button
                                                        onClick={() => sendMessage('confirm')}
                                                        className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
                                                    >
                                                        Confirm Order
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })()}

                                {message.order && (
                                    <div className="mt-3 space-y-3">
                                        <div className="flex gap-2">
                                            <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-medium rounded">
                                                Refill placed by AI
                                            </span>
                                            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">
                                                Inventory updated
                                            </span>
                                        </div>
                                        
                                        {/* Explain My Medicine Card - Post-order explainability */}
                                        <ExplainMedicineCard
                                            medicines={message.order.items?.map((item: any) => ({
                                                medicine_name: item.medicine_name || item.name,
                                                strength: item.strength || item.dosage || '',
                                                quantity: item.quantity || 1
                                            })) || [{
                                                medicine_name: 'Your Medicine',
                                                strength: '',
                                                quantity: 1
                                            }]}
                                            onLoadExplanation={async (medicineName: string) => {
                                                const item = message.order.items?.find(
                                                    (i: any) => (i.medicine_name || i.name) === medicineName
                                                );
                                                const res = await fetch('/api/medicine/explain', {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({
                                                        medicine_name: medicineName,
                                                        strength: item?.strength || item?.dosage || '',
                                                        quantity: item?.quantity || 1,
                                                        frequency: null
                                                    })
                                                });
                                                return await res.json();
                                            }}
                                        />
                                    </div>
                                )}

                                {/* Timestamp */}
                                <p className={`text-xs text-gray-400 mt-1 ${message.role === 'user' ? 'text-right' : ''}`}>
                                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </p>
                            </div>
                            
                            {/* Customer Avatar - right side for user */}
                            {message.role === 'user' && (
                                <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden border-2 border-purple-400 shadow-sm self-end">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                        src={(() => {
                                            const name = (userName || 'Guest').split(' ')[0].toLowerCase();
                                            if (['sh', 'h', 'n', 'k', 'r', 't', 'm', 'd', 's', 'o', 'v', 'l'].some(end => name.endsWith(end))) return '/customer-male.png';
                                            if (['a', 'i', 'y', 'e'].some(end => name.endsWith(end))) return '/customer-female.png';
                                            return '/customer-male.png';
                                        })()}
                                        alt="Customer"
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div className="flex items-start gap-3">
                            {/* AI Pharmacist Avatar */}
                            <div className="relative flex-shrink-0">
                                <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-indigo-400 shadow-lg">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                        src="/ai-pharmacist.jpg"
                                        alt="AI Pharmacist thinking"
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                                {/* Pulsing ring animation */}
                                <div className="absolute inset-0 rounded-full border-2 border-indigo-400 animate-ping opacity-30"></div>
                            </div>
                            {/* Thinking bubble */}
                            <div className="bg-white dark:bg-gray-800 px-4 py-3 rounded-2xl rounded-tl-md shadow-sm border border-gray-200 dark:border-gray-700">
                                <div className="flex items-center gap-2">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                    <span className="text-sm text-gray-500 dark:text-gray-400">AI is thinking...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                {/* Input Area or Voice UI */}
                <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 p-4 transition-colors duration-300 relative">
                    {/* Premium Voice Wave Visualization */}
                    <VoiceWave isListening={isRecording} subtitle="Speak naturally, AI is listening..." />

                    <form onSubmit={(e) => { e.preventDefault(); pendingPillImage ? sendMessageWithImage() : sendMessage(inputValue); }} className="flex flex-col gap-2">
                        {/* Pending Image Preview */}
                        {pendingPillImage && (
                            <div className="flex items-center gap-2 p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded-lg border border-indigo-200 dark:border-indigo-700">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img 
                                    src={pendingPillImage.base64} 
                                    alt="Pill to identify" 
                                    className="w-12 h-12 object-cover rounded-lg border border-indigo-300"
                                />
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-indigo-700 dark:text-indigo-300">📷 Pill image attached</p>
                                    <p className="text-xs text-indigo-500 dark:text-indigo-400">Type your question and press send</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={cancelPillImage}
                                    className="p-1 text-indigo-500 hover:text-indigo-700 dark:hover:text-indigo-300"
                                    title="Remove image"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        )}

                        <div className="flex items-center gap-3">
                        {/* Left Actions */}
                        {isRecording ? (
                            <button
                                type="button"
                                onClick={cancelRecording}
                                className="p-2 w-10 h-10 flex items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30 text-red-500 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                                title="Cancel Recording"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        ) : (
                            <>
                                <button
                                    type="button"
                                    onClick={() => pillImageInputRef.current?.click()}
                                    className={`p-2 transition-colors ${pendingPillImage ? 'text-indigo-500' : 'text-gray-400 hover:text-gray-600'}`}
                                    title="Identify pill from image"
                                >
                                    <Paperclip className="w-5 h-5" />
                                </button>
                                <input
                                    type="file"
                                    ref={pillImageInputRef}
                                    hidden
                                    accept="image/*"
                                    onChange={handlePillImageUpload}
                                />
                            </>
                        )}

                        {/* Input Field */}
                        <div className="flex-1 relative">
                            <input
                                type="text"
                                value={isRecording ? "" : inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder={isRecording ? "Listening..." : (pendingPillImage ? "Ask about this pill..." : "Type your message...")}
                                className={`w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 transition-all ${isRecording ? 'bg-gray-100 dark:bg-gray-800 text-transparent' : 'bg-gray-50 dark:bg-gray-800'}`}
                                disabled={isLoading || isRecording}
                            />
                        </div>

                        {/* Right Actions */}
                        {isRecording ? (
                            <div className="relative group cursor-pointer" onClick={stopRecording}>
                                <div className="absolute inset-0 bg-blue-500 rounded-full opacity-20 animate-ping group-hover:opacity-30"></div>
                                <div className="absolute inset-[-4px] bg-blue-500 rounded-full opacity-10 animate-pulse"></div>
                                <div className="relative z-10 w-14 h-14 bg-gradient-to-b from-blue-500 to-blue-600 rounded-full shadow-xl flex items-center justify-center transition-transform group-active:scale-95 text-white">
                                    <Mic className="w-7 h-7" />
                                </div>
                            </div>
                        ) : (
                            <>
                                {/* Real-time Voice Button (GPT-4o-realtime) */}
                                <RealtimeVoiceButton
                                    conversationId={conversationId || undefined}
                                    onOrderPreview={(preview) => {
                                        // Inject order preview into messages
                                        const syntheticMessage: Message = {
                                            id: Date.now().toString(),
                                            role: 'assistant',
                                            content: '🎤 Voice command received. Here\'s your order preview:',
                                            timestamp: new Date(),
                                            orderPreview: preview,
                                        };
                                        setMessages(prev => [...prev, syntheticMessage]);
                                    }}
                                    onCartUpdate={(cartData) => {
                                        // Trigger cart refresh
                                        console.log('Cart updated via voice:', cartData);
                                    }}
                                    onOrderConfirmed={(orderData) => {
                                        // Trigger celebration and add confirmation message
                                        setOrderCelebrationStatus('CONFIRMED');
                                        const syntheticMessage: Message = {
                                            id: Date.now().toString(),
                                            role: 'assistant',
                                            content: `🎉 Order confirmed via voice! Order ID: ${(orderData as any).order_id}`,
                                            timestamp: new Date(),
                                            order: orderData,
                                        };
                                        setMessages(prev => [...prev, syntheticMessage]);
                                    }}
                                />

                                <button
                                    type="submit"
                                    disabled={(!inputValue.trim() && !pendingPillImage) || isLoading}
                                    className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    {isLoading ? (
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <Send className="w-5 h-5" />
                                    )}
                                </button>
                            </>
                        )}
                        </div>
                    </form>
                </div>
            </div>

            {/* Right Panel - AI Decision Summary & Settings */}
            <aside className="w-80 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 p-0 flex flex-col transition-colors duration-300">


                {/* Chat Settings */}
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                    <div className="flex items-center gap-2 mb-3">
                        <Settings className="w-4 h-4 text-gray-500" />
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Chat Settings</h3>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Personalize your chat experience.</p>

                    <div className="space-y-4">
                        {/* Auto-save chats toggle */}
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-700 dark:text-gray-300">Auto-save chats</span>
                            <button
                                onClick={() => {
                                    const newState = !autoSaveChats;
                                    setAutoSaveChats(newState);
                                    if (!newState && selectedPatient) {
                                        // Clear all chats if auto-save is disabled
                                        setMessages([]);
                                        localStorage.removeItem(`chat_messages_${selectedPatient.patient_id}`);
                                    }
                                }}
                                className={`w-10 h-6 rounded-full transition-colors ${autoSaveChats ? 'bg-indigo-600' : 'bg-gray-300'
                                    }`}
                            >
                                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform mx-1 ${autoSaveChats ? 'translate-x-4' : 'translate-x-0'
                                    }`} />
                            </button>
                        </div>

                        {/* Desktop Notifications toggle */}
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-700 dark:text-gray-300">Desktop Notifications</span>
                            <button
                                onClick={() => setDesktopNotifications(!desktopNotifications)}
                                className={`w-10 h-6 rounded-full transition-colors ${desktopNotifications ? 'bg-indigo-600' : 'bg-gray-300'
                                    }`}
                            >
                                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform mx-1 ${desktopNotifications ? 'translate-x-4' : 'translate-x-0'
                                    }`} />
                            </button>
                        </div>

                        {/* Archive Conversation Section - ChatGPT style */}
                        <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mt-2">
                            <button
                                onClick={() => setIsArchiveExpanded(!isArchiveExpanded)}
                                className="w-full flex items-center justify-between text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
                            >
                                <span className="flex items-center gap-2">
                                    <ChevronRight className={`w-4 h-4 transition-transform ${isArchiveExpanded ? 'rotate-90' : ''}`} />
                                    Archive Conversation
                                </span>
                                {archivedConversations.length > 0 && (
                                    <span className="text-xs bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 px-1.5 py-0.5 rounded-full">
                                        {archivedConversations.length}
                                    </span>
                                )}
                            </button>

                            {isArchiveExpanded && (
                                <div className="mt-3 space-y-2">
                                    {/* New Chat Button */}
                                    <button
                                        onClick={async () => {
                                            if (!user?.uid || !selectedPatient?.patient_id) return;
                                            const newId = await createNewConversation(user.uid, selectedPatient.patient_id);
                                            setConversationId(newId);
                                            setMessages([]);
                                            setCurrentEntities(null);
                                            setPrescriptionVerified(false);
                                            prescriptionCalledRef.current.clear();
                                        }}
                                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
                                    >
                                        <span>+ New Chat</span>
                                    </button>

                                    {/* Archived Conversations List */}
                                    {isLoadingArchive ? (
                                        <div className="flex items-center justify-center py-4">
                                            <div className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                                        </div>
                                    ) : archivedConversations.length === 0 ? (
                                        <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-3">
                                            No archived conversations yet
                                        </p>
                                    ) : (
                                        <div className="max-h-48 overflow-y-auto space-y-1">
                                            {archivedConversations.map((conv) => (
                                                <div
                                                    key={conv.id}
                                                    className={`group relative flex items-center gap-1 p-2 rounded-lg text-xs transition-colors ${
                                                        conv.id === conversationId
                                                            ? 'bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700'
                                                            : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                                                    }`}
                                                >
                                                    <button
                                                        onClick={async () => {
                                                            setConversationId(conv.id);
                                                            setIsLoading(true);
                                                            try {
                                                                const firestoreMessages = await loadMessages(conv.id);
                                                                const formattedMessages = firestoreMessages.map((msg, index) => ({
                                                                    id: `hist-${index}`,
                                                                    role: msg.sender === 'user' ? 'user' as const : 'assistant' as const,
                                                                    content: msg.text,
                                                                    timestamp: msg.timestamp?.toDate() || new Date(),
                                                                    ...(msg.metadata || {})
                                                                }));
                                                                setMessages(formattedMessages);
                                                                const persistedEntities = await getConversationEntities(conv.id);
                                                                setCurrentEntities(persistedEntities || null);
                                                            } catch (err) {
                                                                console.error('[Archive] Failed to load:', err);
                                                            } finally {
                                                                setIsLoading(false);
                                                            }
                                                        }}
                                                        className="flex-1 text-left min-w-0"
                                                    >
                                                        <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                                            {conv.title}
                                                        </p>
                                                        {conv.lastMessagePreview && (
                                                            <p className="text-gray-500 dark:text-gray-400 truncate mt-0.5">
                                                                {conv.lastMessagePreview}
                                                            </p>
                                                        )}
                                                    </button>
                                                    <button
                                                        onClick={async (e) => {
                                                            e.stopPropagation();
                                                            if (confirm('Delete this conversation? This action cannot be undone.')) {
                                                                try {
                                                                    // Track deleted ID to prevent reappearing
                                                                    console.log('[Delete] Adding to deleted set:', conv.id);
                                                                    deletedConversationIdsRef.current.add(conv.id);
                                                                    console.log('[Delete] Deleted set now contains:', Array.from(deletedConversationIdsRef.current));
                                                                    
                                                                    // Remove from UI immediately
                                                                    setArchivedConversations(prev => prev.filter(c => c.id !== conv.id));
                                                                    
                                                                    // Delete from Firestore
                                                                    await deleteConversation(conv.id);
                                                                    console.log('[Delete] Firestore delete completed for:', conv.id);
                                                                    
                                                                    // If deleted current conversation, reset to a new one
                                                                    if (conv.id === conversationId && user?.uid && selectedPatient?.patient_id) {
                                                                        const newId = await createNewConversation(user.uid, selectedPatient.patient_id);
                                                                        setConversationId(newId);
                                                                        setMessages([]);
                                                                        setCurrentEntities(null);
                                                                        setPrescriptionVerified(false);
                                                                        prescriptionCalledRef.current.clear();
                                                                    }
                                                                } catch (err) {
                                                                    console.error('[Archive] Failed to delete:', err);
                                                                }
                                                            }
                                                        }}
                                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all text-gray-400 hover:text-red-500 dark:hover:text-red-400"
                                                        title="Delete conversation"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </aside>

            <CartDrawer 
                isOpen={isCartOpen} 
                onClose={() => setIsCartOpen(false)} 
                items={cartItems}
                onCheckout={() => {
                    setIsCartOpen(false);
                    setIsCheckoutOpen(true);
                }} 
            />

            <CheckoutModal
                isOpen={isCheckoutOpen}
                onClose={() => setIsCheckoutOpen(false)}
                items={cartItems}
                total={cartItems.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0)}
                onConfirm={async (method) => {
                    // Send confirmation message to chat to trigger fulfillment
                    const itemList = cartItems.map(i => `${i.quantity}x ${i.medicine_name}`).join(', ');
                    const msg = `I confirm my order for: ${itemList}. Payment Method: ${method === 'upi' ? 'UPI' : 'COD'}.`;
                    
                    await sendMessage(msg);
                    setIsCheckoutOpen(false);
                    // Cart clearing handled by backend or manual clear here if needed, 
                    // but let's let backend logic handle it for robustness in Phase 3.
                }}
            />
        </div>
    );
}
