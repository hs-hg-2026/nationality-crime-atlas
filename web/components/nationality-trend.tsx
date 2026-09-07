'use client';

/* oxlint-disable jsx-a11y/prefer-tag-over-role -- an inline SVG needs an accessible image role. */

export type NationalityTrendMetric = 'cases' | 'persons';
export type NationalityTrendCalculationStatus = 'calculated' | 'refused';

export interface NationalityTrendValue {
  year: number;
  /** Numeric value used only for the heatmap scale and selected-series plot. */
  value: number | null;
  /** Preformatted public value. It is deliberately not reconstructed in the UI. */
  displayValue: string | null;
  numerator: number | null;
  denominator: number | null;
  calculationStatus: NationalityTrendCalculationStatus;
  refusalCode?: string | null;
  warningCodes: string[];
}

export interface NationalityTrendRow {
  entityId: string;
  label: string;
  japaneseReference: boolean;
  values: NationalityTrendValue[];
}

export interface NationalityTrendProps {
  selectedMetric: NationalityTrendMetric;
  years: number[];
  rows: NationalityTrendRow[];
  selectedEntityId: string;
  caveat?: string;
  warningLabels?: Readonly<Record<string, string>>;
  refusalLabels?: Readonly<Record<string, string>>;
  onMetricChange: (metric: NationalityTrendMetric) => void;
  onEntityChange: (entityId: string) => void;
}

const metricLabels: Record<NationalityTrendMetric, string> = {
  cases: '検挙件数',
  persons: '検挙人員',
};

function valueForYear(row: NationalityTrendRow, year: number) {
  return row.values.find((value) => value.year === year) ?? null;
}

const LOW_HEAT_COLOUR = [219, 238, 246] as const;
const HIGH_HEAT_COLOUR = [194, 65, 12] as const;

function heatIntensity(value: number | null, minimum: number, maximum: number) {
  if (value === null || !Number.isFinite(value)) return undefined;
  if (maximum <= minimum) return 0.5;
  return Math.min(Math.max((value - minimum) / (maximum - minimum), 0), 1);
}

function heatColor(value: number | null, minimum: number, maximum: number) {
  const intensity = heatIntensity(value, minimum, maximum);
  if (intensity === undefined) return undefined;
  const channels = LOW_HEAT_COLOUR.map((low, index) =>
    Math.round(low + (HIGH_HEAT_COLOUR[index] - low) * intensity),
  );
  return `rgb(${channels.join(' ')})`;
}

function heatTextColor(value: number | null, minimum: number, maximum: number) {
  const intensity = heatIntensity(value, minimum, maximum);
  return intensity !== undefined && intensity >= 0.68 ? '#fffaf5' : undefined;
}

function standardizedProfile(row: NationalityTrendRow, years: number[]) {
  const raw = years.map((year) => valueForYear(row, year)?.value ?? null);
  const finite = raw.filter(
    (value): value is number => value !== null && Number.isFinite(value),
  );
  if (finite.length < 2) return null;
  const mean = finite.reduce((sum, value) => sum + value, 0) / finite.length;
  const variance =
    finite.reduce((sum, value) => sum + (value - mean) ** 2, 0) / finite.length;
  const standardDeviation = Math.sqrt(variance);
  return raw.map((value) => {
    if (value === null || !Number.isFinite(value)) return null;
    return standardDeviation === 0 ? 0 : (value - mean) / standardDeviation;
  });
}

function profileDistance(
  left: Array<number | null>,
  right: Array<number | null>,
) {
  const squaredDifferences = left.flatMap((value, index) => {
    const other = right[index];
    return value === null || other === null ? [] : [(value - other) ** 2];
  });
  if (squaredDifferences.length === 0) return Number.POSITIVE_INFINITY;
  return Math.sqrt(
    squaredDifferences.reduce((sum, value) => sum + value, 0) /
      squaredDifferences.length,
  );
}

/**
 * Orders row-standardized time-series profiles with deterministic average-linkage
 * hierarchical clustering. Rows without at least two values remain visible last.
 */
