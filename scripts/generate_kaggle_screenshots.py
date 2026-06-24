#!/usr/bin/env python3
"""Render static HTML mockups of the Flutter result screen for Kaggle Media Gallery."""

from __future__ import annotations

import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MEDIA = REPO / "docs" / "kaggle_submission" / "media"

SEVERITY_COLORS = {
    "HIGH": "#B71C1C",
    "MODERATE": "#E65100",
    "LOW": "#F9A825",
    "INFO": "#1565C0",
    "NONE": "#2E7D32",
}


def _load_json(path: Path) -> dict:
    text = path.read_text()
    start = text.find("{")
    return json.loads(text[start:])


def render(result: dict, title: str, lang_label: str) -> str:
    severity = result.get("overall_severity", "NONE")
    color = SEVERITY_COLORS.get(severity, "#455A64")
    drugs = result.get("resolved_drugs", [])
    interactions = result.get("interactions", [])
    summary = result.get("explanation_localised") or result.get("explanation_en", "")
    questions = result.get("doctor_questions", [])
    disclaimer = result.get("disclaimer", "")
    has_audio = bool(result.get("audio_url"))

    drug_cards = "".join(
        f"""<div class="card drug">
          <div class="name">{html.escape(d.get('raw_name', ''))}</div>
          <div class="generic">→ {html.escape(d.get('generic_name') or 'UNRESOLVED')}</div>
          <span class="tag">{html.escape(d.get('tag', 'NEW'))}</span>
        </div>"""
        for d in drugs
    )

    interaction_cards = "".join(
        f"""<div class="card interaction">
          <div class="sev">{html.escape(i.get('severity', ''))}</div>
          <div class="pair">{html.escape(i.get('drug_a', ''))} + {html.escape(i.get('drug_b', ''))}</div>
          <p>{html.escape(i.get('mechanism', ''))}</p>
        </div>"""
        for i in interactions
    )

    questions_html = "".join(f"<li>{html.escape(q)}</li>" for q in questions)

    audio_block = (
        """<div class="audio">
          <button type="button">▶ Play explanation audio</button>
          <span>GCP Text-to-Speech · 24h signed URL</span>
        </div>"""
        if has_audio
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; display: flex; justify-content: center;
      background: #ECEFF1; font-family: system-ui, -apple-system, sans-serif;
    }}
    .phone {{
      width: 390px; min-height: 844px; background: #FAFAFA; margin: 24px;
      border-radius: 24px; box-shadow: 0 8px 32px rgba(0,0,0,.12); overflow: hidden;
    }}
    .header {{ background: #1A237E; color: #fff; padding: 20px 16px 12px; }}
    .header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
    .header p {{ margin: 4px 0 0; font-size: 12px; opacity: .85; }}
    .banner {{
      margin: 16px; padding: 14px 16px; border-radius: 12px; color: #fff;
      background: {color}; font-weight: 600; font-size: 15px;
    }}
    .section {{ padding: 0 16px 12px; }}
    .section h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .06em;
      color: #607D8B; margin: 16px 0 8px; }}
    .card {{
      background: #fff; border-radius: 12px; padding: 12px 14px; margin-bottom: 8px;
      border: 1px solid #E0E0E0;
    }}
    .drug .name {{ font-weight: 600; color: #212121; }}
    .drug .generic {{ color: #455A64; font-size: 14px; margin-top: 4px; }}
    .tag {{
      display: inline-block; margin-top: 8px; padding: 2px 8px; border-radius: 999px;
      background: #E3F2FD; color: #1565C0; font-size: 11px; font-weight: 600;
    }}
    .interaction .sev {{ color: {color}; font-weight: 700; font-size: 12px; }}
    .interaction .pair {{ font-weight: 600; margin: 4px 0; }}
    .interaction p {{ margin: 0; font-size: 13px; color: #37474F; line-height: 1.45; }}
    .summary {{ font-size: 14px; line-height: 1.5; color: #263238; }}
    .audio {{
      margin: 12px 16px; padding: 12px; background: #E8EAF6; border-radius: 12px;
      display: flex; flex-direction: column; gap: 6px;
    }}
    .audio button {{
      background: #1A237E; color: #fff; border: 0; border-radius: 999px;
      padding: 10px 16px; font-weight: 600; cursor: default;
    }}
    .audio span {{ font-size: 11px; color: #5C6BC0; }}
    .questions ul {{ margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.5; }}
    .disclaimer {{
      margin: 16px; padding: 12px; background: #FFF8E1; border-radius: 8px;
      font-size: 12px; color: #5D4037; line-height: 1.4;
    }}
    .lang {{ float: right; font-size: 11px; opacity: .9; }}
  </style>
</head>
<body>
  <div class="phone">
    <div class="header">
      <span class="lang">{html.escape(lang_label)}</span>
      <h1>Medication Companion</h1>
      <p>AI-powered prescription analysis</p>
    </div>
    <div class="banner">{severity} — review interactions before starting these medicines</div>
    <div class="section">
      <h2>Medications ({len(drugs)})</h2>
      {drug_cards}
    </div>
    <div class="section">
      <h2>Interactions ({len(interactions)})</h2>
      {interaction_cards}
    </div>
    {audio_block}
    <div class="section">
      <h2>Summary</h2>
      <div class="card summary">{html.escape(summary)}</div>
    </div>
    <div class="section questions">
      <h2>Questions for your doctor</h2>
      <div class="card"><ul>{questions_html}</ul></div>
    </div>
    <div class="disclaimer">{html.escape(disclaimer)}</div>
  </div>
</body>
</html>"""


def main() -> None:
    pairs = [
        (MEDIA / "e2e_result_en.json", "Result — English", "en-IN", "02_result_screen_en.html"),
        (MEDIA / "e2e_result_hi.json", "Result — Hindi", "hi-IN", "03_result_screen_hi.html"),
    ]
    for src, title, lang, out_name in pairs:
        if not src.exists():
            print(f"Skip {src} (missing — run E2E capture first)")
            continue
        result = _load_json(src)
        out = MEDIA / out_name
        out.write_text(render(result, title, lang), encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
