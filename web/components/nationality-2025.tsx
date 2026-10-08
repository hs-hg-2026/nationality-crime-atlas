'use client';

/* oxlint-disable jsx-a11y/prefer-tag-over-role -- Composed chart segments need an accessible image role, not an external bitmap. */

function VisitingDefinition() {
  return (
    <p>
      「来日外国人」は、永住権を有する者等の定着居住者、在日米軍関係者、在留資格不明の者を除いた外国人を指す警察統計上の区分です。旅行者だけを指す言葉ではなく、在留外国人全体とも一致しません。
      <a
        href="https://www.npa.go.jp/toukei/keiji35/new_hanzai07.htm"
        target="_blank"
        rel="noreferrer"
      >
        警察庁の用語の解説（4）
      </a>
    </p>
  );
}

import { useState } from 'react';
const sourceTitles: Record<string, string> = {
  S21: '刑法犯検挙状況（全国総数・外国人区分）',
  S22: '国籍等別の刑法犯検挙状況（掲載区分限定）',
  S19_2025: '在留外国人統計：国籍・地域別の在留外国人数',
  S27: '国勢調査：日本人・外国人の別の人口（原数値）',
  S30: '組織犯罪の情勢：来日外国人の国籍等別・包括罪種等別検挙状況',
};
import type {
  Nationality2025Data,
  SupplementMetric,
  SupplementScope,
  SourceComponent,
} from '@/lib/nationality-2025.mjs';

const format = (value: number | null, decimals = 0) =>
  value === null
    ? '未算出'
    : value.toLocaleString('ja-JP', {
        maximumFractionDigits: decimals,
        minimumFractionDigits: decimals,
      });
const colors = [
  '#9f1239',
  '#c2410c',
  '#1d4ed8',
  '#7c3aed',
  '#0f766e',
  '#64748b',
];
const metricLabel = (metric: SupplementMetric) =>
  metric === 'cleared_cases' ? '検挙件数' : '検挙人員';

function Sources({ data, ids }: { data: Nationality2025Data; ids: string[] }) {
  return (
    <details>
      <summary>出典と固定したデータ版</summary>
      <ul>
        {ids.map((id) => (
          <li key={id}>
            <a
              href={data.sources[id].landing_url}
              target="_blank"
              rel="noreferrer"
            >
              {id}：{sourceTitles[id]}
            </a>
            （表{data.sources[id].source_table}）{' '}
            <a
              href={data.sources[id].download_url}
              target="_blank"
              rel="noreferrer"
            >
              原本
            </a>
            <br />
            <small>原本 SHA-256：{data.sources[id].sha256}</small>
          </li>
        ))}
      </ul>
    </details>
  );
}
function coordinates(components: SourceComponent[]) {
  return components
    .map(
      (c) =>
        `${c.source_id} 表${c.source_table} ${c.sheet} 行${c.row}・列${c.column}：${format(c.value)}${c.role === 'subtrahend' ? '（差し引く）' : ''}`,
    )
    .join(' / ');
}

