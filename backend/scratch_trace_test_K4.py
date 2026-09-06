import os
import sys

# Add backend to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.ranking import score_learning_node
from services.learning_engine.context import build_learner_context
from roadmap import get_roadmap

roadmap = get_roadmap()

base_onboarding = {
    "current_position": "1-3",
    "self_assessment": {
        "programming_fundamentals": 10, "java": 10,
        "dsa": 2, "dbms": 3, "operating_systems": 3,
        "computer_networks": 3, "lld": 4, "hld": 4,
    },
}

def analyze_company(company_name):
    print(f"\n{'='*50}\nANALYZING COMPANY: {company_name.upper()}\n{'='*50}")
    onboarding = {**base_onboarding, "target_companies": [company_name.lower()]}
    ctx = build_learner_context(onboarding=onboarding)
    
    dsa_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dsa"), None)
    dbms_node = next((n for n in roadmap.get_learning_nodes() if n.get("track") == "dbms"), None)
    
    for label, node in [("DSA", dsa_node), ("DBMS", dbms_node)]:
        if not node:
            continue
        score_details = score_learning_node(
            node=node,
            progress={},
            target_companies=[company_name.lower()],
            learner_context=ctx
        )
        print(f"{label}: total_score = {score_details['total_score']}")

analyze_company("google")
analyze_company("oracle")
