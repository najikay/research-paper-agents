# Quality Gate Report

**Verdict:** FAIL
**Score:** 52/100
**Threshold:** 90
**Failed Sections:** ['methodology']

## Issues Found

- ch01_intro.tex: subsections=2<3, words≈488<1400
- ch02_bio_basis.tex: words≈753<1400
- ch03_sensors.tex: words≈753<1400
- ch04_slam.tex: words≈753<1400
- ch05_fusion.tex: words≈753<1400
- ch06_algorithm.tex: subsections=3<5, citations=2<3, words≈753<1800
- ch07_oursystem.tex: subsections=3<4, words≈753<1600
- ch08_results.tex: subsections=3<5, citations=2<3, words≈753<1800
- ch09_conclusion.tex: words≈359<700

## Per-Chapter Thresholds

- Default: eq>=2, fig>=1, sub>=3, cite>=2, words>=1400
- abstract.tex: eq>=0, fig>=0, sub>=0, cite>=0, words>=80
- ch01_intro.tex: eq>=1, fig>=0
- ch06_algorithm.tex: eq>=3, sub>=5, cite>=3, words>=1800
- ch07_oursystem.tex: sub>=4, words>=1600
- ch08_results.tex: sub>=5, cite>=3, words>=1800
- ch09_conclusion.tex: eq>=0, fig>=0, sub>=2, cite>=1, words>=700
- references.bib: >=10 entries
- Missing figure files: <=-20 total penalty (capped)

```json
{
  "verdict": "FAIL",
  "score": 52,
  "failed_sections": ["methodology"]
}
```
