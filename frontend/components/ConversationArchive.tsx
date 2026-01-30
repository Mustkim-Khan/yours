'use client';

import { useAuth } from '@/lib/AuthContext';
import { createNewConversation, deleteConversation, getArchivedConversations } from '@/lib/firestoreService';
import { ChevronDown, ChevronUp, Clock, MessageSquare, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface ArchivedConversation {
    id: string;
    title: string;
    lastMessagePreview: string;
    lastMessageAt: Date;
    messageCount: number;
    patientId: string;
}

interface ConversationArchiveProps {
    currentConversationId: string | null;
    currentPatientId: string | null;
    onSelectConversation: (conversationId: string, patientId: string) => void;
    onNewChat: (conversationId: string) => void;
}

export default function ConversationArchive({
    currentConversationId,
    currentPatientId,
    onSelectConversation,
    onNewChat
}: ConversationArchiveProps) {
    const { user } = useAuth();
    const [conversations, setConversations] = useState<ArchivedConversation[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isExpanded, setIsExpanded] = useState(true);
    const [isCreatingNew, setIsCreatingNew] = useState(false);

    // Load archived conversations
    const loadConversations = useCallback(async () => {
        if (!user?.uid) return;
        
        setIsLoading(true);
        try {
            const archived = await getArchivedConversations(user.uid);
            setConversations(archived);
        } catch (error) {
            console.error('[Archive] Failed to load conversations:', error);
        } finally {
            setIsLoading(false);
        }
    }, [user?.uid]);

    useEffect(() => {
        loadConversations();
    }, [loadConversations]);

    // Refresh when current conversation changes (new messages might update titles)
    useEffect(() => {
        if (currentConversationId) {
            // Debounce refresh
            const timer = setTimeout(() => loadConversations(), 1000);
            return () => clearTimeout(timer);
        }
    }, [currentConversationId, loadConversations]);

    // Handle new chat creation
    const handleNewChat = async () => {
        if (!user?.uid || !currentPatientId || isCreatingNew) return;
        
        setIsCreatingNew(true);
        try {
            const newConvId = await createNewConversation(user.uid, currentPatientId);
            onNewChat(newConvId);
            await loadConversations();
        } catch (error) {
            console.error('[Archive] Failed to create new chat:', error);
        } finally {
            setIsCreatingNew(false);
        }
    };

    // Handle conversation deletion
    const handleDelete = async (e: React.MouseEvent, conversationId: string) => {
        e.stopPropagation();
        if (!confirm('Delete this conversation? This cannot be undone.')) return;
        
        try {
            await deleteConversation(conversationId);
            await loadConversations();
            
            // If deleted current conversation, create new one
            if (conversationId === currentConversationId && currentPatientId) {
                handleNewChat();
            }
        } catch (error) {
            console.error('[Archive] Failed to delete conversation:', error);
        }
    };

    // Format relative time (e.g., "2 hours ago")
    const formatRelativeTime = (date: Date): string => {
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    if (!user) return null;

    return (
        <div className="bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 w-64 flex-shrink-0 flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="p-3 border-b border-gray-200 dark:border-gray-800">
                <button
                    onClick={handleNewChat}
                    disabled={isCreatingNew || !currentPatientId}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-lg transition-colors"
                >
                    {isCreatingNew ? (
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <Plus className="w-4 h-4" />
                    )}
                    New Chat
                </button>
            </div>

            {/* Archive Section */}
            <div className="flex-1 overflow-y-auto">
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                    <span>Archived Conversations</span>
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {isExpanded && (
                    <div className="px-2 pb-2">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <div className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                            </div>
                        ) : conversations.length === 0 ? (
                            <div className="text-center py-8">
                                <MessageSquare className="w-8 h-8 mx-auto text-gray-300 dark:text-gray-600 mb-2" />
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    No archived conversations yet
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-1">
                                {conversations.map((conv) => (
                                    <button
                                        key={conv.id}
                                        onClick={() => onSelectConversation(conv.id, conv.patientId)}
                                        className={`w-full text-left p-2.5 rounded-lg transition-colors group ${
                                            conv.id === currentConversationId
                                                ? 'bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700'
                                                : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                                        }`}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1 min-w-0">
                                                <p className={`font-medium text-sm truncate ${
                                                    conv.id === currentConversationId
                                                        ? 'text-indigo-700 dark:text-indigo-300'
                                                        : 'text-gray-900 dark:text-gray-100'
                                                }`}>
                                                    {conv.title}
                                                </p>
                                                {conv.lastMessagePreview && (
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                                                        {conv.lastMessagePreview}
                                                    </p>
                                                )}
                                                <div className="flex items-center gap-2 mt-1 text-xs text-gray-400 dark:text-gray-500">
                                                    <Clock className="w-3 h-3" />
                                                    <span>{formatRelativeTime(conv.lastMessageAt)}</span>
                                                </div>
                                            </div>
                                            
                                            {/* Delete button (hidden until hover) */}
                                            <button
                                                onClick={(e) => handleDelete(e, conv.id)}
                                                className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all"
                                                title="Delete conversation"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
