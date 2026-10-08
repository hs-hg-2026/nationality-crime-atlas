import dashboardExport from '@/public/data/dashboard_export.json';
import nationality2025 from '@/public/data/nationality_2025.json';
import { CrimeAtlasDashboard } from '@/components/crime-atlas-dashboard';
import { parseDashboardData } from '@/lib/dashboard';
import { parseNationality2025 } from '@/lib/nationality-2025.mjs';

export const dynamic = 'force-static';

export default function Home() {
  return (
    <CrimeAtlasDashboard
      dashboard={parseDashboardData(dashboardExport)}
      nationality2025={parseNationality2025(nationality2025)}
    />
  );
}
