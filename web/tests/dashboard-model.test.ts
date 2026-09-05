import { describe, expect, it } from 'vitest';

import dashboardFixture from '@/public/data/dashboard_export.json';
import {
  buildClearanceShareTrendViewModel,
  buildNationalityComparisonViewModel,
  buildOffenseCompositionViewModel,
  buildSelectableNationalityViewModel,
  buildNationalityViewModel,
  buildRegionalViewModel,
  NATIONALITY_PERSPECTIVES,
  parseDashboardData,
} from '@/lib/dashboard';
import { JAPAN_PREFECTURE_PATHS } from '@/lib/japan-map-paths.generated';

describe('regional dashboard model', () => {
  it('builds the all-resident recognized-case view without refused rows', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildRegionalViewModel(
      dashboard,
      'all_resident_recognized_cases',
      'ratio',
    );

    expect(view.prefectures).toHaveLength(47);
    expect(view.national.name).toBe('日本');
    expect(view.refusedCount).toBe(14);
    expect(view.prefectures[0].name).toBe('大阪府');
    expect(view.prefectures[0].value).toBeCloseTo(929.5763389);
    expect(view.tokyo.value).toBeCloseTo(668.3030047);
    expect(view.saitama.value).toBeCloseTo(704.6781233);
    expect(view.tokyo.rawCount).toBe(94_752);
    expect(view.saitama.rawCount).toBe(51_667);
    expect(view.warningCodes).toEqual(
      expect.arrayContaining([
        'annual_flow_vs_point_in_time_population',
        'numerator_residency_scope_not_established',
      ]),
    );
  });

  it('switches to absolute counts without changing source observations', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildRegionalViewModel(
      dashboard,
      'all_resident_recognized_cases',
      'count',
    );

    expect(view.unitLabel).toBe('件');
    expect(view.prefectures[0].name).toBe('東京都');
    expect(view.prefectures[0].value).toBe(94_752);
    expect(view.tokyo.referenceRatio).toBeCloseTo(668.3030047);
  });

  it('labels cleared-person observations as people in count mode', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildRegionalViewModel(
      dashboard,
      'all_resident_cleared_persons',
      'count',
    );

    expect(view.unitLabel).toBe('人');
    expect(view.rawCountLabel).toBe('人員');
    expect(view.tokyo.rawCount).toBe(23_731);
  });

  it('builds a signed same-year recognition-clearance gap without calling it unresolved', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildRegionalViewModel(
      dashboard,
      'all_resident_same_year_recognition_clearance_gap',
      'ratio',
    );

    expect(view.isSameYearGap).toBe(true);
    expect(view.unitLabel).toBe('%');
    expect(view.rawCountLabel).toBe('同年差分件数');
    expect(view.denominatorLabel).toBe('認知件数');
    expect(view.ratioDetailLabel).toBe('同年差分率');
    expect(view.national.value).toBeCloseTo(61.0571807);
    expect(view.national.rawCount).toBe(450_406);
    expect(view.national.denominatorValue).toBe(737_679);
    expect(view.tokyo.value).toBeCloseTo(64.1580125);
    expect(view.saitama.value).toBeCloseTo(67.6950471);
    expect(view.sources.map((source) => source.id)).toEqual(['S15']);
    expect(view.uiCaveat).toMatch(/未解決件数／未解決率ではない/);
  });

  it('joins every CC0 map path to the same prefecture code and label', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildRegionalViewModel(
      dashboard,
      'all_resident_recognized_cases',
      'ratio',
    );
    const labelsById = new Map(
      view.prefectures.map((row) => [row.id, row.name]),
    );

    expect(JAPAN_PREFECTURE_PATHS).toHaveLength(47);
    for (const path of JAPAN_PREFECTURE_PATHS) {
      expect(labelsById.get(`jp-prefecture:${path.code}`)).toBe(path.name);
    }
  });

  it('keeps the public provenance for both all-resident inputs', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildRegionalViewModel(
      dashboard,
      'all_resident_cleared_persons',
      'ratio',
    );

    expect(view.sources.map((source) => source.id)).toEqual(['S15', 'S16']);
    expect(view.sources.every((source) => source.publisher.length > 0)).toBe(
      true,
    );
    expect(
      view.sources.every((source) => source.landingUrl.startsWith('https://')),
    ).toBe(true);
  });

  it('rejects an unsupported compact export schema', () => {
    expect(() =>
      parseDashboardData({
        ...dashboardFixture,
        compact_export_schema_version: 99,
      }),
    ).toThrow(/schema version/i);
  });

  it('rejects a schema-v7 payload without required dashboard records', () => {
    expect(() =>
      parseDashboardData({
        compact_export_schema_version: 7,
        definitions: {},
        records: {},
        sources: {},
      }),
    ).toThrow(/missing the regional dashboard data/i);
  });

  it('stops when a required regional anchor is absent', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const withoutTokyo = {
      ...dashboard,
      records: {
        ...dashboard.records,
        all_resident_context: dashboard.records.all_resident_context.filter(
          (row) => row.geography_id !== 'jp-prefecture:13',
        ),
      },
    };

    expect(() =>
      buildRegionalViewModel(
        withoutTokyo,
        'all_resident_recognized_cases',
        'ratio',
      ),
    ).toThrow(/required regional datum is missing/i);
  });

  it('stops when a calculated row loses a required numeric value', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const withBrokenValue = {
      ...dashboard,
      records: {
        ...dashboard.records,
        all_resident_context: dashboard.records.all_resident_context.map(
          (row) =>
            row.geography_id === 'jp-prefecture:13' &&
            row.context_id === 'all_resident_recognized_cases'
              ? { ...row, numerator_value: null }
              : row,
        ),
      },
    };

    expect(() =>
      buildRegionalViewModel(
        withBrokenValue,
        'all_resident_recognized_cases',
        'ratio',
      ),
    ).toThrow(/has missing values/i);
  });

  it('stops when the selected regional definition is absent', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const contextIds = { ...dashboard.definitions.context_ids };
    delete contextIds.all_resident_recognized_cases;

    expect(() =>
      buildRegionalViewModel(
        {
          ...dashboard,
          definitions: { ...dashboard.definitions, context_ids: contextIds },
        },
        'all_resident_recognized_cases',
        'ratio',
      ),
    ).toThrow(/context definition is missing/i);
  });
});

