'use client';

import { useMemo, useState } from 'react';
import { ExternalLink, MapPinned } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import {
  formatDashboardValue,
  type RegionalDatum,
  type ValueMode,
} from '@/lib/dashboard';
import {
  JAPAN_PREFECTURE_BORDER_PATH,
  JAPAN_PREFECTURE_PATHS,
} from '@/lib/japan-map-paths.generated';

const CHOROPLETH_COLORS = [
  '#d7e9e4',
  '#add3ca',
  '#76b5a9',
  '#3b887f',
  '#155b59',
] as const;

export function choroplethColor(
  value: number,
  minimum: number,
  maximum: number,
): string {
  if (maximum === minimum) return CHOROPLETH_COLORS[2];
  const normalized = (value - minimum) / (maximum - minimum);
  const index = Math.min(
    CHOROPLETH_COLORS.length - 1,
    Math.floor(normalized * CHOROPLETH_COLORS.length),
  );
  return CHOROPLETH_COLORS[index];
}

export function PrefectureMap({
  prefectures,
  mode,
  unitLabel,
  ratioUnitLabel,
  rawCountLabel,
  denominatorLabel,
  ratioDetailLabel,
}: {
  prefectures: RegionalDatum[];
  mode: ValueMode;
  unitLabel: string;
  ratioUnitLabel: string;
  rawCountLabel: string;
  denominatorLabel: string;
  ratioDetailLabel: string;
}) {
  const byId = useMemo(
    () => new Map(prefectures.map((datum) => [datum.id, datum])),
    [prefectures],
  );
  const [selectedId, setSelectedId] = useState('jp-prefecture:13');
  const selected = byId.get(selectedId) ?? prefectures[0];
  if (!selected) throw new Error('The prefecture map has no observations.');

  const values = prefectures.map((datum) => datum.value);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);

  return (
    <section
      className="prefecture-map-section"
      aria-labelledby="prefecture-map-heading"
    >
      <div className="section-heading-row">
        <div>
          <p className="section-kicker">地図で比較</p>
          <h2 id="prefecture-map-heading">47都道府県の地図</h2>
        </div>
        <Badge variant="secondary">{unitLabel}</Badge>
      </div>

      <div className="prefecture-map-card">
        <div className="map-canvas-wrap">
          <svg
            className="prefecture-map-svg"
            data-testid="prefecture-map"
            viewBox="0 0 2000 2000"
            aria-labelledby="prefecture-map-title prefecture-map-description"
          >
            <title id="prefecture-map-title">
              47都道府県の統計値を色分けした日本地図
            </title>
            <desc id="prefecture-map-description">
              薄い色から濃い色になるほど、選択中の表示値が大きいことを示します。
            </desc>
            <g>
              {JAPAN_PREFECTURE_PATHS.map((path) => {
                const datum = byId.get(`jp-prefecture:${path.code}`);
                if (!datum) {
                  throw new Error(
                    `Map datum is missing for prefecture code ${path.code}.`,
                  );
                }
                const label = `${datum.name}: ${formatDashboardValue(datum.value, mode)} ${unitLabel}`;
                return (
                  <path
                    key={path.code}
                    d={path.d}
                    data-prefecture-code={path.code}
                    data-prefecture-name={path.name}
                    fill={choroplethColor(datum.value, minimum, maximum)}
                    aria-label={label}
                    tabIndex={0}
                    onFocus={() => setSelectedId(datum.id)}
                    onPointerEnter={() => setSelectedId(datum.id)}
                  >
                    <title>{label}</title>
                  </path>
                );
              })}
            </g>
            <path
              className="prefecture-map-borders"
              d={JAPAN_PREFECTURE_BORDER_PATH}
              aria-hidden="true"
            />
          </svg>
          <ol className="accessible-ranking">
            {prefectures.map((datum) => (
              <li key={datum.id}>
                {datum.name}: {formatDashboardValue(datum.value, mode)}{' '}
                {unitLabel}
              </li>
            ))}
          </ol>
        </div>

        <aside className="map-readout">
          <MapPinned aria-hidden="true" />
          <p>地図に触れるか、キーボードで選択</p>
          <div data-testid="map-selected-prefecture">
            <h3>{selected.name}</h3>
            <strong>
              {formatDashboardValue(selected.value, mode)}{' '}
              <span>{unitLabel}</span>
            </strong>
            <dl>
              <div>
                <dt>{rawCountLabel}</dt>
                <dd>{selected.rawCount.toLocaleString('ja-JP')}</dd>
              </div>
              <div>
                <dt>{denominatorLabel}</dt>
                <dd>{selected.denominatorValue.toLocaleString('ja-JP')}</dd>
              </div>
              <div>
                <dt>{ratioDetailLabel}</dt>
                <dd>
                  {formatDashboardValue(selected.referenceRatio, 'ratio')}{' '}
                  {ratioUnitLabel}
                </dd>
              </div>
            </dl>
          </div>
          <div className="map-legend" aria-label="色の凡例">
            <span>{formatDashboardValue(minimum, mode)}</span>
            <div>
              {CHOROPLETH_COLORS.map((color) => (
                <i key={color} style={{ backgroundColor: color }} />
              ))}
            </div>
            <span>{formatDashboardValue(maximum, mode)}</span>
          </div>
          <p className="map-geometry-note">
            見やすさのために形を変えた地図です。実際の地形・面積・距離を表すものではありません。
          </p>
          <a
            href="https://github.com/lalamalink/japan-map-svg"
            target="_blank"
            rel="noreferrer"
          >
            地図素材：lalamalink（CC0） <ExternalLink aria-hidden="true" />
          </a>
        </aside>
      </div>
    </section>
  );
}
