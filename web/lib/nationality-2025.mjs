const metrics = ['cleared_cases', 'cleared_persons'];
const scopes = ['all_foreign', 'visiting_foreign'];
const countries = ['ベトナム', '中国', 'タイ', 'ブラジル', 'カンボジア'];

function assert(condition, message) {
  if (!condition) throw new Error(`Invalid 2025 supplement: ${message}`);
}
function count(value) {
  return Number.isSafeInteger(value) && value >= 0;
}
function equal(left, right) {
  return Math.abs(left - right) <= 1e-9 * Math.max(1, Math.abs(right));
}

export function parseNationality2025(data) {
  assert(
    data &&
      data.schema_version === 1 &&
      data.year === 2025 &&
      data.scale === 1000,
    'schema',
  );
  const labels = data.definitions?.entities;
  const categories = data.definitions?.categories;
  assert(
    Array.isArray(labels) &&
      labels.length === 30 &&
      new Set(labels).size === 30 &&
      labels[0] === '日本',
    'entities',
  );
  assert(
    Array.isArray(categories) &&
      categories.length === 6 &&
      new Set(categories.map((c) => c.id)).size === 6,
    'categories',
  );
  assert(
    Array.isArray(data.comparison) && data.comparison.length === 120,
    'comparison coverage',
  );
  const keys = new Set();
  for (const row of data.comparison) {
    assert(
      row.year === 2025 &&
        labels.includes(row.label) &&
        metrics.includes(row.metric) &&
        scopes.includes(row.scope),
      'comparison identity',
    );
    const key = `${row.label}/${row.metric}/${row.scope}`;
    assert(!keys.has(key), 'duplicate comparison');
    keys.add(key);
    assert(
      Array.isArray(row.warnings) &&
        row.warnings.includes('annual_flow_vs_population_stock') &&
        row.warnings.includes('different_population_reference_dates') &&
        row.warnings.every((w) => data.definitions.warning_labels[w]),
      'warnings',
    );
    assert(
      row.japanese_reference === (row.label === '日本'),
      'reference identity',
    );
    assert(row.numerator === null || count(row.numerator), 'numerator');
    assert(row.denominator === null || count(row.denominator), 'denominator');
    for (const [kind, value] of [
      ['numerator', row.numerator],
      ['denominator', row.denominator],
    ]) {
      const components = row[`${kind}_components`];
      assert(Array.isArray(components), 'components');
      for (const component of components) {
        assert(
          count(component.value) &&
            count(component.row) &&
            component.row > 0 &&
            count(component.column) &&
            component.column > 0 &&
            data.sources?.[component.source_id] &&
            typeof component.sheet === 'string' &&
            typeof component.source_table === 'string',
          'component provenance',
        );
      }
      if (value !== null) {
        assert(components.length > 0, 'missing provenance');
        const sum = components.reduce(
          (total, c) => total + (c.role === 'subtrahend' ? -c.value : c.value),
          0,
        );
        assert(sum === value, 'component arithmetic');
      } else assert(components.length === 0, 'unavailable component');
    }
    if (row.status === 'calculated') {
      assert(
        count(row.numerator) &&
          count(row.denominator) &&
          row.denominator > 0 &&
          Number.isFinite(row.value) &&
          equal(row.value, (row.numerator / row.denominator) * 1000) &&
          row.reason === null,
        'ratio',
      );
    } else {
      assert(
        row.status === 'refused' &&
          row.value === null &&
          data.definitions.reason_labels[row.reason],
        'unavailable is not zero',
      );
      if (
        row.reason === 'numerator_not_published' ||
        row.reason === 'japan_not_in_visiting_scope'
      )
        assert(row.numerator === null, 'missing numerator');
    }
    if (row.label === '日本' && row.scope === 'all_foreign') {
      assert(
        row.derivation === 'national_total_minus_all_foreign' &&
          row.warnings.includes('japanese_residual_reference') &&
          row.warnings.includes(
            'japanese_original_population_unknown_excluded',
          ),
        'Japanese residual',
      );
      assert(
        row.numerator_components.length === 2 &&
          row.numerator_components[0].role === 'minuend' &&
          row.numerator_components[1].role === 'subtrahend',
        'residual components',
      );
    }
    if (row.label === '日本' && row.scope === 'visiting_foreign')
      assert(
        row.reason === 'japan_not_in_visiting_scope',
        'Japan not visiting',
      );
    if (row.label === '中国')
      assert(
        row.warnings.includes('china_category_scope_mismatch'),
        'China scope',
      );
    if (row.label === '韓国・朝鮮')
      assert(
        row.warnings.includes('korea_population_aggregation'),
        'Korea aggregation',
      );
    if (row.label !== '日本') {
      assert(
        row.warnings.includes('residency_scope_mismatch'),
        'residency scope',
      );
      if (row.scope === 'visiting_foreign')
        assert(
          row.warnings.includes(
            'visiting_scope_vs_all_resident_foreign_population',
          ),
          'visiting denominator',
        );
    }
  }
  assert(
    Array.isArray(data.composition) && data.composition.length === 14,
    'composition coverage',
  );
  const compositionKeys = new Set();
  for (const row of data.composition) {
    assert(
      [...countries, '来日外国人総数', '日本'].includes(row.label) &&
        metrics.includes(row.metric) &&
        row.scope === 'visiting_foreign',
      'composition scope',
    );
    const key = `${row.label}/${row.metric}`;
    assert(!compositionKeys.has(key), 'duplicate composition');
    compositionKeys.add(key);
    assert(
      row.cells?.length === 6 &&
        new Set(row.cells.map((c) => c.category_id)).size === 6 &&
        row.cells.every((c) =>
          categories.some((category) => category.id === c.category_id),
        ),
      'cell coverage',
    );
    if (row.label === '日本') {
      assert(
        row.status === 'refused' &&
          row.total === null &&
          row.reason === 'japan_not_in_visiting_scope' &&
          row.cells.every(
            (c) => c.count === null && c.share === null && c.source === null,
          ),
        'Japan composition unavailable',
      );
    } else {
      assert(
        row.status === 'calculated' &&
          count(row.total) &&
          row.total > 0 &&
          row.reason === null,
        'composition total',
      );
      for (const cell of row.cells) {
        assert(
          count(cell.count) &&
            Number.isFinite(cell.share) &&
            equal(cell.share, (cell.count / row.total) * 100) &&
            cell.source?.source_id === 'S30' &&
            cell.source.value === cell.count &&
            count(cell.source.row) &&
            count(cell.source.column),
          'composition arithmetic/provenance',
        );
      }
      assert(
        row.cells.reduce((sum, cell) => sum + cell.count, 0) === row.total,
        'composition reconciliation',
      );
    }
  }
  for (const metric of metrics) {
    const order = data.cluster_orders?.[metric];
    assert(
      Array.isArray(order) &&
        order.length === 5 &&
        new Set(order).size === 5 &&
        order.every((label) => countries.includes(label)),
      'cluster membership',
    );
  }
  assert(data.contract_sha256?.match(/^[a-f0-9]{64}$/), 'contract pin');
  assert(
    Object.keys(data.sources ?? {})
      .sort()
      .join(',') === ['S19_2025', 'S21', 'S22', 'S27', 'S30'].sort().join(','),
    'sources',
  );
  for (const source of Object.values(data.sources)) {
    assert(
      source.sha256?.match(/^[a-f0-9]{64}$/) &&
        source.normalized_sha256?.match(/^[a-f0-9]{64}$/) &&
        source.landing_url?.startsWith('https://') &&
        source.download_url?.startsWith('https://'),
      'source pins',
    );
  }
  assert(
    !/\/Users\/|\/home\/|file:\/\//u.test(JSON.stringify(data)),
    'private path',
  );
  return data;
}