export function orderRowsByHierarchicalClustering(
  rows: NationalityTrendRow[],
  years: number[],
) {
  const indexedRows = rows.map((row, index) => ({
    row,
    index,
    profile: standardizedProfile(row, years),
  }));
  const unavailable = indexedRows.filter((item) => item.profile === null);
  let clusters = indexedRows
    .filter(
      (item): item is typeof item & { profile: Array<number | null> } =>
        item.profile !== null,
    )
    .map((item) => ({ members: [item] }));

  const clusterDistance = (
    left: (typeof clusters)[number],
    right: (typeof clusters)[number],
  ) => {
    const distances = left.members.flatMap((leftMember) =>
      right.members.map((rightMember) =>
        profileDistance(leftMember.profile, rightMember.profile),
      ),
    );
    return distances.reduce((sum, value) => sum + value, 0) / distances.length;
  };
  const firstIndex = (cluster: (typeof clusters)[number]) =>
    Math.min(...cluster.members.map((member) => member.index));

  while (clusters.length > 1) {
    let bestLeft = 0;
    let bestRight = 1;
    let bestDistance = clusterDistance(clusters[0], clusters[1]);
    for (let left = 0; left < clusters.length - 1; left += 1) {
      for (let right = left + 1; right < clusters.length; right += 1) {
        const distance = clusterDistance(clusters[left], clusters[right]);
        const currentTieBreaker = [
          firstIndex(clusters[left]),
          firstIndex(clusters[right]),
        ].sort((a, b) => a - b);
        const bestTieBreaker = [
          firstIndex(clusters[bestLeft]),
          firstIndex(clusters[bestRight]),
        ].sort((a, b) => a - b);
        if (
          distance < bestDistance - Number.EPSILON ||
          (Math.abs(distance - bestDistance) <= Number.EPSILON &&
            (currentTieBreaker[0] < bestTieBreaker[0] ||
              (currentTieBreaker[0] === bestTieBreaker[0] &&
                currentTieBreaker[1] < bestTieBreaker[1])))
        ) {
          bestLeft = left;
          bestRight = right;
          bestDistance = distance;
        }
      }
    }
    const selected = [clusters[bestLeft], clusters[bestRight]].sort(
      (left, right) => firstIndex(left) - firstIndex(right),
    );
    const merged = { members: selected.flatMap((cluster) => cluster.members) };
    clusters = clusters.filter(
      (_cluster, index) => index !== bestLeft && index !== bestRight,
    );
    clusters.push(merged);
    clusters.sort((left, right) => firstIndex(left) - firstIndex(right));
  }

  return [
    ...(clusters[0]?.members.map((member) => member.row) ?? []),
    ...unavailable.map((item) => item.row),
  ];
}

function lineSegments(
  values: NationalityTrendValue[],
  xFor: (index: number) => number,
  yFor: (value: number) => number,
) {
  const segments: string[] = [];
  let current: string[] = [];

  for (const [index, item] of values.entries()) {
    if (item.value === null || !Number.isFinite(item.value)) {
      if (current.length > 0) segments.push(current.join(' '));
      current = [];
      continue;
    }
    current.push(
      `${current.length === 0 ? 'M' : 'L'} ${xFor(index)} ${yFor(item.value)}`,
    );
  }
  if (current.length > 0) segments.push(current.join(' '));
  return segments;
}

function niceIntegerTickStep(axisMaximum: number) {
  const target = axisMaximum / 5;
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(target, 1)));
  const candidates = [0.5, 1, 2, 5, 10]
    .map((factor) => Math.max(1, Math.round(factor * magnitude)))
    .filter((value, index, values) => values.indexOf(value) === index);
  return candidates.reduce((best, candidate) =>
    Math.abs(candidate - target) < Math.abs(best - target) ? candidate : best,
  );
}

function displayRowLabel(row: NationalityTrendRow) {
  if (!row.japaneseReference || row.label.includes('参考値')) return row.label;
  return `${row.label}（参考値）`;
}

