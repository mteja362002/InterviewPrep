import os
import sys

# Add backend to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.ranking import score_learning_node
from services.learning_engine.context import build_learner_context
from roadmap import get_roadmap
import json

roadmap = get_roadmap()

base_onboarding = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 5, "dbms": 2, "operating_systems": 2,
        "computer_networks": 2, "lld": 4, "hld": 4,
    },
}

def analyze_company(company_name):
    print(f"\n{'='*50}\nANALYZING COMPANY: {company_name.upper()}\n{'='*50}")
    onboarding = {**base_onboarding, "target_companies": [company_name.lower()]}
    ctx = build_learner_context(onboarding=onboarding)
    
    # We want to score a node from DSA and a node from Core CS (e.g., DBMS)
    dsa_node = next((n for n in roadmap.learning_nodes() if n["track"] == "dsa"), None)
    dbms_node = next((n for n in roadmap.learning_nodes() if n["track"] == "dbms"), None)
    
    print(f"\nEffective Completed Subjects: {ctx.effective_completed_subject_ids(roadmap)}")
    
    for label, node in [("DSA", dsa_node), ("DBMS", dbms_node)]:
        if not node:
            print(f"Could not find node for {label}")
            continue
            
        print(f"\n--- SCORING: {label} ({node['id']}) ---")
        score_details = score_learning_node(
            node=node,
            progress={},
            target_companies=[company_name.lower()],
            learner_context=ctx
        )
        print(json.dumps(score_details, indent=2))

analyze_company("google")
analyze_company("oracle")
