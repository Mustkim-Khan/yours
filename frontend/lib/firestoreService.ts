/**
 * Firestore Service for Data Persistence
 * ========================================
 * Handles CRUD operations for users and conversations.
 * Only stores user-visible data - NO agent reasoning or traces.
 */

import {
    addDoc,
    collection,
    deleteDoc,
    doc,
    getDoc,
    getDocs,
    onSnapshot,
    orderBy,
    query,
    serverTimestamp,
    setDoc,
    Timestamp,
    updateDoc,
    where
} from 'firebase/firestore';
import { db } from './firebase';

// ============ TYPES ============

export interface UserDocument {
    name?: string;  // Optional for backward compatibility with existing users
    email: string;
    role: 'customer' | 'admin';
    phone?: string; // E.164 phone number
    createdAt: Timestamp;
}

export interface ConversationDocument {
    userId: string;
    patientId: string;
    createdAt: Timestamp;
    updatedAt?: Timestamp;
    // NEW: Archive-related fields
    title?: string; // Auto-generated from first user message
    lastMessagePreview?: string; // Preview of last message for archive list
    lastMessageAt?: Timestamp; // For sorting archive list
    isArchived?: boolean; // Whether this is an archived (completed) conversation
    messageCount?: number; // Total messages in conversation
}

export interface MessageDocument {
    sender: 'user' | 'assistant';
    text: string;
    timestamp: Timestamp;
    type: 'chat' | 'order_summary' | 'status';
    metadata?: any; // Rich data for UI reconstruction
}

// ============ USER OPERATIONS ============

/**
 * Ensure user document exists in Firestore.
 * Creates document if it doesn't exist (for login auto-creation).
 * Does NOT overwrite existing documents (preserves admin role).
 * Updates phone number only if provided and not already set.
 */
export async function ensureUserDocument(
    uid: string,
    email: string,
    name?: string,
    phone?: string
): Promise<void> {
    const userRef = doc(db, 'users', uid);
    const userSnap = await getDoc(userRef);

    if (!userSnap.exists()) {
        const userData: any = {
            email,
            role: 'customer', // Default role for new users
            createdAt: serverTimestamp(),
        };
        if (name) userData.name = name;
        if (phone) userData.phone = phone;

        await setDoc(userRef, userData);
        console.log('[Firestore] Created user document for:', uid);
    } else {
        // If document exists, check if we need to add phone number (never overwrite)
        const currentData = userSnap.data();
        if (phone && !currentData.phone) {
            await setDoc(userRef, { phone }, { merge: true });
            console.log('[Firestore] Updated user phone for:', uid);
        }
    }
}

/**
 * Get user document from Firestore.
 */
export async function getUserDocument(uid: string): Promise<UserDocument | null> {
    const userRef = doc(db, 'users', uid);
    const userSnap = await getDoc(userRef);

    if (userSnap.exists()) {
        return userSnap.data() as UserDocument;
    }
    return null;
}

// ============ CONVERSATION OPERATIONS ============

/**
 * Get or create a conversation for a user and patient.
 * Returns the conversation ID.
 */
export async function getOrCreateConversation(userId: string, patientId: string): Promise<string> {
    const conversationsRef = collection(db, 'conversations');

    // Check for existing conversation
    const q = query(
        conversationsRef,
        where('userId', '==', userId),
        where('patientId', '==', patientId)
    );
    const querySnapshot = await getDocs(q);

    if (!querySnapshot.empty) {
        // Return existing conversation ID
        return querySnapshot.docs[0].id;
    }

    // Create new conversation
    const docRef = await addDoc(conversationsRef, {
        userId,
        patientId,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
    });

    console.log('[Firestore] Created conversation:', docRef.id);
    return docRef.id;
}

/**
 * Get the most recent active conversation for a user.
 */
export async function getLatestConversation(userId: string, patientId: string): Promise<string | null> {
    const conversationsRef = collection(db, 'conversations');
    const q = query(
        conversationsRef,
        where('userId', '==', userId),
        where('patientId', '==', patientId),
        orderBy('updatedAt', 'desc')
        // limit(1) - logic handled by accessing docs[0]
    );

    const querySnapshot = await getDocs(q);
    if (!querySnapshot.empty) {
        return querySnapshot.docs[0].id;
    }
    return null;
}

/**
 * Get all conversations for a user.
 */
export async function getConversationsForUser(userId: string): Promise<{ id: string; data: ConversationDocument }[]> {
    const conversationsRef = collection(db, 'conversations');
    const q = query(
        conversationsRef,
        where('userId', '==', userId),
        orderBy('createdAt', 'desc')
    );

    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({
        id: doc.id,
        data: doc.data() as ConversationDocument,
    }));
}

// ============ MESSAGE OPERATIONS ============

/**
 * Save a message to a conversation.
 * Auto-generates title from first user message and updates preview.
 */
