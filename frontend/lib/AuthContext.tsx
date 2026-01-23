/**
 * Authentication Context with Role Support
 * ==========================================
 * Provides authentication state and role-based access throughout the app.
 * 
 * Roles:
 * - "customer" (default for new signups)
 * - "admin" (manually assigned in Firestore)
 * 
 * Usage:
 * - Wrap your app with <AuthProvider>
 * - Use useAuth() hook to access auth state and role
 */

'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
    User,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut as firebaseSignOut,
    onAuthStateChanged
} from 'firebase/auth';
import { doc, getDoc, setDoc, serverTimestamp } from 'firebase/firestore';
import { auth, db } from './firebase';
import { ensureUserDocument } from './firestoreService';

// User role type
export type UserRole = 'customer' | 'admin' | null;

// Auth context type
interface AuthContextType {
    user: User | null;
    loading: boolean;
    idToken: string | null;
    userRole: UserRole;
    userName: string | null;
    signIn: (email: string, password: string) => Promise<void>;
    signUp: (email: string, password: string, name: string, phone: string) => Promise<void>;
    signOut: () => Promise<void>;
}

// Create context with default values
const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    idToken: null,
    userRole: null,
    userName: null,
    signIn: async () => { },
    signUp: async () => { },
    signOut: async () => { },
});

// Auth Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [idToken, setIdToken] = useState<string | null>(null);
    const [userRole, setUserRole] = useState<UserRole>(null);
    const [userName, setUserName] = useState<string | null>(null);

    // Fetch user role from Firestore
    const fetchUserRole = async (uid: string): Promise<UserRole> => {
        try {
            console.log('[AuthContext] Fetching role for UID:', uid);
            const userDoc = await getDoc(doc(db, 'users', uid));
            if (userDoc.exists()) {
                const data = userDoc.data();
                console.log('[AuthContext] Firestore user data:', data);
                // Normalize role to lowercase to handle "Admin" vs "admin"
                const rawRole = data.role;
                const normalizedRole = typeof rawRole === 'string' ? rawRole.toLowerCase() : 'customer';
                console.log('[AuthContext] Raw role:', rawRole, '→ Normalized:', normalizedRole);
                return (normalizedRole === 'admin' ? 'admin' : 'customer') as UserRole;
            }
            console.log('[AuthContext] No user document found, defaulting to customer');
            return 'customer'; // Default role if no document
        } catch (error) {
            console.error('[AuthContext] Error fetching user role:', error);
            return 'customer';
        }
    };

    // Fetch user name from Firestore
    const fetchUserName = async (uid: string): Promise<string | null> => {
        try {
            const userDoc = await getDoc(doc(db, 'users', uid));
            if (userDoc.exists()) {
                const data = userDoc.data();
                // Return name if exists, otherwise fallback to email prefix
                if (data.name) return data.name;
                if (data.email) return data.email.split('@')[0];
            }
            return null;
        } catch (error) {
            console.error('[AuthContext] Error fetching user name:', error);
            return null;
        }
    };

    // Create user profile in Firestore
    const createUserProfile = async (uid: string, email: string, name: string) => {
        try {
            await setDoc(doc(db, 'users', uid), {
                name,
                email,
                role: 'customer', // Default role for all new users
                createdAt: serverTimestamp(),
            });
        } catch (error) {
            console.error('Error creating user profile:', error);
        }
    };

    // Listen to auth state changes
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
            setUser(firebaseUser);

            if (firebaseUser) {
                // Get and store the ID token
                const token = await firebaseUser.getIdToken();
                setIdToken(token);
                localStorage.setItem('authToken', token);

                // Fetch user role from Firestore
                const role = await fetchUserRole(firebaseUser.uid);
                setUserRole(role);
                localStorage.setItem('userRole', role || 'customer');

                // Fetch user name from Firestore
                const name = await fetchUserName(firebaseUser.uid);
                setUserName(name);
                if (name) localStorage.setItem('userName', name);
            } else {
                setIdToken(null);
                setUserRole(null);
                setUserName(null);
                localStorage.removeItem('authToken');
                localStorage.removeItem('userRole');
                localStorage.removeItem('userName');
            }

            setLoading(false);
        });

        // Cleanup subscription
        return () => unsubscribe();
    }, []);

    // Refresh token periodically (tokens expire after 1 hour)
    useEffect(() => {
        if (!user) return;

        const refreshToken = async () => {
            try {
                const token = await user.getIdToken(true); // Force refresh
                setIdToken(token);
                localStorage.setItem('authToken', token);
            } catch (error) {
                console.error('Token refresh failed:', error);
            }
        };

        // Refresh every 50 minutes (before 1 hour expiry)
        const interval = setInterval(refreshToken, 50 * 60 * 1000);
        return () => clearInterval(interval);
    }, [user]);

    // Sign in with email and password
    const signIn = async (email: string, password: string) => {
        const result = await signInWithEmailAndPassword(auth, email, password);
        const token = await result.user.getIdToken();
        setIdToken(token);
        localStorage.setItem('authToken', token);

        // Ensure user document exists in Firestore (auto-create for existing users)
        await ensureUserDocument(result.user.uid, email);

        // Fetch role after sign in
        const role = await fetchUserRole(result.user.uid);
        setUserRole(role);
        localStorage.setItem('userRole', role || 'customer');
    };

    // Sign up with email and password (modified to include phone)
    const signUp = async (email: string, password: string, name: string, phone: string) => {
        const result = await createUserWithEmailAndPassword(auth, email, password);
        const token = await result.user.getIdToken();
        setIdToken(token);
        localStorage.setItem('authToken', token);

        // Create user profile with name, phone, and default "customer" role
        // Use common service to ensure consistency
        await ensureUserDocument(result.user.uid, email, name, phone);

        setUserRole('customer');
        setUserName(name);
        localStorage.setItem('userRole', 'customer');
        localStorage.setItem('userName', name);
    };

    // Sign out
    const signOut = async () => {
        await firebaseSignOut(auth);
        setIdToken(null);
        setUserRole(null);
        setUserName(null);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userRole');
        localStorage.removeItem('userName');
    };

    return (
        <AuthContext.Provider value={{ user, loading, idToken, userRole, userName, signIn, signUp, signOut }}>
            {children}
        </AuthContext.Provider>
    );
}

// Hook to use auth context
export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

// Helper to get token for API requests
export function getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('authToken');
    }
    return null;
}

// Helper to get user role
export function getUserRole(): UserRole {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('userRole') as UserRole;
    }
    return null;
}
