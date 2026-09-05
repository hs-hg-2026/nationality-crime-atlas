import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import dashboardFixture from '@/public/data/dashboard_export.json';
import { CrimeAtlasDashboard } from '@/components/crime-atlas-dashboard';
import { choroplethColor } from '@/components/prefecture-map';
import { parseDashboardData } from '@/lib/dashboard';

const dashboard = parseDashboardData(dashboardFixture);

describe('prefecture choropleth scale', () => {
  it('uses a stable midpoint color when every value is identical', () => {
    expect(choroplethColor(4, 4, 4)).toBe('#76b5a9');
    expect(choroplethColor(1, 0, 4)).not.toBe(choroplethColor(4, 0, 4));
  });
});

describe('CrimeAtlasDashboard', () => {
  it('explains the site purpose in plain Japanese and links to full documentation', () => {
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    expect(
      screen.getByRole('heading', { name: '全国犯罪統計地図' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'このサイトについて' }),
    ).toBeVisible();
    expect(
      screen.getByText(
        /犯罪に関する公的な情報は、複数の機関や資料に分散しており/,
      ),
    ).toBeVisible();
    expect(
      screen.getByText(
        /それらの公表情報を収集・整理し、犯罪統計と人口統計を可視化する試作サイトです/,
      ),
    ).toBeVisible();
    expect(
      screen.getByText(
        /数値の良し悪しの評価、原因の推定、集団や個人に対する価値判断は行いません/,
      ),
    ).toBeVisible();
    expect(
      screen.queryByText(/国籍についての印象や決めつけではなく/),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/日本人と外国人を合わせた地域全体/)).toBeVisible();
    expect(
      screen.getByRole('link', {
        name: 'プロジェクトの詳しい説明を読む',
      }),
    ).toHaveAttribute(
      'href',
      'https://github.com/hs-hg-2026/nationality-crime-atlas/blob/main/README.ja.md',
    );
    expect(
      screen.getByRole('link', { name: /数字の読み方を確認/ }),
    ).toHaveAttribute(
      'href',
      'https://github.com/hs-hg-2026/nationality-crime-atlas/blob/main/docs/interpretation_note.md',
    );
    expect(
      screen.getByRole('navigation', { name: 'ページ内メニュー' }),
    ).toBeVisible();
    expect(screen.queryByText('PRIMARY VIEW')).not.toBeInTheDocument();
    expect(screen.queryByText('SECONDARY VIEW')).not.toBeInTheDocument();
    expect(screen.queryByText(/nationality-neutral/)).not.toBeInTheDocument();
    expect(screen.queryByText(/1年間のflow/)).not.toBeInTheDocument();
    expect(screen.queryByText(/residency scope/)).not.toBeInTheDocument();
  });

  it('opens on a useful all-resident comparison with permanent cautions', () => {
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    expect(screen.getByText('地域比較の例')).toBeVisible();
    expect(
      screen.getByRole('heading', { name: '人口規模をそろえて比較' }),
    ).toBeVisible();
    expect(
      screen.queryByRole('heading', { name: /東京と埼玉/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId('tokyo-comparison')).toHaveTextContent(
      '東京都',
    );
    expect(screen.getByTestId('saitama-comparison')).toHaveTextContent(
      '埼玉県',
    );
    expect(
      screen.getByRole('heading', { name: '全国犯罪統計地図' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        name: '国籍で分けない、地域全体の状況',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /分母の総人口は、日本国籍の住民と外国籍の住民を含みます/,
      ),
    ).toBeVisible();
    expect(
      within(screen.getByTestId('tokyo-comparison')).getByText('668.30'),
    ).toBeVisible();
    expect(
      within(screen.getByTestId('saitama-comparison')).getByText('704.68'),
    ).toBeVisible();
    expect(
      screen.getByText(/公的機関が算出した正式な犯罪率ではありません/),
    ).toBeVisible();
    expect(
      screen.getByText(/1年間の犯罪件数と、その年の10月1日時点の人口/),
    ).toBeVisible();
    expect(
      screen.getByText(/犯罪件数に数えられた人の居住地は確認できません/),
    ).toBeVisible();
    expect(screen.getByText(/刑法犯認知件数 ÷ 人口 × 100,000/)).toBeVisible();
    expect(screen.getAllByText(/SHA-256/).length).toBeGreaterThanOrEqual(4);
    expect(
      screen.getByRole('heading', { name: '47都道府県の地図' }),
    ).toBeVisible();
    expect(
      screen
        .getByTestId('prefecture-map')
        .querySelectorAll('[data-prefecture-code]'),
    ).toHaveLength(47);
    expect(
      screen.getByText(/地形・面積・距離を表すものではありません/),
    ).toBeVisible();
    expect(screen.getByTestId('map-selected-prefecture')).toHaveTextContent(
      /東京都.*668.30.*人口.*14,178,000/,
    );
    const hokkaido = screen
      .getByTestId('prefecture-map')
      .querySelector('[data-prefecture-code="01"]');
    expect(hokkaido).not.toBeNull();
    fireEvent.focus(hokkaido as SVGPathElement);
    expect(screen.getByTestId('map-selected-prefecture')).toHaveTextContent(
      '北海道',
    );
    expect(
      screen.getByRole('heading', {
        name: '日本を含む国籍等別の全国比較',
      }),
    ).toBeVisible();
    expect(
      screen.getByText(/個別国籍 × 都道府県の分子は公表されていません/),
    ).toBeVisible();
    expect(screen.getByText(/26区分すべて/)).toBeVisible();
    expect(screen.getByText('4区分は未算出')).toBeVisible();
    expect(
      screen.queryByText(/excluded from ranking/i),
    ).not.toBeInTheDocument();
  });

  it('switches the comparison from reference ratios to raw counts', async () => {
    const user = userEvent.setup();
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    await user.click(screen.getByRole('button', { name: '件数' }));

    expect(
      within(screen.getByTestId('tokyo-comparison')).getByText('94,752'),
    ).toBeVisible();
    expect(
      within(screen.getByTestId('saitama-comparison')).getByText('51,667'),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: '件数' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    await user.click(screen.getByRole('button', { name: '人口当たり' }));
    expect(
      within(screen.getByTestId('tokyo-comparison')).getByText('668.30'),
    ).toBeVisible();
  });

  it('changes metric and keeps official source links reachable', async () => {
    const user = userEvent.setup();
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: '指標' }),
      'all_resident_cleared_persons',
    );

    expect(
      screen.getByRole('option', { name: '刑法犯検挙人員', selected: true }),
    ).toBeInTheDocument();
    for (const link of screen.getAllByRole('link', {
      name: 'S15 公表ページ',
    })) {
      expect(link).toHaveAttribute(
        'href',
        expect.stringMatching(/^https:\/\//),
      );
    }
    expect(
      screen.getByRole('link', { name: 'S16 公表ページ' }),
    ).toHaveAttribute('href', expect.stringMatching(/^https:\/\//));
  });

  it('renders cleared-person raw values with person semantics', async () => {
    const user = userEvent.setup();
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: '指標' }),
      'all_resident_cleared_persons',
    );
    await user.click(screen.getByRole('button', { name: '人員' }));

    expect(screen.getByRole('button', { name: '人員' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByTestId('tokyo-comparison')).toHaveTextContent(
      /23,731人.*人員 23,731/,
    );
    expect(screen.getByTestId('map-selected-prefecture')).toHaveTextContent(
      /23,731\s*人.*人員.*23,731/,
    );
  });

  it('shows the same-year recognition-clearance gap in plain Japanese without cohort jargon', async () => {
    const user = userEvent.setup();
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    await user.selectOptions(
      screen.getByRole('combobox', { name: '指標' }),
      'all_resident_same_year_recognition_clearance_gap',
    );

    expect(
      screen.getByRole('heading', {
        name: '認知件数と検挙件数の同年差',
      }),
    ).toBeVisible();
    expect(
      screen.getByRole('heading', {
        name: '同年差分の件数と割合を比較',
      }),
    ).toBeVisible();
    expect(screen.getByText('「未解決率」ではありません')).toBeVisible();
    expect(
      screen.getByText(/同じ事件を認知から検挙まで追跡した数字ではありません/),
    ).toBeVisible();
    expect(document.body).not.toHaveTextContent(/cohort|strict|clamp|同年flow/);
    expect(screen.getByText(/61\.06/)).toBeVisible();
    expect(
      within(screen.getByTestId('tokyo-comparison')).getByText('64.16'),
    ).toBeVisible();
    expect(
      within(screen.getByTestId('saitama-comparison')).getByText('67.70'),
    ).toBeVisible();
    expect(screen.getByTestId('map-selected-prefecture')).toHaveTextContent(
      /同年差分件数.*60,791.*認知件数.*94,752.*同年差分率.*64\.16/,
    );

    await user.click(screen.getByRole('button', { name: '同年差分件数' }));
    expect(
      within(screen.getByTestId('tokyo-comparison')).getByText('60,791'),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: '同年差分件数' }),
    ).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('map-selected-prefecture')).toHaveTextContent(
      /同年差分率.*64\.16 %/,
    );
    expect(screen.getByTestId('map-selected-prefecture')).not.toHaveTextContent(
      /同年差分率.*64\.16 件/,
    );
  });

  it('shows high and low observations symmetrically and keeps every nationality category', () => {
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    const section = screen.getByTestId('nationality-comparison-section');
    const highSide = within(section).getByTestId('nationality-high-side');
    const lowSide = within(section).getByTestId('nationality-low-side');
    const fullTable = within(section).getByTestId(
      'nationality-comparison-table',
    );

    expect(
      within(highSide).getByRole('cell', { name: '無国籍' }),
    ).toBeVisible();
    expect(within(highSide).getByText(/10.68/)).toBeVisible();
    expect(
      within(highSide).getByText(
        /人口が少ないため、参考比率が大きく変動しやすい/,
      ),
    ).toBeVisible();
    expect(
      within(lowSide).getByRole('cell', { name: 'インドネシア' }),
    ).toBeVisible();
    expect(
      within(lowSide).getByRole('cell', {
        name: /日本（残差による参考値）/,
      }),
    ).toBeVisible();
    expect(within(fullTable).getAllByRole('row')).toHaveLength(27);
    expect(
      within(fullTable).getByTestId('nationality-japanese-reference'),
    ).toHaveTextContent(/日本（残差による参考値）.*181,362.*120,296,000.*1.51/);
    expect(within(fullTable).getByText('国籍不明')).toBeVisible();
    expect(within(fullTable).getAllByText('未算出')).toHaveLength(4);

    for (const sourceId of ['S08', 'S14_2024_12', 'S15', 'S17']) {
      expect(
        within(section).getByRole('link', {
          name: `${sourceId} 公表ページ`,
        }),
      ).toHaveAttribute('href', expect.stringMatching(/^https:\/\//));
    }
  });

  it('shows all nationality offense patterns as a clustered heatmap and 100% bars', async () => {
    const user = userEvent.setup();
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    const section = screen.getByTestId('offense-composition-section');
    expect(
      within(section).getByRole('heading', {
        name: '日本を含む国籍等別・犯罪類型の構成',
      }),
    ).toBeVisible();
    expect(
      within(section).getAllByTestId('offense-category-legend'),
    ).toHaveLength(6);
    expect(within(section).getByText(/凶悪犯は警察庁の公式区分/)).toBeVisible();
    expect(
      within(section).getByText(/残る5区分を軽犯罪とは定義しません/),
    ).toBeVisible();

    const heatmap = within(section).getByTestId('offense-composition-heatmap');
    expect(within(heatmap).getAllByRole('row')).toHaveLength(27);
    expect(
      within(heatmap).getByTestId('offense-japanese-reference'),
    ).toHaveTextContent(/日本（残差による参考値）.*181,362.*83,810/);
    expect(
      within(section).getByText(/似た構成が近くなるよう機械的に並べています/),
    ).toBeVisible();

    await user.click(within(section).getByRole('button', { name: '検挙件数' }));
    expect(
      within(section).getByText(/国籍不明.*件数構成は算出不能/),
    ).toBeVisible();

    await user.click(
      within(section).getByRole('button', { name: '100%積み上げ棒' }),
    );
    expect(
      within(section).getByTestId('offense-composition-stacked'),
    ).toBeVisible();
    expect(within(section).getAllByTestId('offense-stacked-row')).toHaveLength(
      26,
    );

    await user.click(
      within(section).getByRole('button', { name: '元データの掲載順' }),
    );
    expect(
      within(section).getAllByTestId('offense-stacked-row')[0],
    ).toHaveTextContent('日本（残差による参考値）');
  });

  it('selects nationality numerator scope without hiding refused or warning rows', async () => {
    const user = userEvent.setup();
    render(<CrimeAtlasDashboard dashboard={dashboard} />);

    const section = screen.getByTestId('nationality-comparison-section');
    const selector = within(section).getByRole('combobox', {
      name: '国籍等別の分子・対象範囲',
    });
    expect(within(selector).getAllByRole('option')).toHaveLength(9);
    expect(within(section).getByText('参考比率の式')).toBeVisible();
    expect(within(section).getByText(/高低表の尺度:/)).toBeVisible();
    expect(
      within(section).getByText(
        /比率を算出できる区分から機械的に抽出.*未算出の行は全区分表に残します/,
      ),
    ).toBeVisible();

    await user.selectOptions(selector, 'x_cleared_persons_exact');

    expect(
      within(selector).getByRole('option', {
        name: '全外国人の検挙人員（同じ国籍区分で人口と対応）',
        selected: true,
      }),
    ).toBeInTheDocument();
    const fullTable = within(section).getByTestId(
      'nationality-comparison-table',
    );
    expect(within(fullTable).getAllByRole('row')).toHaveLength(26);
    expect(
      within(fullTable).getByRole('row', { name: /ベトナム/ }),
    ).toHaveTextContent(/4,113.*634,361.*6\.48/);
    expect(
      within(fullTable).getByRole('row', { name: /その他（アジア州の国）/ }),
    ).toHaveTextContent(/1,338.*未算出/);
    expect(
      within(fullTable).getByTestId('nationality-japanese-reference'),
    ).toHaveTextContent(
      /日本（対応する公表分子なし）.*未算出.*同じ条件の日本国籍の犯罪件数・人員がない/,
    );
    expect(within(section).getByText('7区分は未算出')).toBeVisible();

    await user.click(
      within(section).getByRole('button', { name: '実数（検挙人員）' }),
    );
    expect(
      within(section).getByTestId('nationality-high-side'),
    ).toHaveTextContent(/ベトナム.*4,113.*人/);
    expect(
      within(section).getByRole('button', { name: '実数（検挙人員）' }),
    ).toHaveAttribute('aria-pressed', 'true');
    expect(
      within(section).getByText(
        /公表された犯罪件数・人員がある区分から機械的に抽出.*公表実数を表示します/,
      ),
    ).toBeVisible();
  });
});
