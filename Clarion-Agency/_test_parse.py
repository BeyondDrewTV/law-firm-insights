import sys
sys.path.insert(0, r"C:\Users\beyon\OneDrive\Desktop\CLARION\law-firm-insights-main\Clarion-Agency")

from shared.report_parser import parse_and_queue

reports = [
    ("reports/sales/prospect_intelligence_agent_2026-03-12.md", "Prospect Intel", {"prospect_target_list"}),
    ("reports/sales/outbound_sales_agent_2026-03-12.md", "Outbound Sales", {"outreach_email"}),
    ("reports/comms/content_seo_2026-03-12.md", "Content SEO", {"thought_leadership_article","linkedin_post","founder_thread","account_setup"}),
    ("reports/product/product_experience_agent_2026-03-12.md", "Product Exp", {"conversion_friction_report","landing_page_revision","product_improvement"}),
]

BASE = r"C:\Users\beyon\OneDrive\Desktop\CLARION\law-firm-insights-main\Clarion-Agency"
import os
os.chdir(BASE)

for rel, name, types in reports:
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        print(f"[MISSING] {rel}")
        continue
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    print(f"\n--- {name} --- ({len(text)} chars)")
    ids = parse_and_queue(text, name, types)
    print(f"  -> Queued: {ids}")

# Show final queue
import json
with open(os.path.join(BASE, "data/approval_queue.json"), encoding="utf-8") as f:
    q = json.load(f)
print(f"\n=== APPROVAL QUEUE: {len(q)} items ===")
for item in q:
    print(f"  [{item['id']}] {item.get('type','?')} | {item.get('title','?')[:60]}")
