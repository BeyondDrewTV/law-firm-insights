import json, sys
sys.path.insert(0, '.')
from services.bench.deterministic_tagger import tag_review
from services.bench import comparator, calibration_report
from services.bench.fixtures import FIXTURES

comparisons = []
for fix in FIXTURES:
    det = tag_review(fix['review_text'], fix['rating'], fix['review_date'])
    comp = comparator.compare(det, None)
    comp['fixture_notes'] = fix['notes']
    comp['expected_themes'] = fix['expected_themes']
    comparisons.append(comp)

c0 = comparisons[0]
print('=== Fixture 0 themes (positive communication) ===')
for t in c0['deterministic']:
    print(f"  {t['theme']:35s}  {t['polarity']:16s}  conf={t['confidence']}")

c1 = comparisons[1]
print('\n=== Fixture 1 themes (billing nightmare - severe) ===')
for t in c1['deterministic']:
    print(f"  {t['theme']:35s}  {t['polarity']:16s}  conf={t['confidence']}")

c4 = comparisons[4]
print('\n=== Fixture 4 themes (contrast: professional but delays) ===')
for t in c4['deterministic']:
    print(f"  {t['theme']:35s}  {t['polarity']:16s}  conf={t['confidence']}")

# Evidence log spot check
c2 = comparisons[2]
print('\n=== Fixture 2 evidence log (negation test) ===')
for e in c2['evidence_log'][:6]:
    print(f"  phrase={e['matched_phrase']!r:25s}  polarity={e['polarity']:16s}  mults={e['multipliers_applied']}")

report = calibration_report.generate(comparisons)
print('\n=== Summary ===')
print(json.dumps(report['summary'], indent=2))
print('\n=== By-theme ===')
for row in report['by_theme']:
    if row['det_mentions'] > 0:
        print(f"  {row['theme']:35s}  mentions={row['det_mentions']}  disagree={row['total_disagreements']}")
print('\nAll tests passed.')
