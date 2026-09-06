import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from roadmap import get_roadmap

roadmap = get_roadmap()

print("Mastery weights by track:")
for track_id in ["dsa", "dbms", "operating_systems", "computer_networks", "java", "lld", "hld"]:
    nodes = roadmap.get_track_learning_nodes(track_id)
    if nodes:
        print(f"{track_id}: {nodes[0].get('mastery_weight')}")