describe('nationality offense composition model', () => {
  it('builds all 26 entities and all six exhaustive categories in cluster order', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildOffenseCompositionViewModel(
      dashboard,
      'cleared_persons',
      'cluster',
    );

    expect(view.entities).toHaveLength(26);
    expect(view.categories).toHaveLength(6);
    expect(view.entities.every((entity) => entity.cells.length === 6)).toBe(
      true,
    );
    expect(view.entities.map((entity) => entity.id)).toEqual(
      dashboard.definitions.offense_composition_ids[
        'nationality_criminal_code_offense_composition'
      ].clustering.cleared_persons.order,
    );
    expect(view.entities[0].name).toBe('無国籍');
    expect(view.categories[0]).toMatchObject({
      id: 'heinous',
      label: '凶悪犯',
      officialSeverityRole: 'official_high_severity_category',
    });
    expect(
      view.categories
        .slice(1)
        .every(
          (category) =>
            category.officialSeverityRole ===
            'not_a_project_severity_classification',
        ),
    ).toBe(true);
    for (const entity of view.entities) {
      expect(
        entity.cells.reduce((sum, cell) => sum + (cell.share ?? 0), 0),
      ).toBeCloseTo(1);
    }
  });

  it('keeps the Japanese residual and switches independently to case counts and source order', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const personsView = buildOffenseCompositionViewModel(
      dashboard,
      'cleared_persons',
      'cluster',
    );
    const casesView = buildOffenseCompositionViewModel(
      dashboard,
      'cleared_cases',
      'source',
    );
    const japanese = personsView.japaneseReference;
    const theft = japanese.cells.find((cell) => cell.offenseId === 'theft');

    expect(japanese).toMatchObject({
      name: '日本（残差による参考値）',
      total: 181_362,
      isJapaneseReference: true,
      derivationMethod: 'residual_subtraction',
    });
    expect(theft).toMatchObject({ count: 83_810 });
    expect(theft?.share).toBeCloseTo(83_810 / 181_362);
    expect(casesView.entities[0]).toMatchObject({
      id: 'jp-nationality:japanese',
      total: 268_412,
    });
    expect(casesView.metricLabel).toBe('検挙件数');
    expect(casesView.unitLabel).toBe('件');
    expect(
      casesView.entities.find((entity) => entity.name === '国籍不明')?.cells,
    ).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          share: null,
          shareStatus: 'refused_zero_total',
        }),
      ]),
    );
    expect(personsView.sources.map((source) => source.id)).toEqual([
      'S08',
      'S15',
    ]);
  });
});

