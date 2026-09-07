import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { hydrateRoot } from 'react-dom/client';
import { renderToString } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import {
  NationalityTrend,
  orderRowsByHierarchicalClustering,
  type NationalityTrendProps,
  type NationalityTrendRow,
} from '@/components/nationality-trend';

const props: NationalityTrendProps = {
  selectedMetric: 'cases',
  years: [2020, 2021, 2022],
  selectedEntityId: 'vietnam',
  onMetricChange: vi.fn(),
  onEntityChange: vi.fn(),
  rows: [
    {
      entityId: 'japan',
      label: '日本',
      japaneseReference: true,
      values: [
        {
          year: 2020,
          value: 1.2,
          displayValue: '1.20',
          numerator: 120,
          denominator: 100_000,
          calculationStatus: 'calculated',
          warningCodes: ['japanese_numerator_derived_by_residual_subtraction'],
        },
        {
          year: 2021,
          value: 1.1,
          displayValue: '1.10',
          numerator: 110,
          denominator: 100_000,
          calculationStatus: 'calculated',
          warningCodes: [],
        },
        {
          year: 2022,
          value: 1,
          displayValue: '1.00',
          numerator: 100,
          denominator: 100_000,
          calculationStatus: 'calculated',
          warningCodes: [],
        },
      ],
    },
    {
      entityId: 'vietnam',
      label: 'ベトナム',
      japaneseReference: false,
      values: [
        {
          year: 2020,
          value: 7,
          displayValue: '7.00',
          numerator: 70,
          denominator: 10_000,
          calculationStatus: 'calculated',
          warningCodes: [],
        },
        {
          year: 2021,
          value: null,
          displayValue: null,
          numerator: null,
          denominator: null,
          calculationStatus: 'refused',
          refusalCode: 'crosswalk_not_exact',
          warningCodes: [],
        },
        {
          year: 2022,
          value: 2,
          displayValue: '2.00',
          numerator: 20,
          denominator: 10_000,
          calculationStatus: 'calculated',
          warningCodes: [],
        },
      ],
    },
  ],
};

