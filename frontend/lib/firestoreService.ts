/**
 * Firestore Service for Data Persistence
 * ========================================
 * Handles CRUD operations for users and conversations.
 * Only stores user-visible data - NO agent reasoning or traces.
 */

import {
    doc,
    getDoc,
    setDoc,
    addDoc,
    collection,
    query,
    where,
    orderBy,
    getDocs,
    serverTimestamp,
    Timestamp
} from 'firebase/firestore';
import { db } from './firebase';

// ============ TYPES ============

export interface UserDocument {
    name?: string;  // Optional for backward compatibility with existing users
    email: string;
    role: 'customer' | 'admin';
    createdAt: Timestamp;
}

export interface ConversationDocument {
    userId: string;
    patientId: string;
    createdAt: Timestamp;
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
 */
export async function ensureUserDocument(uid: string, email: string): Promise<void> {
    const userRef = doc(db, 'users', uid);
    const userSnap = await getDoc(userRef);

    if (!userSnap.exists()) {
        await setDoc(userRef, {
            email,
            role: 'customer', // Default role for new users
            createdAt: serverTimestamp(),
        });
        console.log('[Firestore] Created user document for:', uid);
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
 * Only saves user-visible data - NO agent reasoning.
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

    // Update conversation timestamp
    const conversationRef = doc(db, 'conversations', conversationId);
    await setDoc(conversationRef, { updatedAt: serverTimestamp() }, { merge: true });

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