export function Nationality2025Comparison({
  data,
}: {
  data: Nationality2025Data;
}) {
  const [metric, setMetric] = useState<SupplementMetric>('cleared_cases');
  const [scope, setScope] = useState<SupplementScope>('all_foreign');
  const [ascending, setAscending] = useState(false);
  const rows = data.comparison
    .filter((r) => r.metric === metric && r.scope === scope)
    .sort((a, b) =>
      a.value === null
        ? b.value === null
          ? a.label.localeCompare(b.label, 'ja')
          : 1
        : b.value === null
          ? -1
          : (ascending ? a.value - b.value : b.value - a.value) ||
            a.label.localeCompare(b.label, 'ja'),
    );
  const maximum = Math.max(1, ...rows.map((r) => r.value ?? 0));
  const unit = metric === 'cleared_cases' ? '件' : '人';
  return (
    <section
      id="nationality-2025"
      className="nationality-section"
      aria-labelledby="nationality-2025-heading"
    >
      <p className="section-kicker">
        国籍等別の全国値 / 2025年・掲載範囲が限定された資料
      </p>
      <h2 id="nationality-2025-heading">
        日本を含む国籍等別の全国比較（2025年）
      </h2>
      <p className="intro-copy">
        2024年版の26区分を残し、新掲載の4区分を加えた30区分を表示します。未掲載はゼロではありません。人口1,000人当たりの数値は公表統計由来の参考比率で、犯罪を行う確率ではありません。
      </p>
      <div className="definition-notice">
        <p>
          公表範囲の制限：件数は2016～2025年のいずれかの年に300件以上、人員は同期間のいずれかの年に150人以上となった国籍等のみ掲載されています。低い側が未掲載となり得るため、この図は全国籍の順位を示すものではありません。
        </p>
      </div>
      <div className="supplement-controls">
        <label>
          2025年の分子
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as SupplementMetric)}
          >
            <option value="cleared_cases">刑法犯の検挙件数</option>
            <option value="cleared_persons">刑法犯の検挙人員</option>
          </select>
        </label>
        <label>
          2025年の外国人対象範囲
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as SupplementScope)}
          >
            <option value="all_foreign">外国人全体（日本は残差参考値）</option>
            <option value="visiting_foreign">来日外国人（日本は対象外）</option>
          </select>
        </label>
        <label>
          参考比率の並び順
          <select
            value={ascending ? 'ascending' : 'descending'}
            onChange={(e) => setAscending(e.target.value === 'ascending')}
          >
            <option value="descending">高い値から（未算出も表示）</option>
            <option value="ascending">低い値から（未算出も表示）</option>
          </select>
        </label>
      </div>
      <p>
        バーの長さ：人口1,000人当たりの{metricLabel(metric)}（{unit}
        ）。橙色＝日本の残差参考値、青色＝外国人区分。未算出にはバーを描きません。
      </p>
      <div className="supplement-bars">
        {rows.map((row) => (
          <div key={row.label} className="supplement-bar-row">
            <span>
              {row.label}
              {row.japanese_reference ? '（参考値）' : ''}
            </span>
            <div className="supplement-bar-track">
              {row.value !== null && (
                <span
                  style={{
                    width: `${(row.value / maximum) * 100}%`,
                    background: row.japanese_reference ? '#c2410c' : '#2563eb',
                  }}
                />
              )}
            </div>
            <strong>{format(row.value, 2)}</strong>
          </div>
        ))}
      </div>
      <div className="definition-notice">
        <ul>
          {[...new Set(rows.flatMap((row) => row.warnings))].map((w) => (
            <li key={w}>{data.definitions.warning_labels[w]}</li>
          ))}
        </ul>
        {scope === 'visiting_foreign' && (
          <p>{data.definitions.reason_labels.japan_not_in_visiting_scope}</p>
        )}
        {scope === 'visiting_foreign' && <VisitingDefinition />}
      </div>
      <div className="supplement-table-wrap">
        <table aria-label="2025年の国籍等別公表値と参考比率">
          <thead>
            <tr>
              <th>国籍等</th>
              <th>
                {metricLabel(metric)}（{unit}）
              </th>
              <th>人口（人）</th>
              <th>人口1,000人当たり（{unit}）</th>
              <th>注意・未算出理由／出典の位置</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">
                  {row.label}
                  {row.japanese_reference ? '（残差参考値）' : ''}
                </th>
                <td>{format(row.numerator)}</td>
                <td>{format(row.denominator)}</td>
                <td>{format(row.value, 2)}</td>
                <td>
                  {row.reason && (
                    <p>{data.definitions.reason_labels[row.reason]}</p>
                  )}
                  <details>
                    <summary>計算と出典の詳細</summary>
                    <p>
                      分子：
                      {coordinates(row.numerator_components) || '掲載なし'}
                    </p>
                    <p>
                      分母：
                      {coordinates(row.denominator_components) || '対応なし'}
                    </p>
                    <ul>
                      {row.warnings.map((w) => (
                        <li key={w}>{data.definitions.warning_labels[w]}</li>
                      ))}
                    </ul>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Sources data={data} ids={['S21', 'S22', 'S19_2025', 'S27']} />
    </section>
  );
}