describe('all-nationality comparison model', () => {
  it('keeps all categories in one descending reference-ratio order', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildNationalityComparisonViewModel(dashboard);

    expect(view.rows).toHaveLength(26);
    expect(view.calculatedRows).toHaveLength(22);
    expect(view.refusedCount).toBe(4);
    expect(
      view.rows.filter((row) => row.calculationStatus === 'refused'),
    ).toHaveLength(4);
    expect(view.orderedRows).toHaveLength(26);
    expect(view.orderedRows[0].name).toBe('無国籍');
    expect(
      view.orderedRows
        .filter((row) => row.referenceRatio !== null)
        .every(
          (row, index, rows) =>
            index === 0 ||
            (rows[index - 1].referenceRatio ?? -Infinity) >=
              (row.referenceRatio ?? -Infinity),
        ),
    ).toBe(true);
    expect(
      view.orderedRows.slice(-4).every((row) => row.referenceRatio === null),
    ).toBe(true);
    expect(view.highRows.map((row) => row.name)).toEqual([
      '無国籍',
      'イラン',
      'パキスタン',
      'アメリカ',
      'ロシア',
    ]);
    expect(view.lowRows.map((row) => row.name)).toEqual([
      'インドネシア',
      'ドイツ',
      '日本（残差による参考値）',
      'インド',
      'イタリア',
    ]);
    expect(view.highRows[0].warningCodes).toEqual([
      'small_denominator_base',
      'sparse_numerator_count',
    ]);
    expect(view.defaultDisplayBehavior).toBe('include_all_with_warnings');
    expect(view.interpretationPolicy).toBe(
      'observed_values_without_intrinsic_group_inference',
    );
  });

  it('includes the Japanese residual reference on the same per-1,000 scale', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildNationalityComparisonViewModel(dashboard);

    expect(view.unitLabel).toBe('人口1,000人当たり');
    expect(view.japaneseReference).toMatchObject({
      name: '日本（残差による参考値）',
      numerator: 181_362,
      denominator: 120_296_000,
      referenceRatio: 1.507631176431469,
      calculationStatus: 'calculated',
      numeratorSourceIds: ['S08', 'S15'],
      denominatorSourceId: 'S17',
      derivationMethod: 'residual_subtraction',
    });
    expect(view.japaneseReference.mismatchCodes).toEqual(
      expect.arrayContaining([
        'japanese_numerator_derived_by_residual_subtraction',
        'all_persons_minus_all_foreign_scope_assumption',
      ]),
    );
    expect(view.sources.map((source) => source.id)).toEqual([
      'S08',
      'S14_2024_12',
      'S15',
      'S17',
    ]);
  });

  it('stops if the comparison definition is absent', () => {
    const dashboard = parseDashboardData(dashboardFixture);

    expect(() =>
      buildNationalityComparisonViewModel({
        ...dashboard,
        definitions: {
          ...dashboard.definitions,
          nationality_comparison_ids: {},
        },
      }),
    ).toThrow(/comparison definition is missing/i);
  });

  it('stops if a calculated comparison row loses its denominator', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const brokenDashboard = {
      ...dashboard,
      records: {
        ...dashboard.records,
        nationality_comparison: dashboard.records.nationality_comparison.map(
          (row) =>
            row.is_japanese_reference
              ? { ...row, denominator_value: null }
              : row,
        ),
      },
    };

    expect(() => buildNationalityComparisonViewModel(brokenDashboard)).toThrow(
      /comparison row .* has missing values/i,
    );
  });
});

