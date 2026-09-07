import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import {
  NationalityTrend,
  type NationalityTrendProps,
} from '@/components/nationality-trend';

const props: NationalityTrendProps = {
  selectedMetric: 'cases',
  years: [2020, 2021, 2022],
  selectedEntityId: 'japan',
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

  it('draws only the selected category as an accessible line chart', () => {
    render(<NationalityTrend {...props} />);

    const chart = screen.getByRole('img', {
      name: '日本（参考値）の人口1,000人当たり検挙件数の推移',
    });
    expect(chart.querySelectorAll('path.nationality-trend-line')).toHaveLength(
      1,
    );
    expect(chart).toHaveTextContent('2020');
    expect(chart).toHaveTextContent('2022');
  });
});
