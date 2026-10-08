export type SupplementMetric = 'cleared_cases' | 'cleared_persons';
export type SupplementScope = 'all_foreign' | 'visiting_foreign';
export interface SourceComponent {
  source_id: string;
  source_table: string;
  sheet: string;
  row: number;
  column: number;
  value: number;
  role: string;
}
export interface Comparison2025 {
  label: string;
  year: 2025;
  scope: SupplementScope;
  metric: SupplementMetric;
  numerator: number | null;
  denominator: number | null;
  value: number | null;
  status: 'calculated' | 'refused';
  reason: string | null;
  japanese_reference: boolean;
  derivation: string | null;
  warnings: string[];
  numerator_components: SourceComponent[];
  denominator_components: SourceComponent[];
}
export interface Composition2025 {
  label: string;
  metric: SupplementMetric;
  scope: 'visiting_foreign';
  total: number | null;
  status: 'calculated' | 'refused';
  reason: string | null;
  cells: {
    category_id: string;
    count: number | null;
    share: number | null;
    source: SourceComponent | null;
  }[];
}
export interface Nationality2025Data {
  schema_version: 1;
  year: 2025;
  scale: 1000;
  contract_sha256: string;
  definitions: {
    entities: string[];
    categories: { id: string; label: string }[];
    warning_labels: Record<string, string>;
    reason_labels: Record<string, string>;
    notes: string[];
    clustering: string;
  };
  comparison: Comparison2025[];
  composition: Composition2025[];
  cluster_orders: Record<SupplementMetric, string[]>;
  sources: Record<
    string,
    {
      publisher: string;
      dataset: string;
      source_table: string;
      landing_url: string;
      download_url: string;
      sha256: string;
      normalized_sha256: string;
      retrieved_at: string;
      revision: string;
    }
  >;
}
export function parseNationality2025(data: unknown): Nationality2025Data;