describe('national clearance foreign-share trend model', () => {
  it('keeps ten years of direct foreign scopes and their residual', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildClearanceShareTrendViewModel(dashboard, 'cleared_cases');

    expect(view.points).toHaveLength(10);
    expect(view.years).toEqual([
      2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024,
    ]);
    const latest = view.points.at(-1);
    expect(latest).toMatchObject({
      year: 2024,
      allPersonsTotal: 287_273,
      allForeignCount: 18_861,
      visitingForeignCount: 13_405,
      allForeignMinusVisitingCount: 5_456,
    });
    expect(latest?.allForeignShare).toBeCloseTo(6.565531742);
    expect(latest?.visitingForeignShare).toBeCloseTo(4.666293038);
    expect(latest?.allForeignMinusVisitingShare).toBeCloseTo(
      ((18_861 - 13_405) / 287_273) * 100,
    );
    expect(view.metricLabel).toBe('検挙件数');
    expect(view.sources.map((source) => source.id)).toEqual([
      'S08',
      'S09',
      'S15',
    ]);
    expect(view.uiCaveat).toMatch(/人口当たりの犯罪率/);
  });

  it('switches to cleared persons without changing the year grid', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildClearanceShareTrendViewModel(
      dashboard,
      'cleared_persons',
    );

    expect(view.points).toHaveLength(10);
    const latest = view.points.at(-1);
    expect(latest).toMatchObject({
      year: 2024,
      allPersonsTotal: 191_826,
      allForeignCount: 10_464,
      visitingForeignCount: 6_368,
      allForeignMinusVisitingCount: 4_096,
    });
    expect(latest?.allForeignShare).toBeCloseTo(5.454943543);
    expect(latest?.visitingForeignShare).toBeCloseTo(3.319675122);
    expect(latest?.allForeignMinusVisitingShare).toBeCloseTo(
      ((10_464 - 6_368) / 191_826) * 100,
    );
    expect(view.metricLabel).toBe('検挙人員');
  });

  it.each([
    'scope_source_binding',
    'residual_label',
    'required_warnings',
    'source_components',
    'interpretation_policy',
    'ui_caveat',
    'metric_label',
    'source_coordinates',
  ])('rejects unsafe clearance-share semantics: %s', (mutation) => {
    const dashboard = structuredClone(parseDashboardData(dashboardFixture));
    const rows = dashboard.records.clearance_share_trends;

    if (mutation === 'scope_source_binding') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign') {
          row.numerator_source_id = 'S09';
          row.numerator_source_ids = ['S09'];
        } else if (row.foreign_scope === 'visiting_foreign') {
          row.numerator_source_id = 'S08';
          row.numerator_source_ids = ['S08'];
        } else {
          row.numerator_source_id = 'S09';
          row.numerator_source_ids = ['S09', 'S08'];
        }
      }
    } else if (mutation === 'residual_label') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          row.foreign_scope_label_ja = '在留外国人';
        }
      }
    } else if (mutation === 'required_warnings') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          row.mismatch_flags = [];
        }
      }
    } else if (mutation === 'source_components') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          Object.assign(row, { source_components: [] });
        }
      }
    } else if (mutation === 'interpretation_policy') {
      Object.assign(
        dashboard.definitions.clearance_share_ids[
          'national_criminal_code_clearance_foreign_share'
        ],
        { interpretation_policy: 'population_crime_rate' },
      );
    } else if (mutation === 'ui_caveat') {
      dashboard.definitions.clearance_share_ids[
        'national_criminal_code_clearance_foreign_share'
      ].ui_caveat = '在留外国人の犯罪率を示す。';
    } else if (mutation === 'metric_label') {
      for (const row of rows) row.metric_label_ja = '犯罪率';
    } else if (mutation === 'source_coordinates') {
      for (const row of rows) {
        if (row.foreign_scope === 'all_foreign_minus_visiting_foreign') {
          row.source_components[0].source_table = '999';
          row.source_components[0].source_row = 999;
        }
      }
    }

    expect(() =>
      buildClearanceShareTrendViewModel(dashboard, 'cleared_cases'),
    ).toThrow(/clearance-share semantic contract/i);
  });
});

