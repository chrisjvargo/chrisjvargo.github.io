from __future__ import annotations

import html


def svg_bar_chart(title: str, desc: str, rows: list[dict[str, str]], label_key: str, value_key: str) -> str:
    width = 760
    bar_h = 26
    gap = 12
    left = 250
    top = 54
    values = [float(r.get(value_key) or 0) for r in rows]
    max_v = max(values) if values else 1
    height = top + len(rows) * (bar_h + gap) + 30
    parts = [
        f'<svg class="dv-chart" role="img" viewBox="0 0 {width} {height}" aria-labelledby="chart-title chart-desc">',
        f'<title id="chart-title">{html.escape(title)}</title>',
        f'<desc id="chart-desc">{html.escape(desc)}</desc>',
        f'<text x="0" y="24" class="chart-title">{html.escape(title)}</text>',
    ]
    for i, row in enumerate(rows):
        y = top + i * (bar_h + gap)
        label = row.get(label_key, "")
        value = float(row.get(value_key) or 0)
        w = 1 if max_v == 0 else int((width - left - 90) * value / max_v)
        parts.append(f'<text x="0" y="{y + 18}" class="chart-label">{html.escape(label)}</text>')
        parts.append(f'<rect x="{left}" y="{y}" width="{w}" height="{bar_h}" rx="0"></rect>')
        parts.append(f'<text x="{left + w + 8}" y="{y + 18}" class="chart-value">{value:g}</text>')
    parts.append("</svg>")
    return "\n".join(parts)

