import dashboardExport from '@/public/data/dashboard_export.json';
import { CrimeAtlasDashboard } from '@/components/crime-atlas-dashboard';
import { parseDashboardData } from '@/lib/dashboard';

export const dynamic = 'force-static';

export default function Home() {
  return (
    <CrimeAtlasDashboard dashboard={parseDashboardData(dashboardExport)} />
  );
}