export function NationalityTrend({
  selectedMetric,
  years,
  rows,
  selectedEntityId,
  caveat,
  warningLabels,
  refusalLabels,
  onMetricChange,
  onEntityChange,
}: NationalityTrendProps) {
  const japaneseReference = rows.find((row) => row.japaneseReference) ?? null;
  const comparisonRows = rows.filter((row) => !row.japaneseReference);
  const selectedRow =
    comparisonRows.find((row) => row.entityId === selectedEntityId) ??
    comparisonRows[0] ??
    null;
  const clusteredRows = orderRowsByHierarchicalClustering(rows, years);
  const allValues = rows.flatMap((row) =>
    row.values.flatMap((value) =>
      value.value !== null && Number.isFinite(value.value) ? [value.value] : [],
    ),
  );
  const minimum = allValues.length > 0 ? Math.min(...allValues) : 0;
  const maximum = allValues.length > 0 ? Math.max(...allValues) : 0;
  const selectedValues = selectedRow
    ? years.map(
        (year) =>
          valueForYear(selectedRow, year) ?? {
            year,
            value: null,
            displayValue: null,
            numerator: null,
            denominator: null,
            calculationStatus: 'refused' as const,
            warningCodes: [],
          },
      )
    : [];
  const referenceValues = japaneseReference
    ? years.map(
        (year) =>
          valueForYear(japaneseReference, year) ?? {
            year,
            value: null,
            displayValue: null,
            numerator: null,
            denominator: null,
            calculationStatus: 'refused' as const,
            warningCodes: [],
          },
      )
    : [];
  const selectedWarningCodes = [
    ...new Set(selectedValues.flatMap((item) => item.warningCodes)),
  ].sort();
  const referenceWarningCodes = [
    ...new Set(referenceValues.flatMap((item) => item.warningCodes)),
  ].sort();
  const selectedRefusalCodes = [
    ...new Set(
      selectedValues.flatMap((item) =>
        item.refusalCode ? [item.refusalCode] : [],
      ),
    ),
  ].sort();
  const plotMax = Math.max(1, Math.ceil(maximum));
  const tickStep = niceIntegerTickStep(plotMax);
  const axisTicks = Array.from(
    { length: Math.floor((plotMax - Number.EPSILON) / tickStep) + 1 },
    (_value, index) => index * tickStep,
  );
  const plotRange = plotMax;
  const chartWidth = 760;
  const chartHeight = 280;
  const chartPadding = { left: 48, right: 22, top: 20, bottom: 40 };
  const plotWidth = chartWidth - chartPadding.left - chartPadding.right;
  const plotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  const xFor = (index: number) =>
    years.length <= 1
      ? chartPadding.left + plotWidth / 2
      : chartPadding.left + (index / (years.length - 1)) * plotWidth;
  const yFor = (value: number) =>
    chartPadding.top + ((plotMax - value) / plotRange) * plotHeight;
  const selectedLabel = selectedRow
    ? displayRowLabel(selectedRow)
    : '比較する国籍等';
  const referenceLabel = japaneseReference
    ? displayRowLabel(japaneseReference)
    : '日本（参考値）';
  const metricLabel = metricLabels[selectedMetric];
  const heatMidpoint = minimum + (maximum - minimum) / 2;

  return (
    <section
      className="nationality-trend"
      aria-labelledby="nationality-trend-heading"
    >
      <div className="nationality-trend-heading">
        <div>
          <p className="section-kicker">2020–2024年 / 全国</p>
          <h3 id="nationality-trend-heading">国籍等別の時系列</h3>
          <p>
            日本を含む全{rows.length}
            区分を同じ表に残し、各年の人口1,000人当たりの公表統計由来の参考比率を表示します。
          </p>
        </div>
        <fieldset
          className="nationality-trend-metric"
          aria-label="時系列の分子"
        >
          <legend>分子</legend>
          <div>
            <button
              type="button"
              aria-pressed={selectedMetric === 'cases'}
              onClick={() => onMetricChange('cases')}
            >
              検挙件数
            </button>
            <button
              type="button"
              aria-pressed={selectedMetric === 'persons'}
              onClick={() => onMetricChange('persons')}
            >
              検挙人員
            </button>
          </div>
        </fieldset>
      </div>

      {caveat ? (
        <aside className="nationality-trend-caveat" aria-label="時系列の注意点">
          <strong>年ごとの差も、属性の評価には使いません</strong>
          <p>{caveat} 未算出は0として扱わず、年と区分を残して表示します。</p>
        </aside>
      ) : null}

      <div
        className="nationality-trend-heatmap-legend"
        aria-label="ヒートマップの色の凡例"
      >
        <div>
          <span>低い値 {minimum.toFixed(2)}</span>
          <i
            aria-hidden="true"
            data-colour-count="2"
            style={{
              background: `linear-gradient(90deg, rgb(${LOW_HEAT_COLOUR.join(' ')}), rgb(${HIGH_HEAT_COLOUR.join(' ')}))`,
            }}
          />
          <span>高い値 {maximum.toFixed(2)}</span>
        </div>
        <span className="nationality-trend-heatmap-midpoint">
          中間 {heatMidpoint.toFixed(2)}
        </span>
        <span className="nationality-trend-heatmap-unavailable">
          <i aria-hidden="true" /> 未算出
        </span>
        <p>色は値の大小だけを示し、良い・悪いを表す色ではありません。</p>
      </div>
      <p className="nationality-trend-cluster-note">
        行は、各区分内で標準化した5年間の変化パターンを、平均連結法・ユークリッド距離による階層クラスタリングで並べています。未算出だけの区分は末尾、年は時系列順です。
      </p>

      <div className="nationality-trend-heatmap-wrap">
        <table
          className="nationality-trend-heatmap"
          aria-label="国籍等別・人口1,000人当たりの時系列ヒートマップ"
        >
          <caption>
            青から橙の2色scaleは、選択中の分子における値の大小を示します。数値そのものは各セルで確認できます。
          </caption>
          <thead>
            <tr>
              <th scope="col">国籍等</th>
              {years.map((year) => (
                <th key={year} scope="col">
                  {year}年
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clusteredRows.map((row) => (
              <tr
                key={row.entityId}
                data-japanese-reference={
                  row.japaneseReference ? 'true' : 'false'
                }
              >
                <th scope="row">{displayRowLabel(row)}</th>
                {years.map((year) => {
                  const value = valueForYear(row, year);
                  const unavailable = !value || value.displayValue === null;
                  const warningCodes = value?.warningCodes.join(' ') ?? '';
                  return (
                    <td
                      key={year}
                      className={
                        unavailable ? 'nationality-trend-missing' : undefined
                      }
                      data-calculation-status={
                        value?.calculationStatus ?? 'refused'
                      }
                      data-refusal-code={value?.refusalCode ?? undefined}
                      data-warning-codes={warningCodes || undefined}
                      style={{
                        backgroundColor: heatColor(
                          value?.value ?? null,
                          minimum,
                          maximum,
                        ),
                        color: heatTextColor(
                          value?.value ?? null,
                          minimum,
                          maximum,
                        ),
                      }}
                      aria-label={
                        unavailable
                          ? `${displayRowLabel(row)}、${year}年: 未算出`
                          : `${displayRowLabel(row)}、${year}年: ${value.displayValue}/1,000人`
                      }
                    >
                      {unavailable ? '未算出' : value.displayValue}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="nationality-trend-detail">
        <label>
          日本と比較する国籍等
          <select
            value={selectedRow?.entityId ?? ''}
            onChange={(event) => onEntityChange(event.target.value)}
          >
            {comparisonRows.map((row) => (
              <option key={row.entityId} value={row.entityId}>
                {displayRowLabel(row)}
              </option>
            ))}
          </select>
        </label>
        <div className="nationality-trend-plot-panel">
          <div
            className="nationality-trend-line-legend"
            aria-label="折れ線の凡例"
          >
            <span className="nationality-trend-line-legend-reference">
              {referenceLabel}
            </span>
            <span className="nationality-trend-line-legend-selected">
              {selectedLabel}
            </span>
          </div>
          <p className="nationality-trend-axis-unit">
            Y軸：人口1,000人当たり（全{rows.length}区分共通、上限
            {plotMax}）
          </p>
          <div className="nationality-trend-plot-wrap">
            {/* SVG has no native text equivalent, so it needs an explicit accessible image role. */}
            <svg
              className="nationality-trend-plot"
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              role="img"
              aria-label={`${referenceLabel}と${selectedLabel}の人口1,000人当たり${metricLabel}の推移`}
              data-series-count="2"
              data-y-axis-maximum={plotMax}
            >
              {axisTicks.map((tick) => (
                <g key={tick}>
                  <line
                    x1={chartPadding.left}
                    x2={chartWidth - chartPadding.right}
                    y1={yFor(tick)}
                    y2={yFor(tick)}
                    className="nationality-trend-grid-line"
                  />
                  <text
                    x={chartPadding.left - 8}
                    y={yFor(tick) + 4}
                    textAnchor="end"
                    className="nationality-trend-axis-label"
                  >
                    {tick}
                  </text>
                </g>
              ))}
              <line
                x1={chartPadding.left}
                x2={chartPadding.left}
                y1={chartPadding.top}
                y2={chartPadding.top + plotHeight}
                className="nationality-trend-axis"
              />
              {years.map((year, index) => (
                <text
                  key={year}
                  x={xFor(index)}
                  y={chartHeight - 14}
                  textAnchor="middle"
                  className="nationality-trend-axis-label"
                >
                  {year}
                </text>
              ))}
              {japaneseReference ? (
                <g data-series-id={japaneseReference.entityId}>
                  {lineSegments(referenceValues, xFor, yFor).map(
                    (path, index) => (
                      <path
                        key={`${japaneseReference.entityId}-${index}`}
                        d={path}
                        className="nationality-trend-line nationality-trend-line-reference"
                      />
                    ),
                  )}
                  {referenceValues.map((item, index) =>
                    item.value === null ||
                    !Number.isFinite(item.value) ? null : (
                      <circle
                        key={item.year}
                        cx={xFor(index)}
                        cy={yFor(item.value)}
                        r="4"
                        className="nationality-trend-point nationality-trend-point-reference"
                      >
                        <title>{`${referenceLabel}、${item.year}年: ${item.displayValue}/1,000人`}</title>
                      </circle>
                    ),
                  )}
                </g>
              ) : null}
              {selectedRow ? (
                <g data-series-id={selectedRow.entityId}>
                  {lineSegments(selectedValues, xFor, yFor).map(
                    (path, index) => (
                      <path
                        // A gap indicates an unpublished or uncalculable value; it is not interpolated.
                        key={`${selectedRow.entityId}-${index}`}
                        d={path}
                        className="nationality-trend-line nationality-trend-line-selected"
                      />
                    ),
                  )}
                  {selectedValues.map((item, index) =>
                    item.value === null ||
                    !Number.isFinite(item.value) ? null : (
                      <circle
                        key={item.year}
                        cx={xFor(index)}
                        cy={yFor(item.value)}
                        r="4"
                        className="nationality-trend-point nationality-trend-point-selected"
                      >
                        <title>{`${selectedLabel}、${item.year}年: ${item.displayValue}/1,000人`}</title>
                      </circle>
                    ),
                  )}
                </g>
              ) : null}
            </svg>
          </div>
        </div>
        <div className="nationality-trend-detail-table-wrap">
          <table
            className="nationality-trend-detail-table"
            aria-label="日本参考値と選択した国籍等の年別分子・分母・参考比率"
          >
            <caption>
              {referenceLabel}と{selectedLabel}
              の公表値、およびこのサイトで算出した参考比率
            </caption>
            <thead>
              <tr>
                <th scope="col">年</th>
                <th scope="col">国籍等</th>
                <th scope="col">{metricLabel}</th>
                <th scope="col">分母人口</th>
                <th scope="col">人口1,000人当たり</th>
                <th scope="col">算出状態</th>
              </tr>
            </thead>
            <tbody>
              {years.flatMap((year, yearIndex) =>
                [
                  {
                    key: `${year}-reference`,
                    label: referenceLabel,
                    item: referenceValues[yearIndex],
                    reference: true,
                  },
                  {
                    key: `${year}-selected`,
                    label: selectedLabel,
                    item: selectedValues[yearIndex],
                    reference: false,
                  },
                ].map(({ key, label, item, reference }) => (
                  <tr key={key} data-japanese-reference={String(reference)}>
                    <th scope="row">{year}年</th>
                    <th scope="row">{label}</th>
                    <td>{item?.numerator?.toLocaleString('ja-JP') ?? '—'}</td>
                    <td>{item?.denominator?.toLocaleString('ja-JP') ?? '—'}</td>
                    <td>
                      {!item || item.displayValue === null
                        ? '未算出'
                        : `${item.displayValue} / 1,000人`}
                    </td>
                    <td>
                      {item?.calculationStatus === 'calculated'
                        ? '算出済み'
                        : '未算出'}
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
        <aside
          className="nationality-trend-selected-warnings"
          aria-label="比較する2区分に関する注意"
        >
          <strong>比較する2区分に関する注意</strong>
          <div>
            <h4>{referenceLabel}</h4>
            {referenceWarningCodes.length > 0 ? (
              <ul>
                {referenceWarningCodes.map((code) => (
                  <li key={code} title={`内部コード: ${code}`}>
                    {warningLabels?.[code] ?? code}
                  </li>
                ))}
              </ul>
            ) : (
              <p>追加の注意はありません。</p>
            )}
          </div>
          <div>
            <h4>{selectedLabel}</h4>
            {selectedWarningCodes.length > 0 ||
            selectedRefusalCodes.length > 0 ? (
              <ul>
                {selectedWarningCodes.map((code) => (
                  <li key={`warning-${code}`} title={`内部コード: ${code}`}>
                    {warningLabels?.[code] ?? code}
                  </li>
                ))}
                {selectedRefusalCodes.map((code) => (
                  <li key={`refusal-${code}`} title={`内部コード: ${code}`}>
                    未算出理由：{refusalLabels?.[code] ?? code}
                  </li>
                ))}
              </ul>
            ) : (
              <p>追加の注意はありません。</p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}
