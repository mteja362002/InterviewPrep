"""Verification: check that effectively_completed_tracks() returns values
that are roadmap track IDs (i.e. the identifiers used by
roadmap.completed_subject_ids and build_all_sessions)."""
from roadmap import get_roadmap
from services.learning_engine.context import build_learner_context

r = get_roadmap()
track_ids = set(r.track_ids())
print("Roadmap track IDs:", track_ids)

# Case 1: PF=9 onboarding, zero progress
ctx1 = build_learner_context(
    onboarding={
        "current_position": "student",
        "self_assessment": {"programming_fundamentals": 9, "java": 1},
    },
)
eff_tracks = ctx1.effectively_completed_tracks()
print("\neffectively_completed_tracks (PF=9):", eff_tracks)
print("All are valid track IDs:", eff_tracks.issubset(track_ids))

eff_subjects = ctx1.effective_completed_subject_ids(r)
print("effective_completed_subject_ids (PF=9):", eff_subjects)
print("All are valid track IDs:", eff_subjects.issubset(track_ids))

# Case 2: PF=0 onboarding, zero progress
ctx2 = build_learner_context(
    onboarding={
        "current_position": "student",
        "self_assessment": {"programming_fundamentals": 0, "java": 0},
    },
)
eff_tracks2 = ctx2.effectively_completed_tracks()
print("\neffectively_completed_tracks (PF=0):", eff_tracks2)
eff_subjects2 = ctx2.effective_completed_subject_ids(r)
print("effective_completed_subject_ids (PF=0):", eff_subjects2)

# Case 3: Threshold boundary - PF=7 → effective score = 70.0, threshold = 70.0
ctx3 = build_learner_context(
    onboarding={
        "current_position": "student",
        "self_assessment": {"programming_fundamentals": 7},
    },
)
score = ctx3.effective_knowledge_score("programming_fundamentals")
eff_tracks3 = ctx3.effectively_completed_tracks()
print(f"\nPF=7: effective_knowledge_score={score}, effectively_completed_tracks={eff_tracks3}")
print("PF=7 is at/above threshold:", "programming_fundamentals" in eff_tracks3)

# Case 4: PF=6 → effective score = 60.0, below threshold
ctx4 = build_learner_context(
    onboarding={
        "current_position": "student",
        "self_assessment": {"programming_fundamentals": 6},
    },
)
score4 = ctx4.effective_knowledge_score("programming_fundamentals")
eff_tracks4 = ctx4.effectively_completed_tracks()
print(f"\nPF=6: effective_knowledge_score={score4}, effectively_completed_tracks={eff_tracks4}")
print("PF=6 is below threshold:", "programming_fundamentals" not in eff_tracks4)

# Check that onboarding_scores keys match roadmap track IDs
print("\n--- Onboarding score keys vs roadmap track IDs ---")
assessment_keys = set(ctx1.onboarding_scores.keys())
print("Assessment keys:", assessment_keys)
print("Assessment keys that are NOT roadmap tracks:", assessment_keys - track_ids)
print("Roadmap tracks that are NOT assessment keys:", track_ids - assessment_keys)