export async function saveMessage(
    conversationId: string,
    message: {
        sender: 'user' | 'assistant';
        text: string;
        type?: 'chat' | 'order_summary' | 'status';
        metadata?: any;
    }
): Promise<string> {
    const messagesRef = collection(db, 'conversations', conversationId, 'messages');

    // Create message document
    const docRef = await addDoc(messagesRef, {
        sender: message.sender,
        text: message.text,
        timestamp: serverTimestamp(),
        type: message.type || 'chat',
        metadata: message.metadata || null,
    });

    // Update conversation metadata
    const conversationRef = doc(db, 'conversations', conversationId);
    const conversationSnap = await getDoc(conversationRef);
    const currentData = conversationSnap.exists() ? conversationSnap.data() : {};
    
    // Generate title from first user message (if not already set)
    const updateData: any = {
        updatedAt: serverTimestamp(),
        lastMessageAt: serverTimestamp(),
        // Always update preview with latest message (truncated)
        lastMessagePreview: message.text.length > 80 
            ? message.text.substring(0, 77) + '...' 
            : message.text,
    };
    
    // Set title from first user message if not already set
    if (!currentData.title && message.sender === 'user') {
        // Generate concise title (3-6 words, max 50 chars)
        const words = message.text.split(/\s+/).slice(0, 6).join(' ');
        updateData.title = words.length > 50 ? words.substring(0, 47) + '...' : words;
    }
    
    await setDoc(conversationRef, updateData, { merge: true });

    return docRef.id;
}

/**
 * Load all messages for a conversation.
 * Returns messages ordered by timestamp (oldest first).
 */
export async function loadMessages(conversationId: string): Promise<MessageDocument[]> {
    const messagesRef = collection(db, 'conversations', conversationId, 'messages');
    const q = query(messagesRef, orderBy('timestamp', 'asc'));

    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => doc.data() as MessageDocument);
}

// ============ ENTITY STATE OPERATIONS ============

/**
 * Update the extracted entity state for a conversation.
 * Persists entities to a sub-document for strict state management.
 */
export async function updateConversationEntities(
    conversationId: string,
    entities: any
): Promise<void> {
    const stateRef = doc(db, 'conversations', conversationId, 'state', 'entities');
    await setDoc(stateRef, {
        extractedEntities: entities,
        updatedAt: serverTimestamp()
    }, { merge: true });
}

/**
 * Get the latest extracted entity state for a conversation.
 */
export async function getConversationEntities(conversationId: string): Promise<any> {
    const stateRef = doc(db, 'conversations', conversationId, 'state', 'entities');
    const docSnap = await getDoc(stateRef);

    if (docSnap.exists()) {
        return docSnap.data().extractedEntities;
    }
    return null;
}
// ============ CART OPERATIONS ============

/**
 * Subscribe to user's active cart.
 * Returns unsubscribe function.
 */
export function subscribeToCart(userId: string, callback: (cart: any) => void) {
    const cartRef = doc(db, 'users', userId, 'cart', 'active');
    return onSnapshot(cartRef, (snapshot) => {
        if (snapshot.exists()) {
            callback(snapshot.data());
        } else {
            callback({ items: [] });
        }
    });
}

/**
 * Remove item from cart.
 */
export async function removeFromCart(userId: string, contextMedicineName: string) {
    const cartRef = doc(db, 'users', userId, 'cart', 'active');
    const snapshot = await getDoc(cartRef);
    if (!snapshot.exists()) return;

    const data = snapshot.data();
    const items = data.items || [];
    // Filter out item by name (using name as ID fallback)
    const newItems = items.filter((i: any) => i.medicine_name !== contextMedicineName);
    
    await updateDoc(cartRef, {
        items: newItems,
        updatedAt: serverTimestamp()
    });
}

/**
 * Clear cart.
 */
export async function clearCart(userId: string) {
    const cartRef = doc(db, 'users', userId, 'cart', 'active');
    await deleteDoc(cartRef); // Or set to empty items
}

// ============ CONVERSATION ARCHIVE OPERATIONS ============

/**
 * Get all archived conversations for a user, sorted by last message time.
 * Returns conversations with title and preview for ChatGPT-style list.
 */
export async function getArchivedConversations(userId: string): Promise<{
    id: string;
    title: string;
    lastMessagePreview: string;
    lastMessageAt: Date;
    messageCount: number;
    patientId: string;
}[]> {
    const conversationsRef = collection(db, 'conversations');
    const q = query(
        conversationsRef,
        where('userId', '==', userId),
        orderBy('updatedAt', 'desc')
    );

    const querySnapshot = await getDocs(q);
    
    return querySnapshot.docs.map(docSnapshot => {
        const data = docSnapshot.data();
        return {
            id: docSnapshot.id,
            title: data.title || 'New Conversation',
            lastMessagePreview: data.lastMessagePreview || '',
            lastMessageAt: data.lastMessageAt?.toDate() || data.updatedAt?.toDate() || data.createdAt?.toDate() || new Date(),
            messageCount: data.messageCount || 0,
            patientId: data.patientId,
        };
    });
}

