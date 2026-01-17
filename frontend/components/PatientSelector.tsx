'use client';

import { User } from 'lucide-react';

interface Patient {
    patient_id: string;
    patient_name: string;
    patient_email: string;
    patient_phone: string;
}

// { patients, onSelect } removed as they are no longer needed
// interface PatientSelectorProps {
//     selectedPatient: Patient | null;
// }

export default function PatientSelector({ selectedPatient }: { selectedPatient: Patient | null }) {
    return (
        <div className="relative">
            <div
                className="flex items-center gap-3 px-4 py-2 bg-white rounded-lg border border-gray-200 min-w-[200px]"
            >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 flex items-center justify-center">
                    <User className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 text-left">
                    <p className="text-sm font-medium text-gray-900">
                        {selectedPatient?.patient_name || 'Select Patient'}
                    </p>
                    <p className="text-xs text-gray-500">
                        {selectedPatient?.patient_id || 'No patient selected'}
                    </p>
                </div>
            </div>
        </div>
    );
}
