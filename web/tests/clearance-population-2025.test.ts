import { describe, expect, it } from 'vitest';
import { validate2025ClearancePopulationRow } from '@/lib/clearance-population-2025.mjs';
import fixture from '@/public/data/dashboard_export.json';

export function population2025Row(group: string, metric: string) {
  const row = structuredClone(fixture.records.clearance_population_trends.find(r => r.year === 2024 && r.population_group === group && r.metric === metric)!);
  const japanese = group === 'japanese_etc_residual';
  const cases = metric === 'cleared_cases';
  const numerator = japanese ? (cases ? 278138 : 189309) : (cases ? 22917 : 11354);
  const denominator = japanese ? 117405318 : 4125395;
  const component = (role: string, value: number, sourceRow: number) => ({source_id:'S21', source_table:'3-3-1', source_sheet:'3-3-1', source_row:sourceRow, source_column:14, metric, value, role});
  return {...row, year:2025, numerator_value:numerator, denominator_value:denominator,
    numerator_source_ids:['S21'], denominator_source_id:japanese?'S27':'S19_2025',
    population_reference_date:japanese?'2025-10-01':'2025-12-31', denominator_rounding:japanese?'none':'as_published_persons',
    quotient:numerator/denominator, display_value:numerator/denominator*1000,
    derivation_formula:japanese?`(S21.all_persons.${metric} - S21.all_foreign.${metric}) / S27.population * 1000`:`S21.all_foreign.${metric} / S19_2025.population * 1000`,
    mismatch_flags:[...row.mismatch_flags.filter(f=>f!=='japanese_population_rounded_to_nearest_1000'), ...(japanese?['census_original_nationality_population','census_nationality_unknown_excluded_from_japanese_denominator','population_source_changed_to_census']:[])],
    source_components:japanese?[
      component('numerator_minuend', cases?301055:200663, cases?4:7), component('numerator_subtrahend', cases?22917:11354, cases?5:8),
      {source_id:'S27', source_table:'49-1', source_sheet:'b49_01', source_row:11, source_column:31, metric:'population', value:denominator, published_value:denominator, published_unit:'persons', role:'denominator', value_basis:'original', excluded_unknown_population:2105452},
    ]:[component('numerator', numerator, cases?5:8), {source_id:'S19_2025', source_table:'1', source_sheet:'25-12-01m', source_row:5, source_column:5, metric:'population', value:denominator, published_value:denominator, published_unit:'persons', role:'denominator'}],
  };
}

describe('2025 population reference publication binding', () => {
  it.each(['japanese_etc_residual','all_foreign'].flatMap(group=>['cleared_cases','cleared_persons'].map(metric=>[group,metric])))('accepts reviewed %s/%s coordinates and arithmetic', (group,metric)=>{
    expect(()=>validate2025ClearancePopulationRow(population2025Row(group,metric))).not.toThrow();
  });
  it.each(['coordinate','rounding','basis','unknown','scope','flags','arithmetic'])('rejects changed %s', change=>{
    const row:any=population2025Row('japanese_etc_residual','cleared_persons');
    if(change==='coordinate')row.source_components[0].source_row=4;
    if(change==='rounding')row.denominator_rounding='nearest_1000_persons';
    if(change==='basis')row.source_components[2].value_basis='official_imputed_reference';
    if(change==='unknown')delete row.source_components[2].excluded_unknown_population;
    if(change==='scope')row.numerator_source_ids=['S08'];
    if(change==='flags')row.mismatch_flags=[];
    if(change==='arithmetic')row.display_value=0;
    expect(()=>validate2025ClearancePopulationRow(row)).toThrow(/semantic contract/);
  });
});
