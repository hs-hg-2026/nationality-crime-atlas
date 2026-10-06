/** Validate the independently reviewed 2025 source coordinates and semantics. */
export function validate2025ClearancePopulationRow(row) {
  const fail = () => {
    throw new Error(
      'Clearance-population semantic contract: 2025 source binding differs.',
    );
  };
  const japanese = row?.population_group === 'japanese_etc_residual';
  const cases = row?.metric === 'cleared_cases';
  const metric = row?.metric;
  if (
    row?.year !== 2025 ||
    !['cleared_cases', 'cleared_persons'].includes(metric) ||
    !['japanese_etc_residual', 'all_foreign'].includes(row.population_group)
  )
    fail();
  const numerator = japanese
    ? cases
      ? 278138
      : 189309
    : cases
      ? 22917
      : 11354;
  const denominator = japanese ? 117405318 : 4125395;
  const required = [
    'annual_clearance_flow_vs_point_in_time_population_stock',
    'numerator_residency_scope_not_established',
    'public_data_reference_ratio_not_official_crime_rate',
    ...(japanese
      ? [
          'japanese_numerator_is_arithmetic_residual',
          'october_1_population_reference_date',
          'census_original_nationality_population',
          'census_nationality_unknown_excluded_from_japanese_denominator',
          'population_source_changed_to_census',
        ]
      : [
          'all_foreign_numerator_vs_resident_foreigner_denominator',
          'december_31_population_reference_date',
        ]),
  ];
  const sourceId = japanese ? 'S27' : 'S19_2025';
  if (
    row.calculation_status !== 'calculated' ||
    row.refusal_reason !== null ||
    row.numerator_value !== numerator ||
    row.denominator_value !== denominator ||
    JSON.stringify(row.numerator_source_ids) !== '["S21"]' ||
    row.denominator_source_id !== sourceId ||
    row.population_scope !==
      (japanese ? 'japanese_population' : 'resident_foreigner_population') ||
    row.population_reference_date !==
      (japanese ? '2025-10-01' : '2025-12-31') ||
    row.denominator_rounding !== (japanese ? 'none' : 'as_published_persons') ||
    row.derivation_method !==
      (japanese
        ? 'arithmetic_residual_all_person_minus_all_foreign_division'
        : 'direct_published_count_division') ||
    row.derivation_formula !==
      (japanese
        ? `(S21.all_persons.${metric} - S21.all_foreign.${metric}) / S27.population * 1000`
        : `S21.all_foreign.${metric} / S19_2025.population * 1000`) ||
    !Array.isArray(row.mismatch_flags) ||
    !required.every((flag) => row.mismatch_flags.includes(flag)) ||
    row.mismatch_flags.includes(
      'japanese_population_rounded_to_nearest_1000',
    ) ||
    (row.display_multiplier !== undefined && row.display_multiplier !== 1000) ||
    !Number.isFinite(row.quotient) ||
    !Number.isFinite(row.display_value) ||
    Math.abs(row.quotient - numerator / denominator) > 1e-12 ||
    Math.abs(row.display_value - (numerator / denominator) * 1000) > 1e-10
  )
    fail();
  const clearance = (role, value, sourceRow) => ({
    source_id: 'S21',
    role,
    metric,
    value,
    source_table: '3-3-1',
    source_sheet: '3-3-1',
    source_row: sourceRow,
    source_column: 14,
  });
  const population = {
    source_id: sourceId,
    role: 'denominator',
    metric: 'population',
    value: denominator,
    published_value: denominator,
    published_unit: 'persons',
    source_table: japanese ? '49-1' : '1',
    source_sheet: japanese ? 'b49_01' : '25-12-01m',
    source_row: japanese ? 11 : 5,
    source_column: japanese ? 31 : 5,
    ...(japanese
      ? { value_basis: 'original', excluded_unknown_population: 2105452 }
      : {}),
  };
  const expected = japanese
    ? [
        clearance('numerator_minuend', cases ? 301055 : 200663, cases ? 4 : 7),
        clearance('numerator_subtrahend', cases ? 22917 : 11354, cases ? 5 : 8),
        population,
      ]
    : [clearance('numerator', numerator, cases ? 5 : 8), population];
  if (
    !Array.isArray(row.source_components) ||
    row.source_components.length !== expected.length ||
    expected.some(
      (component, index) =>
        !row.source_components[index] ||
        Object.entries(component).some(
          ([key, value]) => row.source_components[index][key] !== value,
        ),
    )
  )
    fail();
}