/**
 * Create a new conversation (for "New Chat" button).
 * Does NOT check for existing - always creates fresh.
 */
export async function createNewConversation(userId: string, patientId: string): Promise<string> {
    const conversationsRef = collection(db, 'conversations');
    
    const docRef = await addDoc(conversationsRef, {
        userId,
        patientId,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
        title: null, // Will be set on first user message
        lastMessagePreview: null,
        lastMessageAt: serverTimestamp(),
        isArchived: false,
        messageCount: 0,
    });

    console.log('[Firestore] Created NEW conversation:', docRef.id);
    return docRef.id;
}

/**
 * Update conversation title (auto-generated from first user message).
 * Only updates if title is not already set.
 */
export async function updateConversationTitle(
    conversationId: string,
    firstUserMessage: string
): Promise<void> {
    const conversationRef = doc(db, 'conversations', conversationId);
    const conversationSnap = await getDoc(conversationRef);
    
    if (conversationSnap.exists() && !conversationSnap.data().title) {
        // Generate title from first user message (max 50 chars)
        const title = firstUserMessage.length > 50 
            ? firstUserMessage.substring(0, 47) + '...'
            : firstUserMessage;
        
        await updateDoc(conversationRef, { 
            title,
            updatedAt: serverTimestamp() 
        });
        console.log('[Firestore] Set conversation title:', title);
    }
}

/**
 * Enhanced save message that also updates archive metadata.
 * Updates lastMessagePreview, lastMessageAt, and messageCount.
 */
export async function saveMessageWithArchive(
    conversationId: string,
    message: {
        sender: 'user' | 'assistant';
        text: string;
        type?: 'chat' | 'order_summary' | 'status';
        metadata?: any;
    },
    isFirstUserMessage: boolean = false
): Promise<string> {
    const messagesRef = collection(db, 'conversations', conversationId, 'messages');

    // Create message document
    const docRef = await addDoc(messagesRef, {
        sender: message.sender,
        text: message.text,
        timestamp: serverTimestamp(),
        type: message.type || 'chat',
        metadata: message.metadata || null,
    });

    // Update conversation with archive metadata
    const conversationRef = doc(db, 'conversations', conversationId);
    const preview = message.text.length > 100 
        ? message.text.substring(0, 97) + '...' 
        : message.text;
    
    const updateData: any = {
        updatedAt: serverTimestamp(),
        lastMessageAt: serverTimestamp(),
        lastMessagePreview: preview,
    };

    // If first user message, set the title
    if (isFirstUserMessage && message.sender === 'user') {
        updateData.title = message.text.length > 50 
            ? message.text.substring(0, 47) + '...'
            : message.text;
    }

    await setDoc(conversationRef, updateData, { merge: true });

    // Increment message count
    const snap = await getDoc(conversationRef);
    const currentCount = snap.data()?.messageCount || 0;
    await updateDoc(conversationRef, { messageCount: currentCount + 1 });

    return docRef.id;
}

/**
 * Get conversation details by ID.
 */
export async function getConversationById(conversationId: string): Promise<ConversationDocument | null> {
    const conversationRef = doc(db, 'conversations', conversationId);
    const conversationSnap = await getDoc(conversationRef);
    
    if (conversationSnap.exists()) {
        return conversationSnap.data() as ConversationDocument;
    }
    return null;
}

/**
 * Mark a conversation as archived.
 */
export async function archiveConversation(conversationId: string): Promise<void> {
    const conversationRef = doc(db, 'conversations', conversationId);
    await updateDoc(conversationRef, { isArchived: true });
}

/**
 * Delete a conversation and all its messages.
 * Completely removes from Firestore - permanent deletion.
 */
export async function deleteConversation(conversationId: string): Promise<void> {
    console.log('[Firestore] Deleting conversation:', conversationId);
    
    try {
        // Delete all messages first
        const messagesRef = collection(db, 'conversations', conversationId, 'messages');
        const messagesSnapshot = await getDocs(messagesRef);
        
        const messageDeletes = messagesSnapshot.docs.map(messageDoc => deleteDoc(messageDoc.ref));
        await Promise.all(messageDeletes);
        console.log(`[Firestore] Deleted ${messagesSnapshot.docs.length} messages`);
        
        // Delete state/entities sub-document if exists
        const entitiesRef = doc(db, 'conversations', conversationId, 'state', 'entities');
        await deleteDoc(entitiesRef).catch(() => {
            // Ignore if doesn't exist
        });
        console.log('[Firestore] Deleted entities state');
        
        // Delete conversation document
        const conversationRef = doc(db, 'conversations', conversationId);
        await deleteDoc(conversationRef);
        
        console.log('[Firestore] Conversation fully deleted:', conversationId);
    } catch (error) {
        console.error('[Firestore] Delete failed:', error);
        throw error;
    }
}