describe('NationalityTrend', () => {
  it('orders calculable rows by hierarchical clustering and leaves unavailable rows last', () => {
    const row = (
      entityId: string,
      numericValues: Array<number | null>,
    ): NationalityTrendRow => ({
      entityId,
      label: entityId,
      japaneseReference: false,
      values: numericValues.map((value, index) => ({
        year: 2020 + index,
        value,
        displayValue: value === null ? null : value.toFixed(2),
        numerator: value === null ? null : value * 100,
        denominator: value === null ? null : 100_000,
        calculationStatus: value === null ? 'refused' : 'calculated',
        warningCodes: [],
      })),
    });
    const ordered = orderRowsByHierarchicalClustering(
      [
        row('rising-a', [1, 2, 3]),
        row('falling', [3, 2, 1]),
        row('rising-b', [1.1, 2.1, 3.2]),
        row('unavailable', [null, null, null]),
      ],
      [2020, 2021, 2022],
    );

    expect(ordered.map((item) => item.entityId)).toEqual([
      'rising-a',
      'rising-b',
      'falling',
      'unavailable',
    ]);
  });

  it('shows every provided category and year with exact values, including missing values', () => {
    render(<NationalityTrend {...props} />);

    expect(
      screen.getByRole('heading', { name: '国籍等別の時系列' }),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: '検挙件数' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(
      screen.getByRole('button', { name: '検挙人員' }),
    ).toBeInTheDocument();

    const table = screen.getByRole('table', {
      name: '国籍等別・人口1,000人当たりの時系列ヒートマップ',
    });
    expect(
      within(table).getByRole('columnheader', { name: '2020年' }),
    ).toBeVisible();
    expect(
      within(table).getByRole('rowheader', { name: '日本（参考値）' }),
    ).toBeVisible();
    expect(within(table).getByText('7.00')).toBeVisible();
    expect(within(table).getByText('未算出')).toHaveAttribute(
      'data-calculation-status',
      'refused',
    );
    expect(within(table).getByText('未算出').closest('td')).toHaveClass(
      'nationality-trend-missing',
    );
    const detailTable = screen.getByRole('table', {
      name: '選択した国籍等の年別分子・分母・参考比率',
    });
    expect(
      within(detailTable).getByRole('row', { name: /2020年/ }),
    ).toHaveTextContent(/120.*100,000.*1\.20/);
  });

  it('notifies its parent when the metric or selected category changes', () => {
    const onMetricChange = vi.fn();
    const onEntityChange = vi.fn();
    render(
      <NationalityTrend
        {...props}
        onMetricChange={onMetricChange}
        onEntityChange={onEntityChange}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '検挙人員' }));
    expect(onMetricChange).toHaveBeenCalledWith('persons');

    fireEvent.change(screen.getByRole('combobox', { name: '表示する国籍等' }), {
      target: { value: 'vietnam' },
    });
    expect(onEntityChange).toHaveBeenCalledWith('vietnam');
  });

  it('explains the two-colour heatmap scale without assigning value judgments', () => {
    render(<NationalityTrend {...props} />);

    const legend = screen.getByLabelText('ヒートマップの色の凡例');
    expect(legend).toHaveTextContent('低い値');
    expect(legend).toHaveTextContent('高い値');
    expect(legend).toHaveTextContent('未算出');
    expect(legend).toHaveTextContent('良い・悪いを表す色ではありません');
    expect(legend.querySelector('[data-colour-count="2"]')).toBeVisible();
    expect(
      screen.getByText(/行は.*階層クラスタリング.*平均連結/),
    ).toBeVisible();
  });

  it('always compares the selected category with the Japanese reference', () => {
    render(<NationalityTrend {...props} />);

    const chart = screen.getByRole('img', {
      name: '日本（参考値）とベトナムの人口1,000人当たり検挙件数の推移',
    });
    expect(chart).toHaveAttribute('data-series-count', '2');
    expect(chart.querySelectorAll('[data-series-id]')).toHaveLength(2);
    expect(
      chart.querySelector('[data-series-id="japan"]'),
    ).toBeInTheDocument();
    expect(
      chart.querySelector('[data-series-id="vietnam"]'),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('折れ線の凡例'),
    ).toHaveTextContent('日本（参考値）');
    expect(screen.getByLabelText('折れ線の凡例')).toHaveTextContent(
      'ベトナム',
    );
    expect(
      screen.getByRole('combobox', { name: '日本と比較する国籍等' }),
    ).not.toHaveTextContent('日本（参考値）');
    expect(chart.querySelectorAll('path.nationality-trend-line')).toHaveLength(
      3,
    );
    expect(chart).toHaveTextContent('2020');
    expect(chart).toHaveTextContent('2022');

    const detailTable = screen.getByRole('table', {
      name: '日本参考値と選択した国籍等の年別分子・分母・参考比率',
    });
    expect(
      within(detailTable).getAllByRole('row', { name: /2020年/ }),
    ).toHaveLength(2);
    expect(detailTable).toHaveTextContent('日本（参考値）');
    expect(detailTable).toHaveTextContent('ベトナム');
  });

  it('keeps the Japanese reference even when Japan is passed as the selection', () => {
    render(<NationalityTrend {...props} selectedEntityId="japan" />);

    const chart = screen.getByRole('img', {
      name: '日本（参考値）とベトナムの人口1,000人当たり検挙件数の推移',
    });
    expect(chart.querySelectorAll('[data-series-id]')).toHaveLength(2);
    expect(chart).toHaveAttribute('data-series-count', '2');
  });

  it('shows the selected series warnings in plain language', () => {
    const warningProps = {
      ...props,
      warningLabels: {
        japanese_numerator_derived_by_residual_subtraction:
          '日本の犯罪件数・人員は差し引きによる参考値',
      },
    };

    render(<NationalityTrend {...warningProps} selectedEntityId="japan" />);

    expect(
      screen.getByText('日本の犯罪件数・人員は差し引きによる参考値'),
    ).toBeVisible();
  });

  it('shows why the selected category could not be calculated', () => {
    render(
      <NationalityTrend
        {...props}
        refusalLabels={{
          crosswalk_not_exact:
            '犯罪統計と人口統計の国籍区分が一致しない',
        }}
      />,
    );

    expect(
      screen.getByText('犯罪統計と人口統計の国籍区分が一致しない'),
    ).toBeVisible();
  });

  it('server-renders SVG titles without hydration warnings', async () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined);
    const container = document.createElement('div');
    container.innerHTML = renderToString(<NationalityTrend {...props} />);
    document.body.appendChild(container);

    const root = hydrateRoot(container, <NationalityTrend {...props} />);
    await act(async () => undefined);

    expect(
      consoleError.mock.calls.some((call) =>
        call.some(
          (part) =>
            typeof part === 'string' &&
            part.includes('children prop of <title> tags'),
        ),
      ),
    ).toBe(false);
    await act(async () => root.unmount());
    container.remove();
    consoleError.mockRestore();
  });
});
