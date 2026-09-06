import os
import sys

# Add backend to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.ranking import rank_learning_nodes
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

ctx = build_learner_context(onboarding={**base_onboarding, "target_companies": ["oracle"]})

nodes = roadmap.get_learning_nodes()
ranked = rank_learning_nodes(nodes, {}, target_companies=["oracle"], learner_context=ctx)

for r in ranked[:5]:
    print(f"{r['id']} ({r.get('track')}): {r.get('score')}")
