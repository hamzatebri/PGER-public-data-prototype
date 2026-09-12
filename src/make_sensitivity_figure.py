"""Render two separate measures of score sensitivity from retained results."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = pd.read_csv(ROOT / 'data/processed/score_sensitivity.csv')
    data = data[~data.scenario.str.startswith('Baseline')]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5), sharey=True)
    y = range(len(data))
    axes[0].scatter(data.spearman_with_baseline, y, color='#235477', s=65)
    axes[0].set_yticks(list(y), data.scenario)
    axes[0].set_xlim(.75, 1.06)
    axes[0].set_xlabel('Spearman correlation (zoomed)')
    axes[0].set_title('Overall ranking', weight='bold', pad=18)
    axes[1].barh(list(y), data.top_10_overlap, height=.4, color='#bd642e')
    axes[1].set_xlim(0, 11.5)
    axes[1].set_xlabel('Number of the original ten notices')
    axes[1].set_title('Original top ten retained', weight='bold', pad=18)
    for i, row in enumerate(data.itertuples()):
        axes[0].annotate(f'{row.spearman_with_baseline:.3f}', (row.spearman_with_baseline, i),
                         xytext=(7, 0), textcoords='offset points', va='center', fontsize=11)
        axes[1].text(row.top_10_overlap + .2, i, f'{row.top_10_overlap}/10', va='center')
    axes[0].invert_yaxis()
    for ax in axes:
        ax.grid(axis='x', alpha=.2)
        ax.set_axisbelow(True)
    fig.tight_layout(pad=2.1, w_pad=3)
    for extension in ('png', 'svg'):
        path = ROOT / f'figures/figure_09_score_weight_sensitivity.{extension}'
        fig.savefig(path, dpi=350)
        if extension == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    plt.close(fig)


if __name__ == '__main__':
    main()
