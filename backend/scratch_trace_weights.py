import os
import sys

# Add backend to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from services.learning_engine.adaptive_weights import resolve_weights
import json
import dataclasses

weights = resolve_weights()
print(json.dumps(dataclasses.asdict(weights), indent=2))