describe('selectable all-nationality comparison model', () => {
  it('offers every currently exported numerator and scope perspective', () => {
    expect(NATIONALITY_PERSPECTIVES).toHaveLength(10);
    expect(
      NATIONALITY_PERSPECTIVES.map((perspective) => perspective.id),
    ).toEqual([
      'nationality_criminal_code_cleared_persons',
      'nationality_criminal_code_cleared_cases',
      'x_cleared_persons_exact',
      'x_cleared_cases_exact',
      'y_cleared_persons_exact',
      'y_cleared_cases_exact',
      'x_cleared_persons_as_published_mismatch',
      'x_cleared_cases_as_published_mismatch',
      'y_cleared_persons_as_published_mismatch',
      'y_cleared_cases_as_published_mismatch',
    ]);
  });

  it('builds the Japanese-inclusive criminal-code cleared-case perspective', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildSelectableNationalityViewModel(
      dashboard,
      'nationality_criminal_code_cleared_cases',
      'ratio',
    );

    expect(view.rows).toHaveLength(26);
    expect(view.calculatedRows).toHaveLength(22);
    expect(view.refusedCount).toBe(4);
    expect(view.numeratorLabel).toBe('検挙件数');
    expect(view.rawUnitLabel).toBe('件');
    expect(view.scopeLabel).toMatch(/刑法犯.*検挙件数.*日本/);
    expect(view.japaneseReference).toMatchObject({
      numerator: 268_412,
      denominator: 120_296_000,
      referenceRatio: 2.231262884883953,
      calculationStatus: 'calculated',
      derivationMethod: 'residual_subtraction',
    });
    expect(
      view.rows.find((row) => row.publishedLabel === 'ベトナム'),
    ).toMatchObject({
      numerator: 6_164,
      numeratorSourceIds: ['S08'],
    });
  });

  it('keeps the Japanese-inclusive criminal-code view as the default perspective', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildSelectableNationalityViewModel(
      dashboard,
      'nationality_criminal_code_cleared_persons',
      'ratio',
    );

    expect(view.rows).toHaveLength(26);
    expect(view.calculatedRows).toHaveLength(22);
    expect(view.refusedCount).toBe(4);
    expect(view.numeratorLabel).toBe('検挙人員');
    expect(view.scopeLabel).toMatch(/刑法犯.*日本/);
    expect(view.japaneseReference).toMatchObject({
      numerator: 181_362,
      denominator: 120_296_000,
      referenceRatio: 1.507631176431469,
      calculationStatus: 'calculated',
    });
  });

  it('reveals the former total-scope numerator and keeps every source row', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildSelectableNationalityViewModel(
      dashboard,
      'x_cleared_persons_exact',
      'ratio',
    );

    expect(view.rows).toHaveLength(25);
    expect(view.calculatedRows).toHaveLength(18);
    expect(view.refusedCount).toBe(7);
    expect(view.highRows.map((row) => row.name)).toEqual([
      'イラン',
      'タイ',
      '無国籍',
      'ベトナム',
      'パキスタン',
    ]);
    expect(view.lowRows.map((row) => row.name)).toEqual([
      'インド',
      'イギリス',
      'インドネシア',
      'ドイツ',
      'イタリア',
    ]);
    expect(
      view.rows.find((row) => row.publishedLabel === 'ベトナム'),
    ).toMatchObject({
      numerator: 4_113,
      denominator: 634_361,
      referenceRatio: 6.483689886358083,
      value: 6.483689886358083,
    });
    expect(
      view.rows
        .filter((row) => row.publishedLabel === 'その他')
        .map((row) => row.name),
    ).toEqual([
      'その他（アジア州の国）',
      'その他（ヨーロッパ州の国）',
      'その他（南北アメリカ州の国）',
    ]);
    expect(view.japaneseReference).toMatchObject({
      name: '日本（対応する公表分子なし）',
      numerator: null,
      denominator: 120_296_000,
      referenceRatio: null,
      value: null,
      calculationStatus: 'refused',
      refusalReason: 'compatible_japanese_numerator_not_available',
      numeratorSourceIds: [],
      denominatorSourceId: 'S17',
    });
  });

  it('uses every published numerator in count mode, including ratio-refused rows', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildSelectableNationalityViewModel(
      dashboard,
      'x_cleared_persons_exact',
      'count',
    );

    expect(view.unitLabel).toBe('人');
    expect(view.highRows[0]).toMatchObject({
      publishedLabel: 'ベトナム',
      numerator: 4_113,
      value: 4_113,
    });
    expect(view.highRows).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          publishedLabel: '中国',
          numerator: 3_522,
          calculationStatus: 'refused',
        }),
      ]),
    );
  });

  it('builds every perspective without dropping its serialized source rows', () => {
    const dashboard = parseDashboardData(dashboardFixture);

    for (const perspective of NATIONALITY_PERSPECTIVES) {
      const view = buildSelectableNationalityViewModel(
        dashboard,
        perspective.id,
        'ratio',
      );
      const serializedCount =
        perspective.id === 'nationality_criminal_code_cleared_persons'
          ? dashboard.records.nationality_comparison.filter(
              (row) => row.comparison_id === perspective.id,
            ).length
          : perspective.id === 'nationality_criminal_code_cleared_cases'
            ? new Set(
                dashboard.records.offense_composition.map(
                  (row) => row.entity_id,
                ),
              ).size
            : dashboard.records.nationality_indicators.filter(
                (row) => row.indicator_id === perspective.id,
              ).length;

      expect(view.rows).toHaveLength(
        serializedCount +
          (perspective.id === 'nationality_criminal_code_cleared_persons' ||
          perspective.id === 'nationality_criminal_code_cleared_cases'
            ? 0
            : 1),
      );
      expect(view.highRows).toHaveLength(5);
      expect(view.lowRows).toHaveLength(5);
      expect(view.japaneseReference.publishedLabel).toBe('日本');
    }
  });

  it('makes the Vietnam scope change explicit instead of presenting it as a trend', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const criminalCode = buildSelectableNationalityViewModel(
      dashboard,
      'nationality_criminal_code_cleared_persons',
      'ratio',
    );
    const total = buildSelectableNationalityViewModel(
      dashboard,
      'x_cleared_persons_exact',
      'ratio',
    );

    const criminalCodeVietnam = criminalCode.rows.find(
      (row) => row.publishedLabel === 'ベトナム',
    );
    expect(criminalCodeVietnam).toMatchObject({
      numerator: 1_679,
      year: 2024,
    });
    expect(criminalCodeVietnam?.referenceRatio).toBeCloseTo(2.646757919078);
    expect(
      total.rows.find((row) => row.publishedLabel === 'ベトナム'),
    ).toMatchObject({
      numerator: 4_113,
      referenceRatio: 6.483689886358083,
      year: 2024,
    });
    expect(criminalCode.scopeLabel).not.toBe(total.scopeLabel);
  });
});

