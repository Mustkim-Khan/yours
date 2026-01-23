'use client';

import { AlertCircle, CheckCircle, FileText, Upload, X, XCircle } from 'lucide-react';
import { useRef, useState } from 'react';

interface PrescriptionUploadCardProps {
    medicineName: string;
    onUpload: (file: File, base64: string) => Promise<{ success: boolean; message?: string }>;
    onSkip: () => void;
}

export default function PrescriptionUploadCard({ medicineName, onUpload, onSkip }: PrescriptionUploadCardProps) {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [uploaded, setUploaded] = useState(false);
    const [validationError, setValidationError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setValidationError(null); // Clear previous error
        }
    };

    const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (file && (file.type.startsWith('image/') || file.type === 'application/pdf')) {
            setSelectedFile(file);
            setValidationError(null);
        }
    };

    const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
    };

    // Convert file to base64
    const fileToBase64 = (file: File): Promise<string> => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = error => reject(error);
        });
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setUploading(true);
        setValidationError(null);
        
        try {
            // Convert to base64
            const base64 = await fileToBase64(selectedFile);
            
            // Call parent handler with file and base64
            const result = await onUpload(selectedFile, base64);
            
            if (result.success) {
                setUploaded(true);
            } else {
                // Validation failed
                setValidationError(result.message || 'Prescription validation failed');
            }
        } catch (error) {
            setValidationError('Failed to process image. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const handleRemoveFile = () => {
        setSelectedFile(null);
        setUploaded(false);
        setValidationError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="mt-3 bg-white rounded-xl shadow-lg border border-amber-200 p-4 max-w-sm">
            <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                    <AlertCircle className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                    <h4 className="font-semibold text-gray-900">Prescription Required</h4>
                    <p className="text-sm text-gray-500">
                        <span className="font-medium text-amber-700">{medicineName}</span> requires a valid prescription
                    </p>
                </div>
            </div>

            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/*,.pdf"
                className="hidden"
            />

            {!selectedFile && !uploaded && (
                <div
                    onClick={() => fileInputRef.current?.click()}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors"
                >
                    <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-600">Click to upload or drag & drop</p>
                    <p className="text-xs text-gray-400 mt-1">JPG, PNG, or PDF (max 5MB)</p>
                </div>
            )}

            {selectedFile && !uploaded && (
                <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-3">
                    <FileText className="w-8 h-8 text-indigo-500" />
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{selectedFile.name}</p>
                        <p className="text-xs text-gray-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                        onClick={handleRemoveFile}
                        className="p-1 hover:bg-gray-200 rounded-full transition-colors"
                    >
                        <X className="w-4 h-4 text-gray-500" />
                    </button>
                </div>
            )}

            {/* Validation Error Display */}
            {validationError && (
                <div className="bg-red-50 rounded-lg p-3 flex items-start gap-3">
                    <XCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                        <p className="text-sm font-medium text-red-700">Prescription Rejected</p>
                        <p className="text-xs text-red-600 mt-1">{validationError}</p>
                        <p className="text-xs text-gray-500 mt-2">Please upload a valid prescription with doctor's name, date, and medicine details.</p>
                    </div>
                </div>
            )}

            {uploaded && !validationError && (
                <div className="bg-green-50 rounded-lg p-3 flex items-center gap-3">
                    <CheckCircle className="w-8 h-8 text-green-500" />
                    <div className="flex-1">
                        <p className="text-sm font-medium text-green-700">Prescription Verified ✓</p>
                        <p className="text-xs text-green-600">Your order is being processed</p>
                    </div>
                </div>
            )}

            <div className="flex gap-2 mt-4">
                {!uploaded ? (
                    <>
                        <button
                            onClick={handleUpload}
                            disabled={!selectedFile || uploading}
                            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${selectedFile && !uploading
                                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                }`}
                        >
                            {uploading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                                    Uploading...
                                </span>
                            ) : (
                                'Upload Prescription'
                            )}
                        </button>
                        <button
                            onClick={onSkip}
                            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition-colors"
                        >
                            Skip
                        </button>
                    </>
                ) : null}
            </div>
        </div>
    );
}
