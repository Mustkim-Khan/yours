"""
Firebase Authentication Utilities
==================================
Verifies Firebase ID tokens for API request authentication.

SETUP:
1. Download service account key from Firebase Console:
   Project Settings → Service Accounts → Generate New Private Key
2. Save as 'service-account.json' in backend root
3. OR set FIREBASE_SERVICE_ACCOUNT_JSON env var with JSON content
"""

import os
import json
from typing import Optional
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)

# Flag to track initialization
_firebase_initialized = False


def init_firebase() -> bool:
    """
    Initialize Firebase Admin SDK.
    Reads credentials from service-account.json or environment variable.
    """
    global _firebase_initialized
    
    if _firebase_initialized:
        return True
    
    try:
        # Option 1: Read from JSON file
        service_account_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'service-account.json'
        )
        
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print("✓ Firebase Admin SDK initialized (from file)")
            return True
        
        # Option 2: Read from environment variable
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            print("✓ Firebase Admin SDK initialized (from env)")
            return True
        
        print("⚠ Firebase Admin SDK not initialized - no credentials found")
        print("  Place service-account.json in backend root OR")
        print("  Set FIREBASE_SERVICE_ACCOUNT_JSON environment variable")
        return False
        
    except Exception as e:
        print(f"✗ Firebase Admin SDK initialization failed: {e}")
        return False


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return user info.
    
    Returns:
        dict with 'uid', 'email', and other claims
        
    Raises:
        HTTPException 401 if token is invalid
    """
    if not _firebase_initialized:
        if not init_firebase():
            raise HTTPException(
                status_code=503,
                detail="Authentication service unavailable"
            )
    
    try:
        # Verify the token with Firebase
        decoded_token = auth.verify_id_token(id_token)
        return {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False),
            'name': decoded_token.get('name'),
        }
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please sign in again."
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked. Please sign in again."
        )
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> dict:
    """
    FastAPI dependency to get current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['email']}"}
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )
    
    token = credentials.credentials
    return verify_firebase_token(token)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[dict]:
    """
    FastAPI dependency for optional authentication.
    Returns None if no token provided, user dict if valid token.
    """
    if credentials is None:
        return None
    
    try:
        return verify_firebase_token(credentials.credentials)
    except HTTPException:
        return None


# Initialize on module load (optional - will init on first request if not)
# init_firebase()
