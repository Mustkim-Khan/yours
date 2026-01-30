/**
 * Cabinet Service - API client for medicine cabinet
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface CabinetMedicine {
    id: string;
    name: string;
    strength: string;
    form: string;
    expiryDate?: string;
    expiryStatus: 'safe' | 'expiring' | 'expired';
    quantity: number;
    estimatedRemaining: number;
    aiConfidence: number;
    manufacturer?: string;
    addedDate: string;
    imageUrl?: string;
}

export interface ScanResult {
    success: boolean;
    is_medicine?: boolean;  // Whether the image is actually a medicine
    medicine?: {
        name: string;
        strength: string;
        form: string;
        expiry_date?: string;
        expiry_status: string;
        manufacturer?: string;
        ai_confidence: number;
        image_base64?: string;  // The uploaded image
    };
    error?: string;
}

/**
 * Get auth token from Firebase
 */
async function getAuthToken(): Promise<string | null> {
    // Import firebase auth dynamically to avoid SSR issues
    if (typeof window === 'undefined') return null;
    
    try {
        const { auth } = await import('./firebase');
        const user = auth.currentUser;
        if (user) {
            return await user.getIdToken();
        }
    } catch (e) {
        console.error('Failed to get auth token:', e);
    }
    return null;
}

/**
 * Scan a medicine image using AI
 */
export async function scanMedicine(imageFile: File): Promise<ScanResult> {
    const token = await getAuthToken();
    if (!token) {
        return { success: false, error: 'Not authenticated' };
    }

    const formData = new FormData();
    formData.append('file', imageFile);

    try {
        const response = await fetch(`${API_URL}/api/cabinet/scan`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            return { success: false, error: error.detail || 'Scan failed' };
        }

        return await response.json();
    } catch (e) {
        console.error('Scan error:', e);
        return { success: false, error: 'Network error' };
    }
}

/**
 * Get all medicines in user's cabinet
 */
export async function getCabinetMedicines(userId: string): Promise<CabinetMedicine[]> {
    const token = await getAuthToken();
    if (!token) {
        console.error('Not authenticated');
        return [];
    }

    try {
        const response = await fetch(`${API_URL}/api/cabinet/${userId}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            console.error('Failed to fetch cabinet:', response.status);
            return [];
        }

        const data = await response.json();
        return data.medicines || [];
    } catch (e) {
        console.error('Fetch cabinet error:', e);
        return [];
    }
}

/**
 * Add a medicine to cabinet
 */
export async function addToCabinet(
    userId: string,
    medicine: {
        name: string;
        strength: string;
        form: string;
        expiry_date?: string;
        expiry_status?: string;
        quantity?: number;
        ai_confidence?: number;
        manufacturer?: string;
    }
): Promise<{ success: boolean; medicine?: CabinetMedicine; error?: string }> {
    const token = await getAuthToken();
    if (!token) {
        return { success: false, error: 'Not authenticated' };
    }

    try {
        const response = await fetch(`${API_URL}/api/cabinet/${userId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(medicine),
        });

        if (!response.ok) {
            const error = await response.json();
            return { success: false, error: error.detail || 'Failed to add' };
        }

        const data = await response.json();
        return { success: true, medicine: data.medicine };
    } catch (e) {
        console.error('Add to cabinet error:', e);
        return { success: false, error: 'Network error' };
    }
}

/**
 * Remove medicine from cabinet
 */
export async function removeFromCabinet(
    userId: string,
    medicineId: string
): Promise<{ success: boolean; error?: string }> {
    const token = await getAuthToken();
    if (!token) {
        return { success: false, error: 'Not authenticated' };
    }

    try {
        const response = await fetch(`${API_URL}/api/cabinet/${userId}/${medicineId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            const error = await response.json();
            return { success: false, error: error.detail || 'Failed to remove' };
        }

        return { success: true };
    } catch (e) {
        console.error('Remove from cabinet error:', e);
        return { success: false, error: 'Network error' };
    }
}
