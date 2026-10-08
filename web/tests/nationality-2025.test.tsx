import { readFileSync } from 'node:fs';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { parseNationality2025 } from '@/lib/nationality-2025.mjs';
import { Nationality2025Comparison, VisitingOffense2025 } from '@/components/nationality-2025';

function product() {
  const pointer = JSON.parse(readFileSync('../output/nationality_2025/latest.json', 'utf8'));
  return JSON.parse(readFileSync(`../${pointer.product_path}`, 'utf8'));
}

describe('2025 supplement', () => {
  it('preserves all rows and rejects a missing value silently becoming zero', () => {
    const data = product();
    expect(parseNationality2025(data).comparison).toHaveLength(120);
    const refused = data.comparison.find((row: {status:string}) => row.status === 'refused');
    refused.value = 0;
    expect(() => parseNationality2025(data)).toThrow();
  });

  it('rejects altered rates, duplicated rows, erased warnings and composition totals', () => {
    for (const mutation of ['rate','duplicate','warnings','total','scope','cluster']) {
      const data = product();
      if (mutation === 'rate') data.comparison[0].value += 1;
      if (mutation === 'duplicate') data.comparison[1] = data.comparison[0];
      if (mutation === 'warnings') data.comparison[0].warnings = [];
      if (mutation === 'total') data.composition[0].total += 1;
      if (mutation === 'scope') data.composition[0].scope = 'all_foreign';
      if (mutation === 'cluster') data.cluster_orders.cleared_cases[0] = '日本';
      expect(() => parseNationality2025(data)).toThrow();
    }
  });

  it('shows cases first, Japanese reference, all unlisted rows and population columns', () => {
    render(<Nationality2025Comparison data={parseNationality2025(product())} />);
    expect(screen.getByText(/2016～2025年/)).toBeVisible();
    const table = screen.getByRole('table', {name: '2025年の国籍等別公表値と参考比率'});
    expect(within(table).getAllByRole('row')).toHaveLength(31);
    expect(within(table).getByText('278,138')).toBeVisible();
    expect(within(table).getByText('117,405,318')).toBeVisible();
    expect(screen.getByText(/香港を内数に含みます/)).toBeVisible();
    fireEvent.change(screen.getByLabelText('2025年の分子'), {target:{value:'cleared_persons'}});
    expect(within(table).getByText('189,309')).toBeVisible();
    fireEvent.change(screen.getByLabelText('2025年の外国人対象範囲'), {target:{value:'visiting_foreign'}});
    expect(screen.getAllByText(/日本は来日外国人の対象外/).length).toBeGreaterThan(0);
  });

  it('shows visiting-only 5 countries, real zero, color legend and clustering', () => {
    render(<VisitingOffense2025 data={parseNationality2025(product())} />);
    expect(screen.getByRole('heading', {name:'2025年・来日外国人5国籍の犯罪種類の構成'})).toBeVisible();
    expect(screen.getByText(/0%.*100%/)).toBeVisible();
    expect(screen.getByText(/Jensen–Shannon/)).toBeVisible();
    expect(screen.getByText(/日本：未算出/)).toBeVisible();
    expect(screen.getByText(/外国人全体の構成ではありません/)).toBeVisible();
    fireEvent.change(screen.getByLabelText('2025年犯罪構成の分子'), {target:{value:'cleared_persons'}});
    expect(screen.getByText('7,333')).toBeVisible();
    fireEvent.change(screen.getByLabelText('2025年犯罪構成の表示形式'), {target:{value:'stacked'}});
    expect(screen.getByRole('img', {name:/ベトナムの犯罪構成/})).toBeVisible();
  });
});
