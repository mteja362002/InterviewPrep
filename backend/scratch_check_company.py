import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from roadmap import get_roadmap

roadmap = get_roadmap()

print("Company importance by track:")
for track_id in ["dsa", "dbms", "operating_systems", "computer_networks", "java", "lld", "hld"]:
    google = roadmap.company_importance(track_id, "google")
    oracle = roadmap.company_importance(track_id, "oracle")
    print(f"  {track_id}: google={google}, oracle={oracle}, delta={google - oracle}")
