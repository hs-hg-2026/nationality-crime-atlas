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

function heatColor(value: number | null, maximum: number) {
  if (value === null || !Number.isFinite(value)) return undefined;
  const intensity = maximum > 0 ? Math.min(Math.max(value / maximum, 0), 1) : 0;
  return `hsl(204 58% ${96 - intensity * 42}%)`;
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

function displayRowLabel(row: NationalityTrendRow) {
  return row.japaneseReference ? `${row.label}（参考値）` : row.label;
}

export function NationalityTrend({
  selectedMetric,
  years,
  rows,
  selectedEntityId,
  onMetricChange,
  onEntityChange,
}: NationalityTrendProps) {
  const selectedRow =
    rows.find((row) => row.entityId === selectedEntityId) ?? rows[0] ?? null;
  const allValues = rows.flatMap((row) =>
    row.values.flatMap((value) =>
      value.value !== null && Number.isFinite(value.value) ? [value.value] : [],
    ),
  );
  const maximum = Math.max(...allValues, 0);
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
  const plottedValues = selectedValues.flatMap((item) =>
    item.value !== null && Number.isFinite(item.value) ? [item.value] : [],
  );
  const plotMin = Math.min(...plottedValues, 0);
  const plotMax = Math.max(...plottedValues, 1);
  const plotRange = plotMax - plotMin || 1;
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
    : '選択した国籍等';
  const metricLabel = metricLabels[selectedMetric];

  return (
    <section
      className="nationality-trend"
      aria-labelledby="nationality-trend-heading"
    >
      <div className="nationality-trend-heading">
        <div>
          <p className="section-kicker">2020–2024 NATIONAL TREND</p>
          <h3 id="nationality-trend-heading">国籍等別の時系列</h3>
          <p>
            全区分を同じ表に残し、各年の人口1,000人当たりの公表統計由来の参考比率を表示します。
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

      <div className="nationality-trend-heatmap-wrap">
        <table
          className="nationality-trend-heatmap"
          aria-label="国籍等別・人口1,000人当たりの時系列ヒートマップ"
        >
          <caption>
            色は選択中の分子における値の大きさを示します。数値そのものは各セルで確認できます。
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
            {rows.map((row) => (
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
          表示する国籍等
          <select
            value={selectedRow?.entityId ?? ''}
            onChange={(event) => onEntityChange(event.target.value)}
          >
            {rows.map((row) => (
              <option key={row.entityId} value={row.entityId}>
                {displayRowLabel(row)}
              </option>
            ))}
          </select>
        </label>
        <div className="nationality-trend-plot-wrap">
          {/* SVG has no native text equivalent, so it needs an explicit accessible image role. */}
          <svg
            className="nationality-trend-plot"
            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            role="img"
            aria-label={`${selectedLabel}の人口1,000人当たり${metricLabel}の推移`}
            data-series-count="1"
          >
            <line
              x1={chartPadding.left}
              x2={chartWidth - chartPadding.right}
              y1={chartPadding.top + plotHeight}
              y2={chartPadding.top + plotHeight}
              className="nationality-trend-axis"
            />
            <line
              x1={chartPadding.left}
              x2={chartPadding.left}
              y1={chartPadding.top}
              y2={chartPadding.top + plotHeight}
              className="nationality-trend-axis"
            />
            <text
              x={6}
              y={chartPadding.top + 4}
              className="nationality-trend-axis-label"
            >
              {plotMax.toFixed(2)}
            </text>
            <text
              x={6}
              y={chartPadding.top + plotHeight}
              className="nationality-trend-axis-label"
            >
              {plotMin.toFixed(2)}
            </text>
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
            {lineSegments(selectedValues, xFor, yFor).map((path, index) => (
              <path
                // A gap indicates an unpublished or uncalculable value; it is not interpolated.
                key={`${selectedRow?.entityId ?? 'empty'}-${index}`}
                d={path}
                className="nationality-trend-line"
              />
            ))}
            {selectedValues.map((item, index) =>
              item.value === null || !Number.isFinite(item.value) ? null : (
                <circle
                  key={item.year}
                  cx={xFor(index)}
                  cy={yFor(item.value)}
                  r="4"
                  className="nationality-trend-point"
                >
                  <title>
                    {item.year}年: {item.displayValue}/1,000人
                  </title>
                </circle>
              ),
            )}
          </svg>
        </div>
      </div>
    </section>
  );
}