function heatColor(share: number) {
  const low = [219, 238, 246],
    high = [194, 65, 12];
  return `rgb(${low.map((c, i) => Math.round(c + ((high[i] - c) * share) / 100)).join(' ')})`;
}
export function VisitingOffense2025({ data }: { data: Nationality2025Data }) {
  const [metric, setMetric] = useState<SupplementMetric>('cleared_cases');
  const [display, setDisplay] = useState('heatmap');
  const [order, setOrder] = useState('cluster');
  const labels =
    order === 'cluster'
      ? data.cluster_orders[metric]
      : ['ベトナム', '中国', 'タイ', 'ブラジル', 'カンボジア'];
  const entities = labels.map((label) =>
    data.composition.find((r) => r.label === label && r.metric === metric)!,
  );
  const aggregate = data.composition.find(
    (r) => r.label === '来日外国人総数' && r.metric === metric,
  )!;
  return (
    <section
      id="offense"
      className="offense-section"
      aria-labelledby="offense-2025-heading"
    >
      <p className="section-kicker">2025年の追加資料 / 来日外国人のみ</p>
      <h2 id="offense-2025-heading">2025年・来日外国人5国籍の犯罪種類の構成</h2>
      <VisitingDefinition />
      <p>
        警察庁の図表3-13に掲載された5国籍の刑法犯内訳です。外国人全体の構成ではありません。2024年版の26区分とは対象範囲・掲載範囲が異なるため、年の差を直接比較しません。
      </p>
      <p className="definition-notice">
        日本：未算出。
        {data.definitions.reason_labels.japan_not_in_visiting_scope}{' '}
        その他の国籍も、この図表に内訳が掲載されていないため推計しません。中国の区分は台湾・香港等を除きます。
      </p>
      <div className="supplement-controls">
        <label>
          2025年犯罪構成の分子
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as SupplementMetric)}
          >
            <option value="cleared_cases">検挙件数</option>
            <option value="cleared_persons">検挙人員</option>
          </select>
        </label>
        <label>
          2025年犯罪構成の表示形式
          <select value={display} onChange={(e) => setDisplay(e.target.value)}>
            <option value="heatmap">ヒートマップ</option>
            <option value="stacked">100%積み上げ棒グラフ</option>
          </select>
        </label>
        <label>
          2025年犯罪構成の並び順
          <select value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="cluster">階層クラスタリング</option>
            <option value="source">公表資料の順</option>
          </select>
        </label>
      </div>
      <p>
        各国籍等の{metricLabel(metric)}
        を100%とする構成比です。人口当たりの比率ではありません。階層クラスタリングはJensen–Shannon距離・平均連結法で、5国籍だけを並べ替えます。来日外国人総数は別枠です。
      </p>
      <p>
        公表された包括罪種の6区分を使います。「凶悪犯」などの公式分類は、一件ごとの被害の大きさや法定刑、全犯罪を重犯罪／軽犯罪に二分した評価ではありません。
      </p>
      {display === 'heatmap' ? (
        <>
          <p>
            色の意味：青（0%）→橙（100%）。同じ尺度で各セルの構成比を示します。濃さは人数や危険度ではありません。
          </p>
          <div className="supplement-heat-legend" aria-hidden="true" />
          <div className="supplement-table-wrap">
            <table aria-label="2025年来日外国人の犯罪構成ヒートマップ">
              <thead>
                <tr>
                  <th>国籍等</th>
                  {data.definitions.categories.map((c) => (
                    <th key={c.id}>{c.label}</th>
                  ))}
                  <th>総数</th>
                </tr>
              </thead>
              <tbody>
                {[...entities, aggregate].map((row) => (
                  <tr key={row.label}>
                    <th scope="row">{row.label}</th>
                    {data.definitions.categories.map((c) => {
                      const cell = row.cells.find(
                        (cell) => cell.category_id === c.id,
                      )!;
                      return (
                        <td
                          key={c.id}
                          style={{
                            background: heatColor(cell.share!),
                            color: cell.share! >= 68 ? '#fff' : '#14232b',
                          }}
                          title={coordinates([cell.source!])}
                        >
                          {format(cell.share, 1)}%<br />
                          <small>{format(cell.count)}</small>
                        </td>
                      );
                    })}
                    <td>{format(row.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <>
          <ul className="supplement-category-legend">
            {data.definitions.categories.map((c, i) => (
              <li key={c.id}>
                <span style={{ background: colors[i] }} />
                {c.label}
              </li>
            ))}
          </ul>
          {[...entities, aggregate].map((row) => (
            <div className="supplement-stack-row" key={row.label}>
              <strong>
                {row.label}（{format(row.total)}）
              </strong>
              <div
                className="supplement-stack"
                role="img"
                aria-label={`${row.label}の犯罪構成：${row.cells.map((c) => `${data.definitions.categories.find((category) => category.id === c.category_id)!.label} ${format(c.share, 1)}%`).join('、')}`}
              >
                {data.definitions.categories.map((c, i) => {
                  const cell = row.cells.find(
                    (cell) => cell.category_id === c.id,
                  )!;
                  return (
                    <span
                      key={c.id}
                      style={{ width: `${cell.share}%`, background: colors[i] }}
                      title={`${c.label} ${format(cell.share, 1)}% / ${format(cell.count)}`}
                    >
                      {cell.share! >= 8 ? `${format(cell.share, 1)}%` : ''}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </>
      )}
      <details>
        <summary>公表値と出典の位置をすべて確認</summary>
        <div className="supplement-table-wrap">
          <table aria-label="2025年犯罪構成の実数と出典">
            <thead>
              <tr>
                <th>国籍等</th>
                <th>種類</th>
                <th>{metricLabel(metric)}</th>
                <th>構成比</th>
                <th>出典</th>
              </tr>
            </thead>
            <tbody>
              {[...entities, aggregate].flatMap((row) =>
                row.cells.map((cell) => (
                  <tr key={`${row.label}/${cell.category_id}`}>
                    <th scope="row">{row.label}</th>
                    <td>
                      {
                        data.definitions.categories.find(
                          (c) => c.id === cell.category_id,
                        )!.label
                      }
                    </td>
                    <td>{format(cell.count)}</td>
                    <td>{format(cell.share, 1)}%</td>
                    <td>{coordinates([cell.source!])}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </details>
      <Sources data={data} ids={['S30']} />
    </section>
  );
}