describe('nationality dashboard model', () => {
  it('keeps the nationwide nationality view secondary and excludes flagged rows from ranking', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildNationalityViewModel(
      dashboard,
      'x_cleared_persons_exact',
      'ratio',
    );

    expect(view.year).toBe(2024);
    expect(view.geographyLabel).toBe('日本全国');
    expect(view.rankingRows).toHaveLength(16);
    expect(view.rankingRows[0].name).toBe('イラン');
    expect(view.rankingRows[0].value).toBeCloseTo(12.9574903);
    expect(view.excludedRows.map((row) => row.name)).toEqual([
      '無国籍',
      'イタリア',
    ]);
    expect(view.refusedCount).toBe(6);
    expect(view.refusalReasons).toEqual([
      { reason: 'crosswalk_not_exact', count: 6 },
    ]);
    expect(view.warningCodes).toEqual(
      expect.arrayContaining([
        'small_denominator_base',
        'sparse_numerator_count',
      ]),
    );
    expect(view.mismatchCodes).toEqual(
      expect.arrayContaining([
        'all_foreign_vs_resident_population_mismatch',
        'annual_flow_vs_point_in_time_stock',
        'cleared_person_records_not_unique_risk_population',
      ]),
    );
    expect(view.sources.map((source) => source.id)).toEqual([
      'S08',
      'S14_2024_12',
    ]);
  });

  it('sorts nationwide nationality observations by count without restoring excluded rows', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const view = buildNationalityViewModel(
      dashboard,
      'x_cleared_persons_exact',
      'count',
    );

    expect(view.unitLabel).toBe('人');
    expect(view.rankingRows[0]).toMatchObject({
      name: 'ベトナム',
      value: 4113,
      numerator: 4113,
    });
    expect(view.rankingRows.some((row) => row.name === '無国籍')).toBe(false);
  });

  it('stops when the selected nationality definition is absent', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const indicatorIds = { ...dashboard.definitions.indicator_ids };
    delete indicatorIds.x_cleared_persons_exact;

    expect(() =>
      buildNationalityViewModel(
        {
          ...dashboard,
          definitions: {
            ...dashboard.definitions,
            indicator_ids: indicatorIds,
          },
        },
        'x_cleared_persons_exact',
        'ratio',
      ),
    ).toThrow(/indicator definition is missing/i);
  });

  it('stops when a calculated nationality row loses a required numeric value', () => {
    const dashboard = parseDashboardData(dashboardFixture);
    const brokenDashboard = {
      ...dashboard,
      records: {
        ...dashboard.records,
        nationality_indicators: dashboard.records.nationality_indicators.map(
          (row) =>
            row.indicator_id === 'x_cleared_persons_exact' &&
            row.published_label === 'イギリス'
              ? { ...row, denominator_value: null }
              : row,
        ),
      },
    };

    expect(() =>
      buildNationalityViewModel(
        brokenDashboard,
        'x_cleared_persons_exact',
        'ratio',
      ),
    ).toThrow(/nationality row .* has missing values/i);
  });
});
