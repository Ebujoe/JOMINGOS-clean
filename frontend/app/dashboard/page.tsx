import AlertDashboard from '@/components/AlertDashboard';

export const metadata = {
  title: 'Alerts Dashboard - Jomingos',
  description: 'View and manage patient deterioration alerts',
};

export default function DashboardPage() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5', paddingTop: '20px' }}>
      <AlertDashboard />
    </div>
  );
}
