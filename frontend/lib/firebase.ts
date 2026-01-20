/**
 * Firebase Client Configuration
 * ==============================
 * Initializes Firebase client for authentication and Firestore.
 * 
 * SETUP:
 * 1. Create .env.local in frontend root
 * 2. Add your Firebase config values:
 *    NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
 *    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
 *    NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
 *    NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
 */

import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

// Firebase configuration from environment variables
const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Initialize Firebase (prevent re-initialization in dev mode)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();

// Export auth instance
export const auth = getAuth(app);

// Export Firestore instance for role storage
export const db = getFirestore(app);

export default app;
