import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Your Pharma AI - Intelligent Pharmacy, Reimagined',
    description: 'Conversational AI that understands prescriptions, manages medicines, and assists patients like a real pharmacist.',
};

export default function LandingLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    // Landing page has its own layout - no sidebar, no app footer
    // This bypasses the root layout's Sidebar and footer
    return <>{children}</>;
}
