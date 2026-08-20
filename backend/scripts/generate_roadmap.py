"""PrepOS Roadmap Generator (v1)
================================
Builds `backend/data/roadmap_v1.json` — the single source of truth for the
entire PrepOS learning graph. Every future feature (Mission Engine, AI
Mentor, Analytics, Revision Engine, Mock Interviews) reads from this graph.

Design principles:
- Preserve every legacy node ID that existed in v1 so user progress stays valid.
- Keep the exact schema expected by `roadmap.py`:
  Track -> modules[] -> topics[] -> (subtopics[] | learning_nodes[])
- Attach rich metadata to every node without touching UI/logic.
- Deterministic output: running this script twice produces byte-identical JSON.

Run: `python -m backend.scripts.generate_roadmap`
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

# Ensure ``backend/`` is importable so the canonical curriculum metadata
# derivation is shared with the runtime migration (single source of truth).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.curriculum.activity_metadata import stamp_node  # noqa: E402

VERSION = "v1"
GENERATED_AT = "2026-02-01"

COMPANIES = [
    "google", "microsoft", "atlassian", "uber", "adobe", "linkedin",
    "stripe", "salesforce", "oracle", "phonepe", "flipkart",
    "paypal", "goldman_sachs", "zoho",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ci(**overrides: int) -> dict:
    """Build a company_importance dict (0..5) with default 3 for unspecified."""
    unknown = set(overrides) - set(COMPANIES)
    if unknown:
        raise ValueError(f"ci() received unknown company id(s) not in COMPANIES: {sorted(unknown)}")
    base = {c: 3 for c in COMPANIES}
    for k, v in overrides.items():
        base[k] = v
    return base


def node(nid: str, label: str, description: str = "", **extra) -> dict:
    """Minimal learning-node factory. Extra kwargs become metadata."""
    d = {"id": nid, "label": label, "description": description}
    d.update(extra)
    return d


# ---------------------------------------------------------------------------
# Design-pattern & case-study helpers
# ---------------------------------------------------------------------------

def pattern_subtopic(pid: str, label: str, description: str = "", *,
                     prereqs: list | None = None) -> dict:
    """A GoF pattern with the mandated 5-part breakdown.

    ``prereqs`` is optional and additive: it is authored on the pattern
    container itself (mirroring ``lld_case_topic``/``hld_case_topic``) and
    is resolved down onto the pattern's first real leaf
    (``{pid}.overview``) by ``_propagate_container_prerequisites`` in the
    post-processing pass, since the container itself has children and is
    therefore never a directly-unlockable learning node.
    """
    d: dict = {
        "id": pid, "label": label, "description": description,
        "learning_nodes": [
            node(f"{pid}.overview", "Overview",
                 f"Intent, motivation and applicability of the {label} pattern."),
            node(f"{pid}.uml", "UML Diagram",
                 "Class + sequence diagram."),
            node(f"{pid}.use_cases", "Use Cases",
                 "Real-world scenarios where this pattern shines."),
            node(f"{pid}.java", "Java Implementation",
                 "Reference implementation with idiomatic Java."),
            node(f"{pid}.interview", "Interview Questions",
                 "Common LLD-round follow-ups on this pattern."),
        ],
    }
    if prereqs:
        d["prerequisites"] = prereqs
    return d


def lld_case_topic(cid: str, label: str, description: str, *,
                   difficulty: str = "medium", minutes: int = 75,
                   freq: int = 3, weight: float = 1.3,
                   tags: list | None = None, company: dict | None = None,
                   prereqs: list | None = None) -> dict:
    """LLD case-study topic — no subtopics per spec."""
    return {
        "id": cid, "label": label, "description": description,
        "difficulty": difficulty, "estimated_minutes": minutes,
        "interview_frequency": freq, "mastery_weight": weight,
        "prerequisites": prereqs or [],
        "tags": tags or ["case-study", "machine-coding"],
        "company_importance": company or ci(),
    }


_HLD_SUBTOPIC_SPECS = [
    ("problem", "Problem Statement",
        "What are we building and for whom?"),
    ("func_req", "Functional Requirements",
        "Must-have user-visible features."),
    ("non_func_req", "Non-Functional Requirements",
        "Availability, latency, consistency, durability targets."),
    ("capacity", "Capacity Estimation",
        "QPS, storage and bandwidth back-of-envelope math."),
    ("apis", "APIs",
        "Public REST / gRPC surface with request-response shapes."),
    ("db", "Database Design",
        "Schema, indexes, sharding key, replication topology."),
    ("components", "High-Level Components",
        "Services, queues, caches, data stores and their wiring."),
    ("scaling", "Scaling Strategy",
        "How the system grows with load and geographic distribution."),
    ("bottlenecks", "Bottlenecks",
        "Failure modes, hot spots and their mitigations."),
    ("interview", "Interview Discussion Points",
        "Follow-ups a system-design interviewer will drill into."),
]


def hld_case_topic(cid: str, label: str, description: str, *,
                   difficulty: str = "hard", minutes: int = 90,
                   freq: int = 4, weight: float = 1.5,
                   tags: list | None = None, company: dict | None = None,
                   prereqs: list | None = None) -> dict:
    """HLD case-study topic with the mandated 10-subtopic breakdown."""
    return {
        "id": cid, "label": label, "description": description,
        "difficulty": difficulty, "estimated_minutes": minutes,
        "interview_frequency": freq, "mastery_weight": weight,
        "prerequisites": prereqs or [],
        "tags": tags or ["case-study", "system-design"],
        "company_importance": company or ci(),
        "subtopics": [
            {"id": f"{cid}.{suf}", "label": lbl, "description": desc}
            for suf, lbl, desc in _HLD_SUBTOPIC_SPECS
        ],
    }


# ---------------------------------------------------------------------------
# PROGRAMMING FUNDAMENTALS
# ---------------------------------------------------------------------------
# Phase 1 curriculum sync (2026) — the canonical PF-101 subject
# (`docs/curriculum/subjects/01-programming-fundamentals.md`) had no
# corresponding track anywhere in the roadmap. Every downstream subject
# (Java, DSA, DBMS, OS, CN, LLD, HLD) assumed programming fluency that was
# never actually taught. This track is the language-independent on-ramp
# every learner starts at. One topic per canonical module (29 modules,
# Foundation -> Expert), matching the shallow-topic style already used for
# OS/DBMS/CN modules elsewhere in this file — the source doc provides only
# a "Major Areas" concept list per module, not exhaustive sub-lessons, so
# no additional depth is invented beyond what's named in the doc.

PF_TRACK = {
    "id": "programming_fundamentals", "label": "Programming Fundamentals", "icon": "terminal",
    "description": "The language-independent on-ramp: computational thinking, memory, complexity and "
                   "engineering discipline before any specific language or system-level subject.",
    "interview_importance": 2,
    "company_importance": ci(),
    "tags": ["fundamentals", "programming-basics"],
    "modules": [
        {"id": "pf.intro", "label": "Introduction to Programming",
         "description": "Why programming exists, language history and how source becomes execution.",
         "topics": [
            {"id": "pf.intro.core", "label": "What Is Programming?",
             "description": "History of programming languages, low-level vs high-level, compiled vs "
                            "interpreted, source/executable/machine code, bytecode, runtime environment.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.7,
             "tags": ["programming-basics", "compiled-interpreted", "bytecode"]},
         ]},
        {"id": "pf.computer_basics", "label": "Computer Basics for Programmers",
         "description": "The hardware and encoding vocabulary every programmer needs.",
         "topics": [
            {"id": "pf.computer_basics.core", "label": "CPU, Memory & Encoding",
             "description": "CPU, RAM, storage, input/output devices, registers, cache memory, binary "
                            "numbers, bits and bytes, number systems, ASCII & Unicode.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.8,
             "prerequisites": ["pf.intro.core"],
             "tags": ["cpu", "memory", "binary", "encoding"]},
         ]},
        {"id": "pf.execution", "label": "Program Execution",
         "description": "How a program actually runs from source to process.",
         "topics": [
            {"id": "pf.execution.core", "label": "Compilers, Linkers & the Runtime",
             "description": "Compiler, interpreter, linker, loader, runtime, call stack (intro), heap "
                            "(intro), program lifecycle.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.9,
             "prerequisites": ["pf.computer_basics.core"],
             "tags": ["compiler", "interpreter", "call-stack"]},
         ]},
        {"id": "pf.problem_solving", "label": "Problem Solving",
         "description": "Computational thinking before any syntax is introduced.",
         "topics": [
            {"id": "pf.problem_solving.core", "label": "Computational Thinking",
             "description": "Breaking problems into steps, algorithms, flowcharts, pseudocode, decision "
                            "making, pattern recognition, abstraction.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.execution.core"],
             "tags": ["computational-thinking", "algorithms", "pseudocode"]},
         ]},
        {"id": "pf.variables", "label": "Variables",
         "description": "Naming, scope and lifetime of stored values.",
         "topics": [
            {"id": "pf.variables.core", "label": "Variables, Constants & Scope",
             "description": "Variables, constants, naming conventions, scope, lifetime.",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.8,
             "prerequisites": ["pf.problem_solving.core"],
             "tags": ["variables", "scope"]},
         ]},
        {"id": "pf.data_types", "label": "Data Types",
         "description": "What kinds of values a program can represent.",
         "topics": [
            {"id": "pf.data_types.core", "label": "Primitive & Non-Primitive Types",
             "description": "Primitive types, non-primitive types, type conversion, type casting.",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "prerequisites": ["pf.variables.core"],
             "tags": ["data-types", "type-casting"]},
         ]},
        {"id": "pf.operators", "label": "Operators",
         "description": "Combining values into expressions.",
         "topics": [
            {"id": "pf.operators.core", "label": "Arithmetic, Logical & Bitwise Operators",
             "description": "Arithmetic, assignment, comparison, logical, bitwise (intro), ternary, "
                            "operator precedence.",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.8,
             "prerequisites": ["pf.data_types.core"],
             "tags": ["operators", "precedence"]},
         ]},
        {"id": "pf.io", "label": "Input & Output",
         "description": "Getting data into and out of a program.",
         "topics": [
            {"id": "pf.io.core", "label": "Reading & Printing",
             "description": "Reading input, printing output, formatting output.",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.7,
             "prerequisites": ["pf.operators.core"],
             "tags": ["io"]},
         ]},
        {"id": "pf.control_flow", "label": "Control Flow",
         "description": "Directing execution with conditions and loops.",
         "topics": [
            {"id": "pf.control_flow.core", "label": "Conditionals & Loops",
             "description": "If, else, nested if, switch, loops, break, continue.",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.io.core"],
             "tags": ["control-flow", "loops"]},
         ]},
        {"id": "pf.functions", "label": "Functions",
         "description": "Structuring code into reusable, callable units.",
         "topics": [
            {"id": "pf.functions.core", "label": "Parameters, Returns & Pass Semantics",
             "description": "Why functions, parameters, arguments, return values, pass-by-value, "
                            "pass-by-reference (concept), recursion introduction.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["pf.control_flow.core"],
             "tags": ["functions", "pass-by-value"]},
         ]},
        {"id": "pf.arrays", "label": "Arrays",
         "description": "The first fixed-size, indexable data structure.",
         "topics": [
            {"id": "pf.arrays.core", "label": "Array Memory & Traversal",
             "description": "Why arrays, memory representation, indexing, traversal, multi-dimensional "
                            "arrays.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["pf.functions.core"],
             "tags": ["arrays", "indexing"]},
         ]},
        {"id": "pf.strings", "label": "Strings",
         "description": "Text as a sequence of characters.",
         "topics": [
            {"id": "pf.strings.core", "label": "Characters & String Operations",
             "description": "Characters, strings, string operations, immutable vs mutable (concept).",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.arrays.core"],
             "tags": ["strings", "immutability"]},
         ]},
        {"id": "pf.memory", "label": "Memory Fundamentals",
         "description": "Where values actually live at runtime.",
         "topics": [
            {"id": "pf.memory.core", "label": "Stack, Heap & References",
             "description": "Stack memory, heap memory, references, objects (concept), garbage "
                            "collection (concept).",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.2,
             "prerequisites": ["pf.strings.core"],
             "tags": ["stack", "heap", "garbage-collection"]},
         ]},
        {"id": "pf.error_handling", "label": "Error Handling",
         "description": "Recognizing and recovering from things going wrong.",
         "topics": [
            {"id": "pf.error_handling.core", "label": "Error Types & Debugging Basics",
             "description": "Syntax errors, runtime errors, logical errors, debugging basics.",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.memory.core"],
             "tags": ["errors", "debugging"]},
         ]},
        {"id": "pf.modular", "label": "Modular Programming",
         "description": "Organizing code so it stays maintainable as it grows.",
         "topics": [
            {"id": "pf.modular.core", "label": "Code Organization & Reuse",
             "description": "Code organization, reusability, separation of concerns.",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.9,
             "prerequisites": ["pf.error_handling.core"],
             "tags": ["modularity", "reusability"]},
         ]},
        {"id": "pf.recursion", "label": "Recursion",
         "description": "Functions that call themselves — the on-ramp to DSA recursion.",
         "topics": [
            {"id": "pf.recursion.core", "label": "Recursive Thinking & Base Cases",
             "description": "Call stack, base case, recursive thinking, tail recursion (concept).",
             "estimated_minutes": 35, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.3,
             "prerequisites": ["pf.modular.core"],
             "tags": ["recursion", "call-stack"]},
         ]},
        {"id": "pf.complexity", "label": "Time & Space Complexity",
         "description": "Reasoning about how algorithms scale.",
         "topics": [
            {"id": "pf.complexity.core", "label": "Big-O, Big-Omega & Big-Theta",
             "description": "Why complexity matters, Big-O notation, Big-Omega, Big-Theta, constant, "
                            "linear, logarithmic and quadratic time.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["pf.recursion.core"],
             "tags": ["big-o", "complexity"]},
         ]},
        {"id": "pf.searching", "label": "Searching Fundamentals",
         "description": "The first two search strategies, before DSA's pattern library.",
         "topics": [
            {"id": "pf.searching.core", "label": "Linear & Binary Search",
             "description": "Linear search, binary search (concept).",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["pf.complexity.core"],
             "tags": ["searching", "binary-search"]},
         ]},
        {"id": "pf.sorting", "label": "Sorting Fundamentals",
         "description": "The elementary O(n^2) sorts, before DSA's efficient sorts.",
         "topics": [
            {"id": "pf.sorting.core", "label": "Bubble, Selection & Insertion Sort",
             "description": "Why sorting, stability, in-place vs out-of-place, bubble sort, selection "
                            "sort, insertion sort.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["pf.searching.core"],
             "tags": ["sorting", "stability"]},
         ]},
        {"id": "pf.paradigms", "label": "Programming Paradigms",
         "description": "The major styles of structuring a program.",
         "topics": [
            {"id": "pf.paradigms.core", "label": "Procedural, OOP, Functional & Event-Driven",
             "description": "Procedural programming, object-oriented programming, functional "
                            "programming, declarative programming, event-driven programming.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["pf.sorting.core"],
             "tags": ["paradigms", "oop", "functional"]},
         ]},
        {"id": "pf.code_quality", "label": "Code Quality",
         "description": "What separates readable code from a code smell.",
         "topics": [
            {"id": "pf.code_quality.core", "label": "Readability, Naming & Refactoring Basics",
             "description": "Readable code, naming, comments, code smells, refactoring basics.",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.paradigms.core"],
             "tags": ["clean-code", "refactoring"]},
         ]},
        {"id": "pf.debugging", "label": "Debugging",
         "description": "Systematically finding why a program misbehaves.",
         "topics": [
            {"id": "pf.debugging.core", "label": "Breakpoints, Stack Traces & Logging",
             "description": "Breakpoints, stack trace, variable inspection, logging, assertions.",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.code_quality.core"],
             "tags": ["debugging", "logging"]},
         ]},
        {"id": "pf.testing", "label": "Testing Fundamentals",
         "description": "Verifying code behaves as intended.",
         "topics": [
            {"id": "pf.testing.core", "label": "Unit, Integration & Edge-Case Testing",
             "description": "Why testing, unit testing, integration testing, manual testing, edge "
                            "cases.",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.debugging.core"],
             "tags": ["testing", "unit-testing"]},
         ]},
        {"id": "pf.swe_basics", "label": "Software Engineering Basics",
         "description": "The team practices around writing code.",
         "topics": [
            {"id": "pf.swe_basics.core", "label": "SDLC, Version Control & Code Review",
             "description": "SDLC, version control, Git basics, code review, documentation.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.testing.core"],
             "tags": ["sdlc", "git"]},
         ]},
        {"id": "pf.engineering_mindset", "label": "Engineering Mindset",
         "description": "The heuristics that precede formal SOLID/LLD training.",
         "topics": [
            {"id": "pf.engineering_mindset.core", "label": "Clean Code, SOLID (Intro), DRY & KISS",
             "description": "Clean code principles, SOLID (introduction), DRY, KISS, YAGNI.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["pf.swe_basics.core"],
             "tags": ["solid", "dry", "kiss", "yagni"]},
         ]},
        {"id": "pf.design_thinking", "label": "Design Thinking",
         "description": "Weighing trade-offs before writing a line of code.",
         "topics": [
            {"id": "pf.design_thinking.core", "label": "Decomposition, Trade-offs & Maintainability",
             "description": "Problem decomposition, trade-offs, maintainability, scalability "
                            "(introduction).",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.engineering_mindset.core"],
             "tags": ["trade-offs", "maintainability"]},
         ]},
        {"id": "pf.performance_awareness", "label": "Performance Awareness",
         "description": "The resource costs every engineer should notice.",
         "topics": [
            {"id": "pf.performance_awareness.core", "label": "CPU, Memory, IO & Network Cost",
             "description": "CPU usage, memory usage, IO cost, network cost (introduction).",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.design_thinking.core"],
             "tags": ["performance", "cpu", "memory"]},
         ]},
        {"id": "pf.security_awareness", "label": "Security Awareness",
         "description": "The baseline security hygiene every engineer needs.",
         "topics": [
            {"id": "pf.security_awareness.core", "label": "Input Validation & Common Vulnerabilities",
             "description": "Input validation, safe coding practices, common vulnerabilities "
                            "(introduction).",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["pf.performance_awareness.core"],
             "tags": ["security", "input-validation"]},
         ]},
        {"id": "pf.professional_engineering", "label": "Professional Engineering",
         "description": "The capstone: writing code the way a production team expects. Completing "
                        "this module is the PF-101 exit gate every other subject's prerequisite "
                        "points at.",
         "topics": [
            {"id": "pf.professional_engineering.core", "label": "Production Code & Technical Communication",
             "description": "Writing production code, code reviews, technical communication, "
                            "documentation standards, continuous learning.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["pf.security_awareness.core"],
             "tags": ["production-code", "code-review"]},
         ]},
    ],
}


# ---------------------------------------------------------------------------
# DSA
# ---------------------------------------------------------------------------

DSA_TRACK = {
    "id": "dsa", "label": "Data Structures & Algorithms", "icon": "code2",
    "description": "The interview backbone. Master patterns, not problems.",
    "interview_importance": 5,
    "company_importance": ci(google=5, microsoft=5, atlassian=4, uber=5, adobe=4,
                              linkedin=5, stripe=4, salesforce=3, oracle=3,
                              phonepe=4, flipkart=5, paypal=4, goldman_sachs=5, zoho=4),
    "tags": ["algorithms", "problem-solving", "coding-round"],
    "modules": [
        # ---------------- Foundations ----------------
        {
            "id": "dsa.foundations", "label": "Foundations",
            "description": "Bread-and-butter primitives every interviewer expects fluency in.",
            "topics": [
                # Arrays
                {"id": "dsa.foundations.arrays", "label": "Arrays",
                 "description": "Contiguous memory workhorse — the base of ~40% of interview problems.",
                 "pattern": "arrays", "estimated_minutes": 120, "difficulty": "easy",
                 "interview_frequency": 5, "mastery_weight": 2.0,
                 "tags": ["arrays", "linear"],
                 "company_importance": ci(google=5, microsoft=5, atlassian=4, uber=5, linkedin=5, flipkart=5, goldman_sachs=5),
                 "learning_nodes": [
                    node("dsa.foundations.arrays.traversal", "Traversal & In-Place Ops",
                         "Reverse, rotate, and shift arrays with O(1) extra space.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=4, mastery_weight=1.0,
                         # Curriculum sync (2026) — DSA's canonical "Prerequisite Subjects":
                         # Programming Fundamentals, Java. This is DSA's entry leaf.
                         prerequisites=["pf.professional_engineering.core", "java.enterprise.core"],
                         problem_ids=["lc-189", "lc-27", "lc-283"], leetcode_tags=["array", "two-pointers"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.arrays.kadane", "Kadane's Algorithm",
                         "Maximum subarray sum via running max — O(n) DP-in-disguise.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=5, mastery_weight=1.5,
                         problem_ids=["lc-53", "lc-152"], leetcode_tags=["array", "dp"], neetcode_tags=["dp"]),
                    node("dsa.foundations.arrays.prefix_sum", "Prefix Sum",
                         "Precompute cumulative sums for O(1) range queries.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=4, mastery_weight=1.5,
                         prerequisites=["dsa.foundations.arrays.traversal"],
                         problem_ids=["lc-238", "lc-560", "lc-303"], leetcode_tags=["array", "prefix-sum"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.arrays.diff_array", "Difference Array",
                         "Range-update pattern used in interval and scheduling problems.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                         prerequisites=["dsa.foundations.arrays.prefix_sum"],
                         problem_ids=["lc-1109", "lc-1094"], leetcode_tags=["array", "prefix-sum"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.arrays.matrix", "2-D Matrix Basics",
                         "Row/col traversal, transpose, spiral, rotate-in-place.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.3,
                         problem_ids=["lc-48", "lc-54", "lc-73"], leetcode_tags=["matrix"], neetcode_tags=["arrays-hashing"]),
                 ]},
                # Hashing
                {"id": "dsa.foundations.hashing", "label": "Hashing",
                 "description": "Trade space for time — the #1 interview optimization pattern.",
                 "pattern": "hashing", "estimated_minutes": 90, "difficulty": "easy",
                 "interview_frequency": 5, "mastery_weight": 1.8,
                 "prerequisites": ["java.collections.hashmap"],
                 "tags": ["hashing", "hashmap", "hashset"],
                 "company_importance": ci(google=5, microsoft=5, atlassian=5, uber=5, linkedin=5, flipkart=5, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.foundations.hashing.frequency", "Frequency Counting",
                         "Count occurrences with a HashMap — the anagram/majority family.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=5, mastery_weight=1.2,
                         prerequisites=["dsa.foundations.arrays.traversal"],
                         problem_ids=["lc-217", "lc-49", "lc-242"], leetcode_tags=["hash-table"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.hashing.two_sum", "Two-Sum Family",
                         "Complement lookup in O(n) with a HashMap.",
                         difficulty="easy", estimated_minutes=15, interview_frequency=5, mastery_weight=1.5,
                         problem_ids=["lc-1", "lc-167"], leetcode_tags=["hash-table", "two-pointers"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.hashing.subarray_sum", "Subarray Sum Equals K",
                         "Prefix-sum + hashmap combo for count/length questions.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         prerequisites=["dsa.foundations.arrays.prefix_sum"],
                         problem_ids=["lc-560", "lc-974"], leetcode_tags=["hash-table", "prefix-sum"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.hashing.consecutive", "Longest Consecutive Sequence",
                         "Hash-set trick to skip non-start elements — O(n).",
                         difficulty="medium", estimated_minutes=25, interview_frequency=4, mastery_weight=1.3,
                         problem_ids=["lc-128"], leetcode_tags=["hash-table", "union-find"], neetcode_tags=["arrays-hashing"]),
                 ]},
                # Two Pointers
                {"id": "dsa.foundations.two_pointers", "label": "Two Pointers",
                 "description": "Opposite-end and same-direction pointer techniques on sorted data.",
                 "pattern": "two_pointers", "estimated_minutes": 90, "difficulty": "easy",
                 "interview_frequency": 5, "mastery_weight": 1.6,
                 "prerequisites": ["dsa.foundations.arrays.traversal"],
                 "tags": ["two-pointers"],
                 "company_importance": ci(google=5, microsoft=4, uber=5, linkedin=4, flipkart=5, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.foundations.two_pointers.palindrome", "Palindrome Check",
                         "Converge from both ends; O(1) space.",
                         difficulty="easy", estimated_minutes=15, interview_frequency=4, mastery_weight=1.0,
                         prerequisites=["dsa.foundations.arrays.traversal"],
                         problem_ids=["lc-125", "lc-680"], leetcode_tags=["two-pointers", "string"], neetcode_tags=["two-pointers"]),
                    node("dsa.foundations.two_pointers.k_sum", "3Sum / k-Sum",
                         "Sort + fix i + two-pointer — the canonical extension of Two-Sum.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=5, mastery_weight=1.6,
                         prerequisites=["dsa.foundations.hashing.two_sum"],
                         problem_ids=["lc-15", "lc-18", "lc-11"], leetcode_tags=["two-pointers", "sorting"], neetcode_tags=["two-pointers"]),
                    node("dsa.foundations.two_pointers.container", "Container With Most Water / Trapping Rain",
                         "Greedy pointer moves on height arrays.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.5,
                         problem_ids=["lc-11", "lc-42"], leetcode_tags=["two-pointers", "stack"], neetcode_tags=["two-pointers"]),
                    node("dsa.foundations.two_pointers.remove_dup", "In-Place Dedup / Move Zeros",
                         "Same-direction pointers for O(1)-space rewrites.",
                         difficulty="easy", estimated_minutes=15, interview_frequency=3, mastery_weight=1.0,
                         problem_ids=["lc-26", "lc-283", "lc-80"], leetcode_tags=["two-pointers"], neetcode_tags=["two-pointers"]),
                 ]},
                # Strings (new)
                {"id": "dsa.foundations.strings", "label": "Strings",
                 "description": "String scans, palindromic tricks, and encoding patterns.",
                 "pattern": "strings", "estimated_minutes": 90, "difficulty": "easy",
                 "interview_frequency": 4, "mastery_weight": 1.4,
                 "tags": ["strings"],
                 "company_importance": ci(google=4, microsoft=5, adobe=4, atlassian=4, flipkart=4, zoho=5),
                 "learning_nodes": [
                    node("dsa.foundations.strings.basics", "String Basics & Immutability",
                         "StringBuilder vs String, character arrays, common gotchas.",
                         difficulty="easy", estimated_minutes=15, interview_frequency=3, mastery_weight=0.8,
                         problem_ids=["lc-344", "lc-541"], leetcode_tags=["string"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.strings.anagram", "Anagram / Isomorphic",
                         "Frequency-array or hash-map equivalence checks.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=4, mastery_weight=1.2,
                         prerequisites=["dsa.foundations.hashing.frequency"],
                         problem_ids=["lc-242", "lc-205", "lc-49"], leetcode_tags=["hash-table", "string"], neetcode_tags=["arrays-hashing"]),
                    node("dsa.foundations.strings.palindromic_subs", "Palindromic Substrings",
                         "Expand-around-center in O(n²).",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         problem_ids=["lc-5", "lc-647"], leetcode_tags=["string", "dp"], neetcode_tags=["dp"]),
                    node("dsa.foundations.strings.encode_decode", "Encode / Decode Strings",
                         "Length-prefixed encoding — a common design-adjacent problem.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.1,
                         problem_ids=["lc-271", "lc-38"], leetcode_tags=["string", "design"], neetcode_tags=["arrays-hashing"]),
                 ]},
                # Bit Manipulation & Math
                {"id": "dsa.foundations.bit_math", "label": "Bit Manipulation & Math",
                 "description": "XOR tricks, bit masks, modular arithmetic and combinatorics for coding rounds.",
                 "pattern": "bit_math", "estimated_minutes": 90, "difficulty": "medium",
                 "interview_frequency": 3, "mastery_weight": 1.1,
                 "tags": ["bits", "math"],
                 "company_importance": ci(google=4, microsoft=3, goldman_sachs=4, adobe=3, uber=3),
                 "learning_nodes": [
                    node("dsa.foundations.bit_math.xor_tricks", "XOR Tricks",
                         "Find-the-unique/missing/duplicate in O(1) space.",
                         difficulty="medium", estimated_minutes=20, interview_frequency=4, mastery_weight=1.2,
                         problem_ids=["lc-136", "lc-268", "lc-260"], leetcode_tags=["bit-manipulation"], neetcode_tags=["bit-manipulation"]),
                    node("dsa.foundations.bit_math.bit_ops", "Bit Ops · Counting Bits",
                         "popcount, Brian Kernighan, bit DP.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.0,
                         problem_ids=["lc-191", "lc-338", "lc-190"], leetcode_tags=["bit-manipulation"], neetcode_tags=["bit-manipulation"]),
                    node("dsa.foundations.bit_math.pow_mod", "Fast Exponentiation & Mod",
                         "Binary exponentiation, modular inverse.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.0,
                         problem_ids=["lc-50", "lc-372"], leetcode_tags=["math", "recursion"], neetcode_tags=["math-geometry"]),
                    node("dsa.foundations.bit_math.gcd_lcm", "GCD / LCM / Number Theory",
                         "Euclid's algorithm and sieve basics.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=2, mastery_weight=0.8,
                         problem_ids=["lc-204", "lc-1071"], leetcode_tags=["math"], neetcode_tags=["math-geometry"]),
                 ]},
                # Recursion (RC1.3.5B — curriculum-foundation gap: every
                # backtracking/DP/tree topic assumes recursive fluency but
                # nothing taught it explicitly).
                {"id": "dsa.foundations.recursion", "label": "Recursion",
                 "description": "Base cases, call-stack mental model and recursion-to-iteration trade-offs — "
                                "the prerequisite mindset for trees, backtracking and DP.",
                 "pattern": "recursion", "estimated_minutes": 75, "difficulty": "easy",
                 "interview_frequency": 4, "mastery_weight": 1.3,
                 "tags": ["recursion", "foundations"],
                 "company_importance": ci(google=4, microsoft=4, atlassian=3, uber=3, flipkart=4),
                 "learning_nodes": [
                    node("dsa.foundations.recursion.basics", "Recursion Fundamentals",
                         "Base case, recursive case and the call-stack mental model.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=4, mastery_weight=1.1,
                         problem_ids=["lc-509", "lc-70"], leetcode_tags=["recursion", "math"], neetcode_tags=["dp"]),
                    node("dsa.foundations.recursion.recurrence", "Recurrence Relations & Recursion Tree",
                         "Modeling time complexity of recursive calls (T(n) = ...).",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                         prerequisites=["dsa.foundations.recursion.basics"],
                         problem_ids=["lc-50", "lc-779"], leetcode_tags=["recursion", "math"], neetcode_tags=["math-geometry"]),
                    node("dsa.foundations.recursion.to_iterative", "Recursion → Iteration & Memoization",
                         "Tail-call rewriting, explicit stack simulation and top-down caching — "
                         "the on-ramp to Dynamic Programming.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         prerequisites=["dsa.foundations.recursion.basics"],
                         problem_ids=["lc-509", "lc-206"], leetcode_tags=["recursion", "dp"], neetcode_tags=["dp"]),
                 ]},
                # Sorting (RC1.3.5B — curriculum-foundation gap: no dedicated
                # sorting topic despite greedy/heap/interval topics assuming it).
                {"id": "dsa.foundations.sorting", "label": "Sorting",
                 "description": "Comparison and non-comparison sorts, stability and when interviewers expect "
                                "you to implement one from scratch.",
                 "pattern": "sorting", "estimated_minutes": 90, "difficulty": "easy",
                 "interview_frequency": 4, "mastery_weight": 1.3,
                 "prerequisites": ["dsa.foundations.recursion.basics"],
                 "tags": ["sorting", "foundations"],
                 "company_importance": ci(google=4, microsoft=4, goldman_sachs=4, flipkart=4, oracle=4),
                 "learning_nodes": [
                    node("dsa.foundations.sorting.comparison", "Merge Sort & Quick Sort",
                         "Divide-and-conquer sorts, partitioning and worst-case analysis.",
                         difficulty="medium", estimated_minutes=35, interview_frequency=5, mastery_weight=1.6,
                         problem_ids=["lc-912", "lc-148"], leetcode_tags=["sorting", "divide-and-conquer"], neetcode_tags=["dp"]),
                    node("dsa.foundations.sorting.non_comparison", "Counting / Bucket / Radix Sort",
                         "Non-comparison sorts and when O(n log n) can be beaten.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=2, mastery_weight=1.1,
                         problem_ids=["lc-75", "lc-164"], leetcode_tags=["sorting"], neetcode_tags=["math-geometry"]),
                    node("dsa.foundations.sorting.stability_apps", "Stability & Applied Sorting",
                         "Stable-sort guarantees and sort-then-scan interview patterns.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=4, mastery_weight=1.2,
                         prerequisites=["dsa.foundations.sorting.comparison"],
                         problem_ids=["lc-56", "lc-179"], leetcode_tags=["sorting", "greedy"], neetcode_tags=["intervals"]),
                 ]},
            ],
        },
        # ---------------- Windows & Search ----------------
        {
            "id": "dsa.windows_search", "label": "Windows & Search",
            "description": "Sliding windows and binary search — the workhorses of medium-hard rounds.",
            "topics": [
                {"id": "dsa.windows.sliding_window", "label": "Sliding Window",
                 "description": "Fixed and variable window techniques for subarray/substring problems.",
                 "pattern": "sliding_window", "estimated_minutes": 150, "difficulty": "medium",
                 "interview_frequency": 5, "mastery_weight": 1.8,
                 "prerequisites": ["dsa.foundations.two_pointers", "dsa.foundations.hashing"],
                 "tags": ["sliding-window"],
                 "company_importance": ci(google=5, microsoft=5, uber=4, linkedin=5, atlassian=5, flipkart=5, goldman_sachs=4),
                 "subtopics": [
                    {"id": "dsa.windows.sliding_window.fixed", "label": "Fixed Window",
                     "description": "Windows of known size — precompute, slide, update in O(1).",
                     "learning_nodes": [
                        node("dsa.windows.sliding_window.fixed.max_avg", "Max Average Subarray",
                             "Classic fixed-window intro problem.",
                             difficulty="easy", estimated_minutes=15, interview_frequency=3, mastery_weight=1.0,
                             prerequisites=["dsa.foundations.two_pointers.palindrome", "dsa.foundations.hashing.frequency"],
                             problem_ids=["lc-643"], leetcode_tags=["sliding-window"], neetcode_tags=["sliding-window"]),
                        node("dsa.windows.sliding_window.fixed.max_sum_k", "Max Sum Subarray of Size K",
                             "Warm-up for variable window follow-ups.",
                             difficulty="easy", estimated_minutes=15, interview_frequency=3, mastery_weight=1.0,
                             prerequisites=["dsa.windows.sliding_window.fixed.max_avg"],
                             problem_ids=["lc-2461"], leetcode_tags=["sliding-window"], neetcode_tags=["sliding-window"]),
                     ]},
                    {"id": "dsa.windows.sliding_window.variable", "label": "Variable Window",
                     "description": "Grow/shrink dynamically based on a constraint.",
                     "learning_nodes": [
                        node("dsa.windows.sliding_window.variable.longest_unique", "Longest Substring w/o Repeat",
                             "Hashmap + shrinking window; canonical variable-window problem.",
                             difficulty="medium", estimated_minutes=25, interview_frequency=5, mastery_weight=1.5,
                             prerequisites=["dsa.windows.sliding_window.fixed.max_sum_k"],
                             problem_ids=["lc-3"], leetcode_tags=["sliding-window", "hash-table"], neetcode_tags=["sliding-window"]),
                        node("dsa.windows.sliding_window.variable.min_window", "Minimum Window Substring",
                             "Two hashmaps + `have/need` counter — hard-favorite.",
                             difficulty="hard", estimated_minutes=40, interview_frequency=5, mastery_weight=2.0,
                             prerequisites=["dsa.windows.sliding_window.variable.longest_unique"],
                             problem_ids=["lc-76"], leetcode_tags=["sliding-window", "hash-table"], neetcode_tags=["sliding-window"]),
                        node("dsa.windows.sliding_window.variable.anagrams", "Anagrams & Permutations",
                             "Fixed-length variable window with char-frequency match.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                             prerequisites=["dsa.windows.sliding_window.variable.longest_unique"],
                             problem_ids=["lc-438", "lc-567"], leetcode_tags=["sliding-window"], neetcode_tags=["sliding-window"]),
                        node("dsa.windows.sliding_window.variable.longest_ones", "Longest 1s / Consecutive Ones",
                             "Track allowed budget while sliding.",
                             difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                             prerequisites=["dsa.windows.sliding_window.variable.longest_unique"],
                             problem_ids=["lc-1004", "lc-424"], leetcode_tags=["sliding-window"], neetcode_tags=["sliding-window"]),
                     ]},
                    {"id": "dsa.windows.sliding_window.monotonic", "label": "Monotonic Deque Window",
                     "description": "Sliding window max/min via deque in O(n).",
                     "learning_nodes": [
                        node("dsa.windows.sliding_window.monotonic.max", "Sliding Window Maximum",
                             "Deque of indices holding a decreasing sequence.",
                             difficulty="hard", estimated_minutes=35, interview_frequency=4, mastery_weight=1.6,
                             prerequisites=["dsa.windows.sliding_window.fixed.max_sum_k"],
                             problem_ids=["lc-239", "lc-1438"], leetcode_tags=["sliding-window", "monotonic-queue"], neetcode_tags=["sliding-window"]),
                     ]},
                 ]},
                {"id": "dsa.search.binary_search", "label": "Binary Search",
                 "description": "Divide-and-conquer on sorted data and on answer spaces.",
                 "pattern": "binary_search", "estimated_minutes": 150, "difficulty": "medium",
                 "interview_frequency": 5, "mastery_weight": 1.8,
                 "prerequisites": ["dsa.foundations.arrays.traversal"],
                 "tags": ["binary-search"],
                 "company_importance": ci(google=5, microsoft=5, uber=4, linkedin=4, goldman_sachs=5, flipkart=4),
                 "learning_nodes": [
                    node("dsa.search.binary_search.basic", "Basic Binary Search",
                         "Templates for lower_bound / upper_bound.",
                         difficulty="easy", estimated_minutes=15, interview_frequency=4, mastery_weight=1.2,
                         problem_ids=["lc-704", "lc-35"], leetcode_tags=["binary-search"], neetcode_tags=["binary-search"]),
                    node("dsa.search.binary_search.rotated", "Rotated Sorted Array",
                         "Pivot detection + search across pivot.",
                         difficulty="medium", estimated_minutes=40, interview_frequency=5, mastery_weight=1.6,
                         problem_ids=["lc-33", "lc-153", "lc-81"], leetcode_tags=["binary-search"], neetcode_tags=["binary-search"]),
                    node("dsa.search.binary_search.on_answer", "Binary Search on Answer",
                         "Bisect the answer space when the problem is monotonic.",
                         difficulty="hard", estimated_minutes=45, interview_frequency=5, mastery_weight=2.0,
                         problem_ids=["lc-410", "lc-875", "lc-1011"], leetcode_tags=["binary-search"], neetcode_tags=["binary-search"]),
                    node("dsa.search.binary_search.matrix", "Binary Search on Matrix",
                         "Row/col monotone or flattened index search.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                         problem_ids=["lc-74", "lc-240"], leetcode_tags=["binary-search", "matrix"], neetcode_tags=["binary-search"]),
                    node("dsa.search.binary_search.median", "Median of Two Sorted Arrays",
                         "Partition-based O(log(min(n, m))) technique.",
                         difficulty="hard", estimated_minutes=45, interview_frequency=4, mastery_weight=1.8,
                         problem_ids=["lc-4"], leetcode_tags=["binary-search"], neetcode_tags=["binary-search"]),
                 ]},
            ],
        },
        # ---------------- Linear Structures ----------------
        {
            "id": "dsa.linear_structures", "label": "Linear Structures",
            "description": "Stacks, queues and linked lists — the primitives behind design questions.",
            "topics": [
                {"id": "dsa.linear.stack", "label": "Stack & Monotonic",
                 "description": "LIFO patterns and monotonic-stack tricks for next-greater/histogram.",
                 "pattern": "stack", "estimated_minutes": 120, "difficulty": "medium",
                 "interview_frequency": 4, "mastery_weight": 1.6,
                 "tags": ["stack", "monotonic-stack"],
                 "company_importance": ci(google=4, microsoft=4, atlassian=4, adobe=4, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.linear.stack.parens", "Balanced Parentheses",
                         "Bracket matching, minimum removes, valid strings.",
                         difficulty="easy", estimated_minutes=15, interview_frequency=4, mastery_weight=1.0,
                         problem_ids=["lc-20", "lc-921", "lc-1249"], leetcode_tags=["stack", "string"], neetcode_tags=["stack"]),
                    node("dsa.linear.stack.eval", "Expression / RPN Evaluation",
                         "Reverse Polish, basic calculator variants.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.2,
                         problem_ids=["lc-150", "lc-224", "lc-227"], leetcode_tags=["stack", "math"], neetcode_tags=["stack"]),
                    node("dsa.linear.stack.monotonic", "Monotonic Stack",
                         "Next-greater/less element and histogram problems.",
                         difficulty="hard", estimated_minutes=40, interview_frequency=5, mastery_weight=1.8,
                         problem_ids=["lc-739", "lc-84", "lc-496", "lc-503"], leetcode_tags=["stack", "monotonic-stack"], neetcode_tags=["stack"]),
                    node("dsa.linear.stack.min_stack", "Min Stack / Design Stack",
                         "O(1) getMin via auxiliary stack — a design classic.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.1,
                         problem_ids=["lc-155", "lc-716"], leetcode_tags=["stack", "design"], neetcode_tags=["stack"]),
                 ]},
                {"id": "dsa.linear.queue", "label": "Queues & Deques",
                 "description": "FIFO structures, circular queues and monotonic deques.",
                 "pattern": "queue", "estimated_minutes": 90, "difficulty": "medium",
                 "interview_frequency": 3, "mastery_weight": 1.2,
                 "tags": ["queue", "deque"],
                 "company_importance": ci(google=3, microsoft=4, uber=3, atlassian=3),
                 "learning_nodes": [
                    node("dsa.linear.queue.impl", "Implement Queue / Stack",
                         "Two-stack queue, circular buffer.",
                         difficulty="easy", estimated_minutes=20, interview_frequency=3, mastery_weight=1.0,
                         problem_ids=["lc-232", "lc-225", "lc-622"], leetcode_tags=["queue", "design"], neetcode_tags=["stack"]),
                    node("dsa.linear.queue.deque_apps", "Deque Applications",
                         "Sliding window max, first-negative in window.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                         prerequisites=["dsa.windows.sliding_window.monotonic"],
                         problem_ids=["lc-239"], leetcode_tags=["monotonic-queue"], neetcode_tags=["sliding-window"]),
                 ]},
                {"id": "dsa.linear.linked_list", "label": "Linked List",
                 "description": "Pointer manipulation and cycle detection idioms.",
                 "pattern": "linked_list", "estimated_minutes": 150, "difficulty": "medium",
                 "interview_frequency": 4, "mastery_weight": 1.6,
                 "prerequisites": ["dsa.foundations.two_pointers"],
                 "tags": ["linked-list", "two-pointers"],
                 "company_importance": ci(google=4, microsoft=5, adobe=5, atlassian=4, goldman_sachs=4, flipkart=4),
                 "learning_nodes": [
                    node("dsa.linear.linked_list.reverse", "Reverse & Merge",
                         "Iterative + recursive reverse; merge two sorted lists.",
                         difficulty="easy", estimated_minutes=25, interview_frequency=5, mastery_weight=1.4,
                         problem_ids=["lc-206", "lc-21", "lc-92"], leetcode_tags=["linked-list", "recursion"], neetcode_tags=["linked-list"]),
                    node("dsa.linear.linked_list.fast_slow", "Fast / Slow Pointers",
                         "Cycle detection (Floyd) and mid-node identification.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=5, mastery_weight=1.5,
                         problem_ids=["lc-141", "lc-142", "lc-876"], leetcode_tags=["linked-list", "two-pointers"], neetcode_tags=["linked-list"]),
                    node("dsa.linear.linked_list.reorder", "Reorder / Palindrome / Rotate",
                         "Split + reverse + interleave — the recipe for many hards.",
                         difficulty="medium", estimated_minutes=35, interview_frequency=4, mastery_weight=1.5,
                         problem_ids=["lc-143", "lc-234", "lc-61"], leetcode_tags=["linked-list"], neetcode_tags=["linked-list"]),
                    node("dsa.linear.linked_list.lru", "LRU Cache",
                         "HashMap + doubly-linked-list — the interview darling.",
                         difficulty="hard", estimated_minutes=45, interview_frequency=5, mastery_weight=2.0,
                         prerequisites=["dsa.foundations.hashing", "dsa.linear.linked_list.reverse"],
                         problem_ids=["lc-146", "lc-460"], leetcode_tags=["linked-list", "design", "hash-table"], neetcode_tags=["linked-list"]),
                 ]},
            ],
        },
        # ---------------- Trees & Graphs ----------------
        {
            "id": "dsa.trees_graphs", "label": "Trees & Graphs",
            "description": "Hierarchical and networked structures — traversal, search and shortest-path.",
            "topics": [
                {"id": "dsa.trees.binary_tree", "label": "Binary Trees",
                 "description": "Recursive thinking and DFS/BFS templates on binary trees.",
                 "pattern": "trees", "estimated_minutes": 180, "difficulty": "medium",
                 "interview_frequency": 5, "mastery_weight": 1.8,
                 "prerequisites": ["dsa.foundations.recursion.basics"],
                 "tags": ["tree", "dfs", "bfs"],
                 "company_importance": ci(google=5, microsoft=5, uber=4, linkedin=4, atlassian=5, adobe=4, flipkart=5),
                 "subtopics": [
                    {"id": "dsa.trees.traversal", "label": "Traversal",
                     "description": "Inorder / preorder / postorder / level-order recipes.",
                     "learning_nodes": [
                        node("dsa.trees.traversal.level_order", "Level Order (BFS)",
                             "Queue-based traversal by depth.",
                             difficulty="medium", estimated_minutes=25, interview_frequency=5, mastery_weight=1.4,
                             problem_ids=["lc-102", "lc-107", "lc-199"], leetcode_tags=["tree", "bfs"], neetcode_tags=["trees"]),
                        node("dsa.trees.traversal.depth", "Depth & Comparison",
                             "Max/min depth, same-tree, symmetric-tree.",
                             difficulty="easy", estimated_minutes=20, interview_frequency=4, mastery_weight=1.2,
                             problem_ids=["lc-104", "lc-100", "lc-101"], leetcode_tags=["tree", "dfs"], neetcode_tags=["trees"]),
                        node("dsa.trees.traversal.iterative", "Iterative Traversal",
                             "Stack-based DFS + Morris traversal.",
                             difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.1,
                             problem_ids=["lc-94", "lc-144", "lc-145"], leetcode_tags=["tree", "stack"], neetcode_tags=["trees"]),
                        node("dsa.trees.traversal.diameter", "Diameter & Path Sum",
                             "Post-order height + global max.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.5,
                             problem_ids=["lc-543", "lc-124", "lc-687"], leetcode_tags=["tree", "dfs"], neetcode_tags=["trees"]),
                     ]},
                    {"id": "dsa.trees.bst", "label": "Binary Search Tree",
                     "description": "Ordered-tree invariant enables O(log n) search.",
                     "learning_nodes": [
                        node("dsa.trees.bst.validate", "Validate BST",
                             "Inorder monotonicity or min/max recursion.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                             problem_ids=["lc-98"], leetcode_tags=["tree", "bst"], neetcode_tags=["trees"]),
                        node("dsa.trees.bst.kth_smallest", "Kth Smallest",
                             "Inorder traversal with early exit.",
                             difficulty="medium", estimated_minutes=25, interview_frequency=4, mastery_weight=1.3,
                             problem_ids=["lc-230"], leetcode_tags=["tree", "bst"], neetcode_tags=["trees"]),
                        node("dsa.trees.bst.lca", "Lowest Common Ancestor",
                             "BST split-point + generic-tree LCA.",
                             difficulty="medium", estimated_minutes=25, interview_frequency=5, mastery_weight=1.5,
                             problem_ids=["lc-235", "lc-236"], leetcode_tags=["tree", "bst"], neetcode_tags=["trees"]),
                        node("dsa.trees.bst.serialize", "Serialize / Deserialize",
                             "Preorder-null encoding — a hard-favorite design problem.",
                             difficulty="hard", estimated_minutes=40, interview_frequency=4, mastery_weight=1.7,
                             problem_ids=["lc-297", "lc-449"], leetcode_tags=["tree", "design"], neetcode_tags=["trees"]),
                     ]},
                 ]},
                {"id": "dsa.trees.tries", "label": "Tries",
                 "description": "Prefix-tree structure for word search and autocomplete.",
                 "pattern": "trie", "estimated_minutes": 90, "difficulty": "medium",
                 "interview_frequency": 3, "mastery_weight": 1.3,
                 "prerequisites": ["dsa.trees.binary_tree"],
                 "tags": ["trie", "design"],
                 "company_importance": ci(google=4, microsoft=4, atlassian=3, adobe=3, linkedin=3),
                 "learning_nodes": [
                    node("dsa.trees.tries.implement", "Implement Trie",
                         "Insert / search / prefix in O(L).",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         problem_ids=["lc-208"], leetcode_tags=["trie", "design"], neetcode_tags=["tries"]),
                    node("dsa.trees.tries.word_search", "Word Search II",
                         "Trie + backtracking on a grid — hard-favorite combo.",
                         difficulty="hard", estimated_minutes=45, interview_frequency=3, mastery_weight=1.6,
                         prerequisites=["dsa.backtracking.core"],
                         problem_ids=["lc-212", "lc-79"], leetcode_tags=["trie", "backtracking"], neetcode_tags=["tries"]),
                    node("dsa.trees.tries.autocomplete", "Autocomplete / Search Suggestions",
                         "System-design flavored trie problem.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.2,
                         problem_ids=["lc-1268", "lc-642"], leetcode_tags=["trie", "design"], neetcode_tags=["tries"]),
                 ]},
                {"id": "dsa.trees.graphs", "label": "Graphs · BFS & DFS",
                 "description": "Grid + adjacency-list traversal, cycle detection, connectivity.",
                 "pattern": "graphs", "estimated_minutes": 210, "difficulty": "medium",
                 "interview_frequency": 5, "mastery_weight": 2.0,
                 "prerequisites": ["dsa.trees.binary_tree", "dsa.linear.queue"],
                 "tags": ["graph", "bfs", "dfs"],
                 "company_importance": ci(google=5, microsoft=5, uber=5, linkedin=5, atlassian=5, stripe=4, flipkart=5, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.trees.graphs.islands", "Grid Islands · BFS / DFS",
                         "Connected components on a matrix.",
                         difficulty="medium", estimated_minutes=35, interview_frequency=5, mastery_weight=1.7,
                         problem_ids=["lc-200", "lc-994", "lc-695", "lc-130"], leetcode_tags=["dfs", "bfs", "matrix"], neetcode_tags=["graphs"]),
                    node("dsa.trees.graphs.clone", "Graph Clone / Traversal",
                         "HashMap + DFS/BFS clone template.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         problem_ids=["lc-133"], leetcode_tags=["graph", "hash-table"], neetcode_tags=["graphs"]),
                    node("dsa.trees.graphs.topo", "Topological Sort",
                         "Kahn's BFS + DFS post-order; cycle detection in DAGs.",
                         difficulty="medium", estimated_minutes=35, interview_frequency=5, mastery_weight=1.7,
                         problem_ids=["lc-207", "lc-210", "lc-269"], leetcode_tags=["graph", "topological-sort"], neetcode_tags=["graphs"]),
                    node("dsa.trees.graphs.shortest_path", "Shortest Path · Dijkstra",
                         "Weighted single-source shortest path.",
                         difficulty="hard", estimated_minutes=45, interview_frequency=4, mastery_weight=1.8,
                         prerequisites=["dsa.heaps.priority_queue"],
                         problem_ids=["lc-743", "lc-787", "lc-1631"], leetcode_tags=["graph", "shortest-path"], neetcode_tags=["advanced-graphs"]),
                    node("dsa.trees.graphs.bellman", "Bellman-Ford / Floyd-Warshall",
                         "Negative edges and all-pairs shortest paths.",
                         difficulty="hard", estimated_minutes=35, interview_frequency=2, mastery_weight=1.4,
                         problem_ids=["lc-787", "lc-1334"], leetcode_tags=["graph"], neetcode_tags=["advanced-graphs"]),
                    node("dsa.trees.graphs.mst", "Minimum Spanning Tree",
                         "Kruskal (union-find) and Prim (heap).",
                         difficulty="hard", estimated_minutes=40, interview_frequency=2, mastery_weight=1.4,
                         prerequisites=["dsa.advanced.union_find.core"],
                         problem_ids=["lc-1584", "lc-1489"], leetcode_tags=["graph", "mst"], neetcode_tags=["advanced-graphs"]),
                    node("dsa.trees.graphs.bipartite", "Bipartite / Coloring",
                         "2-color BFS on undirected graphs.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                         problem_ids=["lc-785", "lc-886"], leetcode_tags=["graph", "bfs"], neetcode_tags=["graphs"]),
                 ]},
            ],
        },
        # ---------------- Heaps & Priority ----------------
        {
            "id": "dsa.priority", "label": "Heaps & Priority",
            "description": "Heap-based selection, streaming stats and scheduling problems.",
            "topics": [
                {"id": "dsa.heaps.priority_queue", "label": "Heaps & Priority Queues",
                 "description": "Binary heap fundamentals and PQ patterns.",
                 "pattern": "heap", "estimated_minutes": 180, "difficulty": "medium",
                 "interview_frequency": 4, "mastery_weight": 1.7,
                 "prerequisites": ["dsa.trees.binary_tree", "java.collections.comparator", "dsa.foundations.sorting.comparison"],
                 "tags": ["heap", "priority-queue"],
                 "company_importance": ci(google=5, microsoft=4, uber=5, linkedin=4, atlassian=4, stripe=4, flipkart=4, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.heaps.kth", "Kth Largest / Smallest",
                         "Size-k min-heap for streams.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=5, mastery_weight=1.5,
                         problem_ids=["lc-215", "lc-703"], leetcode_tags=["heap", "sorting"], neetcode_tags=["heap-priority-queue"]),
                    node("dsa.heaps.k_closest", "K Closest Points",
                         "Bounded max-heap of size K on distance.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=4, mastery_weight=1.3,
                         problem_ids=["lc-973"], leetcode_tags=["heap", "sorting"], neetcode_tags=["heap-priority-queue"]),
                    node("dsa.heaps.merge_k", "Merge K Sorted Lists",
                         "Heap of head pointers.",
                         difficulty="hard", estimated_minutes=35, interview_frequency=5, mastery_weight=1.7,
                         prerequisites=["dsa.linear.linked_list.reverse"],
                         problem_ids=["lc-23", "lc-378"], leetcode_tags=["heap", "linked-list"], neetcode_tags=["heap-priority-queue"]),
                    node("dsa.heaps.two_heaps", "Two-Heap Median (Streaming)",
                         "Balanced max/min heap pair.",
                         difficulty="hard", estimated_minutes=40, interview_frequency=4, mastery_weight=1.8,
                         problem_ids=["lc-295", "lc-480"], leetcode_tags=["heap", "design"], neetcode_tags=["heap-priority-queue"]),
                    node("dsa.heaps.task_scheduler", "Task Scheduler",
                         "Greedy heap for cool-down scheduling.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.3,
                         problem_ids=["lc-621", "lc-1834"], leetcode_tags=["heap", "greedy"], neetcode_tags=["heap-priority-queue"]),
                    node("dsa.heaps.reorganize", "Reorganize String / Rearrange",
                         "Max-heap of frequencies + placement.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.3,
                         problem_ids=["lc-767", "lc-1054"], leetcode_tags=["heap", "greedy"], neetcode_tags=["heap-priority-queue"]),
                 ]},
            ],
        },
        # ---------------- DP & Backtracking ----------------
        {
            "id": "dsa.dp_backtracking", "label": "DP, Backtracking & Greedy",
            "description": "Overlapping-subproblem optimization and combinatorial search.",
            "topics": [
                {"id": "dsa.dp.core", "label": "Dynamic Programming",
                 "description": "Bottom-up, top-down memo, and state-compression templates.",
                 "pattern": "dp", "estimated_minutes": 300, "difficulty": "hard",
                 "interview_frequency": 5, "mastery_weight": 2.2,
                 "prerequisites": ["dsa.foundations.arrays", "dsa.foundations.recursion.to_iterative"],
                 "tags": ["dp"],
                 "company_importance": ci(google=5, microsoft=5, atlassian=4, uber=4, linkedin=4, adobe=4, goldman_sachs=5, flipkart=4),
                 "subtopics": [
                    {"id": "dsa.dp.1d", "label": "1D DP",
                     "description": "Single-dimension state — Fibonacci flavor.",
                     "learning_nodes": [
                        node("dsa.dp.1d.climbing", "Climbing Stairs",
                             "Canonical DP intro — Fibonacci with steps.",
                             difficulty="easy", estimated_minutes=15, interview_frequency=4, mastery_weight=1.0,
                             problem_ids=["lc-70", "lc-746"], leetcode_tags=["dp"], neetcode_tags=["dp"]),
                        node("dsa.dp.1d.house_robber", "House Robber I & II",
                             "Pick / skip decision with a circular variant.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                             problem_ids=["lc-198", "lc-213"], leetcode_tags=["dp"], neetcode_tags=["dp"]),
                        node("dsa.dp.1d.decode", "Decode Ways",
                             "State transitions with validity checks.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.2,
                             problem_ids=["lc-91"], leetcode_tags=["dp"], neetcode_tags=["dp"]),
                        node("dsa.dp.1d.jump", "Jump Game / Word Break",
                             "Reachability DP + greedy hybrid.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                             problem_ids=["lc-55", "lc-45", "lc-139"], leetcode_tags=["dp", "greedy"], neetcode_tags=["dp"]),
                     ]},
                    {"id": "dsa.dp.unbounded", "label": "Unbounded Knapsack",
                     "description": "Reuse-allowed knapsack — coin change family.",
                     "learning_nodes": [
                        node("dsa.dp.unbounded.coin_change", "Coin Change I & II",
                             "Min-coins vs count-ways with unbounded picks.",
                             difficulty="medium", estimated_minutes=40, interview_frequency=5, mastery_weight=1.8,
                             problem_ids=["lc-322", "lc-518"], leetcode_tags=["dp", "knapsack"], neetcode_tags=["dp"]),
                     ]},
                    {"id": "dsa.dp.2d", "label": "2D DP",
                     "description": "Two-string / grid tabulation problems.",
                     "learning_nodes": [
                        node("dsa.dp.2d.lcs", "Longest Common Subsequence",
                             "Classic O(mn) tabulation.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=5, mastery_weight=1.6,
                             problem_ids=["lc-1143", "lc-583"], leetcode_tags=["dp", "string"], neetcode_tags=["dp"]),
                        node("dsa.dp.2d.edit_distance", "Edit Distance",
                             "Insert / delete / replace transitions.",
                             difficulty="hard", estimated_minutes=40, interview_frequency=4, mastery_weight=1.8,
                             problem_ids=["lc-72"], leetcode_tags=["dp", "string"], neetcode_tags=["dp"]),
                        node("dsa.dp.2d.grid", "Unique Paths / Min Path Sum",
                             "Grid tabulation with obstacle variants.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                             problem_ids=["lc-62", "lc-63", "lc-64"], leetcode_tags=["dp", "matrix"], neetcode_tags=["dp"]),
                        node("dsa.dp.2d.regex", "Regex / Wildcard Matching",
                             "State machine expressed as DP.",
                             difficulty="hard", estimated_minutes=45, interview_frequency=3, mastery_weight=1.6,
                             problem_ids=["lc-10", "lc-44"], leetcode_tags=["dp", "string"], neetcode_tags=["dp"]),
                     ]},
                    {"id": "dsa.dp.lis", "label": "LIS & Sequence DP",
                     "description": "Longest increasing subsequence and generalizations.",
                     "learning_nodes": [
                        node("dsa.dp.lis.core", "Longest Increasing Subsequence",
                             "O(n²) DP and O(n log n) patience trick.",
                             difficulty="medium", estimated_minutes=35, interview_frequency=4, mastery_weight=1.6,
                             problem_ids=["lc-300", "lc-673"], leetcode_tags=["dp", "binary-search"], neetcode_tags=["dp"]),
                        node("dsa.dp.lis.russian_doll", "Russian Doll Envelopes",
                             "2-D LIS via sort + LIS.",
                             difficulty="hard", estimated_minutes=30, interview_frequency=2, mastery_weight=1.3,
                             problem_ids=["lc-354"], leetcode_tags=["dp", "sorting"], neetcode_tags=["dp"]),
                     ]},
                    {"id": "dsa.dp.interval", "label": "Interval DP",
                     "description": "DP over sub-intervals of an array.",
                     "learning_nodes": [
                        node("dsa.dp.interval.balloons", "Burst Balloons / Matrix Chain",
                             "Range DP with pivot selection.",
                             difficulty="hard", estimated_minutes=45, interview_frequency=2, mastery_weight=1.5,
                             problem_ids=["lc-312", "lc-1039"], leetcode_tags=["dp"], neetcode_tags=["dp"]),
                        node("dsa.dp.interval.stone", "Stone Game / Predict the Winner",
                             "Adversarial range DP.",
                             difficulty="medium", estimated_minutes=30, interview_frequency=2, mastery_weight=1.2,
                             problem_ids=["lc-486", "lc-877"], leetcode_tags=["dp", "game-theory"], neetcode_tags=["dp"]),
                     ]},
                    {"id": "dsa.dp.bitmask", "label": "Bitmask DP",
                     "description": "Compact state representation over subsets.",
                     "learning_nodes": [
                        node("dsa.dp.bitmask.tsp", "Travelling Salesman (Bitmask)",
                             "O(n² · 2ⁿ) exact TSP.",
                             difficulty="hard", estimated_minutes=40, interview_frequency=2, mastery_weight=1.3,
                             problem_ids=["lc-943", "lc-847"], leetcode_tags=["dp", "bitmask"], neetcode_tags=["dp"]),
                     ]},
                 ]},
                {"id": "dsa.backtracking.core", "label": "Backtracking",
                 "description": "Recursive combinatorial search with pruning.",
                 "pattern": "backtracking", "estimated_minutes": 150, "difficulty": "hard",
                 "interview_frequency": 4, "mastery_weight": 1.7,
                 "prerequisites": ["dsa.trees.binary_tree", "dsa.foundations.recursion.basics"],
                 "tags": ["backtracking", "recursion"],
                 "company_importance": ci(google=4, microsoft=4, atlassian=4, adobe=4, uber=3, flipkart=4),
                 "learning_nodes": [
                    node("dsa.backtracking.subsets", "Subsets & Permutations",
                         "Include/exclude and swap-in-place templates.",
                         difficulty="medium", estimated_minutes=35, interview_frequency=5, mastery_weight=1.5,
                         problem_ids=["lc-78", "lc-46", "lc-90", "lc-47"], leetcode_tags=["backtracking"], neetcode_tags=["backtracking"]),
                    node("dsa.backtracking.combinations", "Combination Sum",
                         "Choose-with-repeat plus pruning.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         problem_ids=["lc-39", "lc-40", "lc-216"], leetcode_tags=["backtracking"], neetcode_tags=["backtracking"]),
                    node("dsa.backtracking.word_search", "Word Search",
                         "Grid DFS with visited-mask.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         problem_ids=["lc-79"], leetcode_tags=["backtracking", "matrix"], neetcode_tags=["backtracking"]),
                    node("dsa.backtracking.n_queens", "N-Queens / Sudoku",
                         "Constraint-satisfaction with bitmask pruning.",
                         difficulty="hard", estimated_minutes=45, interview_frequency=2, mastery_weight=1.4,
                         problem_ids=["lc-51", "lc-37"], leetcode_tags=["backtracking", "matrix"], neetcode_tags=["backtracking"]),
                    node("dsa.backtracking.partitioning", "Palindrome Partitioning",
                         "Split-string backtracking with palindrome check.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.3,
                         problem_ids=["lc-131", "lc-93"], leetcode_tags=["backtracking", "string"], neetcode_tags=["backtracking"]),
                 ]},
                {"id": "dsa.greedy.core", "label": "Greedy",
                 "description": "Locally-optimal choices leading to global optima.",
                 "pattern": "greedy", "estimated_minutes": 120, "difficulty": "medium",
                 "interview_frequency": 4, "mastery_weight": 1.4,
                 "prerequisites": ["dsa.foundations.sorting.comparison"],
                 "tags": ["greedy"],
                 "company_importance": ci(google=4, microsoft=4, uber=4, adobe=3, atlassian=4, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.greedy.intervals", "Interval Scheduling",
                         "Sort-by-end and pick-first pattern.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=5, mastery_weight=1.6,
                         problem_ids=["lc-435", "lc-56", "lc-57", "lc-252", "lc-253"], leetcode_tags=["greedy", "sorting"], neetcode_tags=["intervals"]),
                    node("dsa.greedy.jump", "Jump Game (Greedy Variant)",
                         "Farthest-reachable optimization.",
                         difficulty="medium", estimated_minutes=20, interview_frequency=4, mastery_weight=1.3,
                         problem_ids=["lc-55", "lc-45"], leetcode_tags=["greedy"], neetcode_tags=["greedy"]),
                    node("dsa.greedy.gas", "Gas Station / Candy",
                         "Prefix accumulation + greedy reset.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.2,
                         problem_ids=["lc-134", "lc-135"], leetcode_tags=["greedy"], neetcode_tags=["greedy"]),
                    node("dsa.greedy.huffman", "Huffman / Merge Stones",
                         "Repeated-min heap-driven greedy.",
                         difficulty="hard", estimated_minutes=30, interview_frequency=2, mastery_weight=1.1,
                         prerequisites=["dsa.heaps.priority_queue"],
                         problem_ids=["lc-1000", "lc-1167"], leetcode_tags=["greedy", "heap"], neetcode_tags=["heap-priority-queue"]),
                 ]},
            ],
        },
        # ---------------- Advanced ----------------
        {
            "id": "dsa.advanced", "label": "Advanced Structures",
            "description": "Union-Find, Segment Tree and Fenwick — the last-mile interview edge.",
            "topics": [
                {"id": "dsa.advanced.union_find", "label": "Union-Find (DSU)",
                 "description": "Disjoint-set with path compression + union by rank.",
                 "pattern": "union_find", "estimated_minutes": 120, "difficulty": "hard",
                 "interview_frequency": 3, "mastery_weight": 1.5,
                 "prerequisites": ["dsa.trees.graphs"],
                 "tags": ["union-find", "graph"],
                 "company_importance": ci(google=4, microsoft=3, uber=4, stripe=4, atlassian=3, linkedin=3),
                 "learning_nodes": [
                    node("dsa.advanced.union_find.core", "DSU Fundamentals",
                         "Find, union, path-compression, near-O(1) amortized.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=4, mastery_weight=1.4,
                         problem_ids=["lc-547", "lc-323"], leetcode_tags=["union-find"], neetcode_tags=["advanced-graphs"]),
                    node("dsa.advanced.union_find.redundant", "Redundant Connection",
                         "Detect cycle formation in an incrementally built graph.",
                         difficulty="medium", estimated_minutes=25, interview_frequency=3, mastery_weight=1.3,
                         problem_ids=["lc-684", "lc-685"], leetcode_tags=["union-find"], neetcode_tags=["advanced-graphs"]),
                    node("dsa.advanced.union_find.accounts", "Accounts Merge / Similar Strings",
                         "Grouping equivalence classes.",
                         difficulty="medium", estimated_minutes=30, interview_frequency=3, mastery_weight=1.3,
                         problem_ids=["lc-721", "lc-839"], leetcode_tags=["union-find", "dfs"], neetcode_tags=["advanced-graphs"]),
                 ]},
                {"id": "dsa.advanced.segment_tree", "label": "Segment Tree / Fenwick",
                 "description": "Range queries and point updates in O(log n).",
                 "pattern": "segment_tree", "estimated_minutes": 120, "difficulty": "hard",
                 "interview_frequency": 2, "mastery_weight": 1.3,
                 "prerequisites": ["dsa.foundations.arrays.prefix_sum"],
                 "tags": ["segment-tree", "fenwick"],
                 "company_importance": ci(google=3, microsoft=3, uber=3, goldman_sachs=4),
                 "learning_nodes": [
                    node("dsa.advanced.segment_tree.range_sum", "Range Sum Query · Mutable",
                         "Segment tree or Fenwick tree for updates.",
                         difficulty="hard", estimated_minutes=40, interview_frequency=2, mastery_weight=1.3,
                         problem_ids=["lc-307", "lc-315"], leetcode_tags=["segment-tree", "fenwick"], neetcode_tags=["advanced-graphs"]),
                    node("dsa.advanced.segment_tree.count_smaller", "Count of Smaller Numbers After Self",
                         "Fenwick tree with coordinate compression.",
                         difficulty="hard", estimated_minutes=40, interview_frequency=2, mastery_weight=1.2,
                         problem_ids=["lc-315"], leetcode_tags=["fenwick", "divide-and-conquer"], neetcode_tags=["advanced-graphs"]),
                 ]},
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# JAVA
# ---------------------------------------------------------------------------

JAVA_TRACK = {
    "id": "java", "label": "Java", "icon": "coffee",
    "description": "Deep language + JVM mastery for backend and platform interviews.",
    "interview_importance": 4,
    "company_importance": ci(google=3, microsoft=4, atlassian=4, uber=3, adobe=4, linkedin=4,
                              stripe=4, salesforce=5, oracle=5, phonepe=4, flipkart=4,
                              paypal=4, goldman_sachs=5, zoho=5),
    "tags": ["java", "jvm", "backend"],
    "modules": [
        # RC1.3.5B — Curriculum-foundation gap: the Java track previously
        # started at OOP, assuming programming fluency that was never
        # actually taught anywhere in PrepOS. This module is the on-ramp.
        {"id": "java.basics", "label": "Programming Basics",
         "description": "The absolute-beginner on-ramp: syntax, variables, control flow and classes — "
                        "before OOP, Collections or the JVM assume any of it.",
         "topics": [
            {"id": "java.basics.programming_intro", "label": "What Is Programming? The JVM",
             "description": "Source → bytecode → JVM execution; compiling and running a first Java program.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.8,
             # Curriculum sync (2026) — Java's canonical "Prerequisite Subjects": Programming
             # Fundamentals. This is Java's entry leaf.
             "prerequisites": ["pf.professional_engineering.core"],
             "tags": ["basics", "jvm"]},
            {"id": "java.basics.variables_datatypes", "label": "Variables & Data Types",
             "description": "Primitives vs references, literals, type widening/narrowing, arrays as a "
                            "reference type.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "prerequisites": ["java.basics.programming_intro"],
             "tags": ["basics", "variables"]},
            {"id": "java.basics.operators", "label": "Operators & Expressions",
             "description": "Arithmetic, relational, logical, bitwise and ternary operators; precedence.",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.7,
             "prerequisites": ["java.basics.variables_datatypes"],
             "tags": ["basics", "operators"]},
            {"id": "java.basics.control_flow", "label": "Control Flow",
             "description": "if/else, switch, for/while/do-while loops, break/continue.",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 1, "mastery_weight": 0.8,
             "prerequisites": ["java.basics.operators"],
             "tags": ["basics", "control-flow"]},
            {"id": "java.basics.methods", "label": "Methods & Parameters",
             "description": "Method signatures, overloading, pass-by-value semantics, varargs.",
             "estimated_minutes": 25, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "prerequisites": ["java.basics.control_flow"],
             "tags": ["basics", "methods"]},
            {"id": "java.basics.classes_objects", "label": "Classes, Objects & Constructors",
             "description": "Defining a class, instantiation, the `this` reference, constructor chaining — "
                            "the direct bridge into OOP Foundations.",
             "estimated_minutes": 35, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["java.basics.methods"],
             "tags": ["basics", "classes", "constructors"]},
         ]},
        {"id": "java.oop", "label": "OOP Foundations",
         "description": "The four pillars and object identity semantics.",
         "topics": [
            {"id": "java.oop.equals_hashcode", "label": "equals() & hashCode()",
             "description": "Contract, symmetry, and use inside HashMap.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.5,
             "prerequisites": ["java.basics.classes_objects"],
             "tags": ["oop", "hashmap"],
             "company_importance": ci(oracle=5, salesforce=5, goldman_sachs=5, phonepe=4, zoho=5)},
            {"id": "java.oop.inheritance", "label": "Inheritance & Polymorphism",
             "description": "Overriding, dynamic dispatch, diamond problem.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["java.basics.classes_objects"],
             "tags": ["oop", "polymorphism"],
             "company_importance": ci(oracle=5, salesforce=4, adobe=4, phonepe=4, zoho=5)},
            {"id": "java.oop.abstraction", "label": "Abstract Classes & Interfaces",
             "description": "When to pick which; default & static methods on interfaces.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.2,
             "prerequisites": ["java.basics.classes_objects"],
             "tags": ["oop", "interface"],
             "company_importance": ci(oracle=5, salesforce=4, atlassian=3, zoho=5, phonepe=4)},
            {"id": "java.oop.encapsulation", "label": "Encapsulation & Immutability",
             "description": "Builder, final classes, defensive copies.",
             "estimated_minutes": 35, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["java.basics.classes_objects"],
             "tags": ["oop", "immutability"]},
            {"id": "java.oop.inner_classes", "label": "Inner / Anonymous / Nested Classes",
             "description": "Static vs non-static nesting; anonymous classes vs lambdas.",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.0,
             "prerequisites": ["java.basics.classes_objects"],
             "tags": ["oop"]},
         ]},
        {"id": "java.collections", "label": "Collections",
         "description": "Interface hierarchy plus internals of the everyday classes.",
         "topics": [
            {"id": "java.collections.core", "label": "Core Collections",
             "description": "List / Set / Queue: implementation choices and trade-offs.",
             "estimated_minutes": 60, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.4,
             "tags": ["collections"],
             "company_importance": ci(oracle=5, salesforce=5, goldman_sachs=4, phonepe=4, zoho=5),
             "subtopics": [
                {"id": "java.collections.core.arraylist", "label": "ArrayList", "description": "Dynamic array, resize policy, iterator invalidation."},
                {"id": "java.collections.core.linkedlist", "label": "LinkedList", "description": "Doubly-linked list; when it actually beats ArrayList."},
                {"id": "java.collections.core.hashset", "label": "HashSet", "description": "HashMap-backed uniqueness set."},
                {"id": "java.collections.core.priorityqueue", "label": "PriorityQueue", "description": "Binary heap: peek/poll/offer characteristics."},
                {"id": "java.collections.core.arraydeque", "label": "ArrayDeque", "description": "Prefer over Stack/LinkedList in modern code."},
             ]},
            {"id": "java.collections.hashmap", "label": "HashMap Internals",
             "description": "Bucket array + treeified bins after collisions.",
             "estimated_minutes": 75, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 2.0,
             "prerequisites": ["java.collections.core", "java.oop.equals_hashcode"],
             "tags": ["hashmap", "internals"],
             "company_importance": ci(oracle=5, salesforce=5, atlassian=5, phonepe=5, flipkart=5, zoho=5, goldman_sachs=5, adobe=4),
             "subtopics": [
                {"id": "java.collections.hashmap.collision", "label": "Collision Handling",
                 "description": "Chaining, tree-bin conversion at threshold 8."},
                {"id": "java.collections.hashmap.internal", "label": "Internal Working (Java 8+)",
                 "description": "put(), get(), resize(), treeify() step-by-step."},
                {"id": "java.collections.hashmap.questions", "label": "Interview Questions",
                 "description": "Load factor, capacity, ordering guarantees."},
                {"id": "java.collections.hashmap.linked_hashmap", "label": "LinkedHashMap & LRU",
                 "description": "Access-order iteration for LRU caches."},
             ]},
            {"id": "java.collections.treemap", "label": "TreeMap · Sorted Maps",
             "description": "Red-black tree; floorKey/ceilingKey range operations.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["treemap", "red-black-tree"]},
            {"id": "java.collections.concurrent_map", "label": "ConcurrentHashMap",
             "description": "Segmented locking in Java 7, CAS + bin locking in Java 8+.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "prerequisites": ["java.collections.hashmap", "java.concurrency.sync"],
             "tags": ["concurrent", "hashmap"],
             "company_importance": ci(oracle=5, salesforce=4, atlassian=4, goldman_sachs=5, stripe=4)},
            {"id": "java.collections.comparator", "label": "Comparator & Comparable",
             "description": "Natural ordering vs strategy; chaining and nulls.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["sorting"]},
         ]},
        {"id": "java.generics_exceptions", "label": "Generics & Exceptions",
         "description": "Type-safety at compile time and error-handling contracts.",
         "topics": [
            {"id": "java.generics.core", "label": "Generics · PECS",
             "description": "Bounded wildcards, invariance vs covariance, type erasure.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["generics"]},
            {"id": "java.exceptions.core", "label": "Checked vs Unchecked",
             "description": "throw / throws, try-with-resources, suppressed exceptions.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["exceptions"]},
         ]},
        {"id": "java.streams_lambdas", "label": "Streams & Lambdas",
         "description": "Functional pipeline API introduced in Java 8.",
         "topics": [
            {"id": "java.lambdas.core", "label": "Lambdas & Functional Interfaces",
             "description": "@FunctionalInterface, method references, Function/Predicate/Consumer.",
             "estimated_minutes": 35, "difficulty": "easy", "interview_frequency": 4, "mastery_weight": 1.2,
             "tags": ["lambda", "functional"]},
            {"id": "java.streams.core", "label": "Streams API",
             "description": "Intermediate vs terminal ops, laziness, short-circuiting.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["java.lambdas.core"],
             "tags": ["streams"],
             "company_importance": ci(oracle=5, salesforce=4, atlassian=4, adobe=4, zoho=4)},
            {"id": "java.streams.collectors", "label": "Collectors & Grouping",
             "description": "groupingBy, partitioningBy, downstream collectors.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["java.streams.core"],
             "tags": ["streams", "collectors"]},
            {"id": "java.optional.core", "label": "Optional",
             "description": "Null-safety idioms, when to (never) call get().",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 0.9,
             "tags": ["optional"]},
         ]},
        {"id": "java.concurrency", "label": "Concurrency",
         "description": "Threading primitives, executors and modern async APIs.",
         "topics": [
            {"id": "java.concurrency.threads", "label": "Threads & Runnable",
             "description": "Lifecycle, join, interrupt, daemon threads.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["threads"],
             "company_importance": ci(oracle=5, salesforce=4, goldman_sachs=5, atlassian=4, stripe=4)},
            {"id": "java.concurrency.executor", "label": "Executors & Thread Pools",
             "description": "Fixed / cached / scheduled pools, ForkJoinPool, sizing.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.6,
             "prerequisites": ["java.concurrency.threads"],
             "tags": ["executor"],
             "company_importance": ci(oracle=5, salesforce=4, goldman_sachs=5, atlassian=4, stripe=5)},
            {"id": "java.concurrency.sync", "label": "Locks & Synchronization",
             "description": "synchronized, volatile, ReentrantLock, StampedLock, ReadWriteLock.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 5, "mastery_weight": 1.8,
             "tags": ["locks", "sync"]},
            {"id": "java.concurrency.atomics", "label": "Atomics & CAS",
             "description": "AtomicInteger, LongAdder, java.util.concurrent internals.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "prerequisites": ["java.concurrency.sync"],
             "tags": ["atomics", "cas"]},
            {"id": "java.concurrency.completable", "label": "CompletableFuture & Async",
             "description": "Async pipelines, combinators, exception handling.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "prerequisites": ["java.concurrency.executor"],
             "tags": ["async", "future"]},
            {"id": "java.concurrency.memory_model", "label": "Java Memory Model (JMM)",
             "description": "Happens-before, visibility, safe publication.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "tags": ["jmm", "memory"]},
         ]},
        {"id": "java.jvm", "label": "JVM Internals",
         "description": "Runtime memory layout, garbage collection and class loading.",
         "topics": [
            {"id": "java.jvm.memory", "label": "JVM Memory Model",
             "description": "Heap / Stack / Metaspace / PC / Native.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "tags": ["jvm", "memory"],
             "company_importance": ci(oracle=5, goldman_sachs=5, atlassian=3, adobe=3, phonepe=4)},
            {"id": "java.jvm.gc", "label": "Garbage Collection",
             "description": "Generational, G1, ZGC, Shenandoah — how to pick.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "prerequisites": ["java.jvm.memory"],
             "tags": ["gc"]},
            {"id": "java.jvm.classloader", "label": "Class Loading",
             "description": "Bootstrap / Ext / App loaders, delegation model.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "tags": ["classloader"]},
            {"id": "java.jvm.jit", "label": "JIT · C1 & C2",
             "description": "Interpreter → tiered compilation → deoptimization.",
             "estimated_minutes": 30, "difficulty": "hard", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["jit", "performance"]},
            # Curriculum sync (2026) — canonical Module 19 "Performance" (JVM tuning, profiling,
            # memory leaks, CPU profiling, JMH) had no corresponding topic.
            {"id": "java.jvm.performance", "label": "JVM Performance & Profiling",
             "description": "JVM tuning flags, CPU/heap profiling, memory-leak diagnosis, JMH micro-"
                            "benchmarking.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["java.jvm.gc"],
             "tags": ["performance", "profiling", "jmh"]},
         ]},
        {"id": "java.io_nio", "label": "IO & NIO",
         "description": "Blocking vs non-blocking IO, channels and selectors.",
         "topics": [
            {"id": "java.io.streams", "label": "IO Streams & Readers",
             "description": "Byte vs char streams, buffered wrappers.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["io"]},
            {"id": "java.nio.channels", "label": "NIO · Channels & Buffers",
             "description": "Non-blocking IO, Selector, memory-mapped files.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["nio", "channels"]},
            {"id": "java.io.serialization", "label": "Serialization",
             "description": "Serializable, transient, versioning, alternatives (Jackson, Protobuf).",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["serialization"]},
            # Curriculum sync (2026) — canonical Module 14 "File Handling" (Path/Files API) had no
            # corresponding topic; NIO channels above only covered network-style IO.
            {"id": "java.io.file_handling", "label": "File Handling · Path & Files API",
             "description": "java.nio.file.Path, Files API (read/write/copy/move/walk), file "
                            "attributes, try-with-resources for file streams.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 0.9,
             "prerequisites": ["java.nio.channels"],
             "tags": ["file-io", "nio", "path"]},
         ]},
        # Curriculum sync (2026) — canonical Module 13 "Date & Time API" and Module 18
        # "Reflection" had no corresponding modules anywhere in the Java track.
        {"id": "java.datetime_reflection", "label": "Date/Time API & Reflection",
         "description": "The modern java.time package and runtime introspection via Reflection.",
         "topics": [
            {"id": "java.datetime.core", "label": "java.time · LocalDate/Time/Duration",
             "description": "LocalDate, LocalTime, LocalDateTime, ZonedDateTime, Duration, Period — "
                            "replacing the legacy Date/Calendar APIs.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["date-time", "java-time"]},
            {"id": "java.reflection.core", "label": "Reflection, Annotations & Dynamic Proxies",
             "description": "Reflection API for inspecting classes/methods/fields at runtime, custom "
                            "annotations, dynamic proxies — the mechanism behind most DI frameworks.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["java.oop.abstraction"],
             "tags": ["reflection", "annotations", "proxy"]},
         ]},
        # Curriculum sync (2026) — canonical Module 20 "Modern Java" (virtual threads, structured
        # concurrency, pattern matching) and Module 21 "Enterprise Java" (JDBC, connection
        # pooling, transactions) had no corresponding modules.
        {"id": "java.modern", "label": "Modern Java",
         "description": "Recent JDK features that show up in senior-level interviews.",
         "topics": [
            {"id": "java.modern.core", "label": "Virtual Threads, Structured Concurrency & Pattern Matching",
             "description": "Virtual threads (Project Loom), structured concurrency, pattern matching "
                            "for switch, record patterns, sealed classes.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["java.concurrency.executor"],
             "tags": ["virtual-threads", "pattern-matching", "records"]},
         ]},
        {"id": "java.enterprise", "label": "Enterprise Java",
         "description": "Java in production backends: databases, pooling and transactions. The "
                        "track's capstone — other subjects' subject-level prerequisites point here.",
         "topics": [
            {"id": "java.enterprise.core", "label": "JDBC, Connection Pooling & Transactions",
             "description": "JDBC fundamentals, connection pooling (HikariCP), programmatic and "
                            "declarative transaction management, ORM overview (JPA/Hibernate). "
                            # Curriculum sync (2026) — Java's canonical subject order places DBMS
                            # AFTER Java, so this topic teaches JDBC mechanics without a hard
                            # dependency on the DBMS track (avoids a Java <-> DBMS prerequisite
                            # cycle); relational concepts are reinforced later once DBMS unlocks.
                            "Relational concepts (ACID, keys) are reinforced later in DBMS.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["java.modern.core"],
             "tags": ["jdbc", "transactions", "orm"]},
         ]},
    ],
}


# ---------------------------------------------------------------------------
# LLD
# ---------------------------------------------------------------------------

LLD_TRACK = {
    "id": "lld", "label": "Low-Level Design", "icon": "layers",
    "description": "Object-oriented design of components, patterns and small systems.",
    "interview_importance": 4,
    "company_importance": ci(google=3, microsoft=4, atlassian=5, uber=4, adobe=5, linkedin=4,
                              stripe=4, salesforce=5, oracle=3, phonepe=4, flipkart=4,
                              paypal=4, goldman_sachs=3, zoho=4),
    "tags": ["oop", "design-patterns"],
    "modules": [
        {"id": "lld.principles", "label": "Design Principles",
         "description": "Timeless rules that separate good and bad object-oriented code.",
         "topics": [
            {"id": "lld.principles.solid", "label": "SOLID Principles",
             "description": "SRP, OCP, LSP, ISP, DIP with real-world violations.",
             "estimated_minutes": 90, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.8,
             "tags": ["solid"],
             "company_importance": ci(atlassian=5, adobe=5, salesforce=5, uber=4, stripe=4),
             "subtopics": [
                # RC1.3.5B — OOP -> SOLID: SOLID is a refinement of OOP,
                # never taught as depending on it. srp is the first
                # sub-node in this container, so it is the leaf that
                # inherits an explicit OOP prerequisite.
                {"id": "lld.principles.solid.srp", "label": "Single Responsibility",
                 "prerequisites": ["java.oop.abstraction", "java.oop.inheritance",
                                   # Curriculum sync (2026) — LLD's canonical "# Prerequisites":
                                   # Programming Fundamentals, Java, DSA, DBMS, OS, CN. This is
                                   # LLD's entry leaf; additive alongside the existing OOP edges.
                                   "pf.professional_engineering.core", "java.enterprise.core",
                                   "dsa.advanced.segment_tree.range_sum", "dbms.warehousing.core",
                                   "os.modern_engineering.core", "cn.production.core"]},
                {"id": "lld.principles.solid.ocp", "label": "Open / Closed"},
                {"id": "lld.principles.solid.lsp", "label": "Liskov Substitution"},
                {"id": "lld.principles.solid.isp", "label": "Interface Segregation"},
                {"id": "lld.principles.solid.dip", "label": "Dependency Inversion"},
             ]},
            {"id": "lld.principles.dry_kiss", "label": "DRY / KISS / YAGNI",
             "description": "Simplicity heuristics that keep codebases honest.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["principles"]},
            {"id": "lld.principles.cohesion_coupling", "label": "Cohesion & Coupling",
             "description": "High cohesion + low coupling as a design compass.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["principles"]},
         ]},
        {"id": "lld.patterns", "label": "Design Patterns",
         "description": "The 23 GoF patterns — each with intent, UML, use-cases, Java code and interview questions.",
         "topics": [
            {"id": "lld.patterns.creational", "label": "Creational Patterns",
             "description": "How objects are constructed.",
             "estimated_minutes": 180, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.6,
             "tags": ["patterns", "creational"],
             "company_importance": ci(atlassian=5, adobe=5, salesforce=5, uber=4, stripe=4),
             "subtopics": [
                # RC1.3.5B — SOLID -> Patterns: the first pattern of each
                # category carries the SOLID (DIP) prerequisite; propagated
                # onto its `.overview` leaf by `_propagate_container_prerequisites`.
                pattern_subtopic("lld.patterns.creational.factory", "Factory Method",
                                 "Defer instantiation to subclasses.",
                                 prereqs=["lld.principles.solid.dip"]),
                pattern_subtopic("lld.patterns.creational.abstract_factory", "Abstract Factory",
                                 "Families of related objects without concrete classes."),
                pattern_subtopic("lld.patterns.creational.builder", "Builder",
                                 "Step-by-step construction of complex objects."),
                pattern_subtopic("lld.patterns.creational.singleton", "Singleton",
                                 "One-and-only-one instance with global access."),
                pattern_subtopic("lld.patterns.creational.prototype", "Prototype",
                                 "Clone existing objects instead of building anew."),
             ]},
            {"id": "lld.patterns.structural", "label": "Structural Patterns",
             "description": "How objects compose.",
             "estimated_minutes": 200, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.5,
             "tags": ["patterns", "structural"],
             "subtopics": [
                pattern_subtopic("lld.patterns.structural.adapter", "Adapter",
                                 "Wrap a class so its interface matches what a client expects.",
                                 prereqs=["lld.principles.solid.dip"]),
                pattern_subtopic("lld.patterns.structural.bridge", "Bridge",
                                 "Separate an abstraction from its implementation."),
                pattern_subtopic("lld.patterns.structural.composite", "Composite",
                                 "Tree structures where leaves and containers share an interface."),
                pattern_subtopic("lld.patterns.structural.decorator", "Decorator",
                                 "Attach responsibilities dynamically without subclassing."),
                pattern_subtopic("lld.patterns.structural.facade", "Facade",
                                 "Single simplified entry-point over a subsystem."),
                pattern_subtopic("lld.patterns.structural.flyweight", "Flyweight",
                                 "Share fine-grained objects to save memory."),
                pattern_subtopic("lld.patterns.structural.proxy", "Proxy",
                                 "Placeholder controlling access to another object."),
             ]},
            {"id": "lld.patterns.behavioral", "label": "Behavioral Patterns",
             "description": "How objects interact.",
             "estimated_minutes": 280, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.7,
             "tags": ["patterns", "behavioral"],
             "subtopics": [
                pattern_subtopic("lld.patterns.behavioral.chain", "Chain of Responsibility",
                                 "Pass a request along a chain until someone handles it.",
                                 prereqs=["lld.principles.solid.dip"]),
                pattern_subtopic("lld.patterns.behavioral.command", "Command",
                                 "Encapsulate a request as an object."),
                pattern_subtopic("lld.patterns.behavioral.interpreter", "Interpreter",
                                 "Represent grammar as an object tree and evaluate."),
                pattern_subtopic("lld.patterns.behavioral.iterator", "Iterator",
                                 "Sequentially access aggregate elements without exposing the underlying representation."),
                pattern_subtopic("lld.patterns.behavioral.mediator", "Mediator",
                                 "Central object encapsulating how a set of peers interact."),
                pattern_subtopic("lld.patterns.behavioral.memento", "Memento",
                                 "Capture and restore an object's internal state."),
                pattern_subtopic("lld.patterns.behavioral.observer", "Observer",
                                 "Publish/subscribe notification of state changes."),
                pattern_subtopic("lld.patterns.behavioral.state", "State",
                                 "Change behavior when internal state changes — the class appears to change."),
                pattern_subtopic("lld.patterns.behavioral.strategy", "Strategy",
                                 "Interchangeable algorithms selected at runtime."),
                pattern_subtopic("lld.patterns.behavioral.template", "Template Method",
                                 "Skeleton of an algorithm with steps deferred to subclasses."),
                pattern_subtopic("lld.patterns.behavioral.visitor", "Visitor",
                                 "Add operations to object structures without modifying the classes."),
             ]},
         ]},
        {"id": "lld.uml_modelling", "label": "UML & Modelling",
         "description": "Communicate designs precisely in an interview.",
         "topics": [
            {"id": "lld.uml.class_diagram", "label": "Class Diagrams",
             "description": "Association, aggregation, composition, dependency.",
             "estimated_minutes": 40, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["uml"]},
            {"id": "lld.uml.sequence", "label": "Sequence & State Diagrams",
             "description": "Model runtime behavior.",
             "estimated_minutes": 40, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["uml"]},
         ]},
        {"id": "lld.cases", "label": "Case Studies",
         "description": "Machine-coding interview darlings.",
         "topics": [
            {"id": "lld.cases.parking_lot", "label": "Design a Parking Lot",
             "description": "Slots, vehicles, entry/exit, pricing strategy.",
             "estimated_minutes": 90, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.6,
             "prerequisites": ["lld.patterns.creational", "lld.patterns.behavioral"],
             "tags": ["case-study", "machine-coding"],
             "company_importance": ci(atlassian=5, adobe=5, uber=5, phonepe=5, flipkart=5, paypal=4)},
            {"id": "lld.cases.chess", "label": "Design Chess",
             "description": "Piece polymorphism, board rules, game state.",
             "estimated_minutes": 120, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.5,
             "tags": ["case-study"]},
            {"id": "lld.cases.splitwise", "label": "Design Splitwise",
             "description": "User graph + expense settlement algorithm.",
             "estimated_minutes": 90, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.5,
             "tags": ["case-study"],
             "company_importance": ci(uber=5, atlassian=4, phonepe=5, paypal=5)},
            {"id": "lld.cases.tic_tac_toe", "label": "Design Tic-Tac-Toe",
             "description": "Efficient O(1) win-check via row/col/diag counters.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["case-study"]},
            {"id": "lld.cases.snake_ladder", "label": "Design Snake & Ladder",
             "description": "Board + dice + snakes/ladders as data.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["case-study"]},
            {"id": "lld.cases.elevator", "label": "Design Elevator System",
             "description": "Request queue, direction, scheduling algorithm.",
             "estimated_minutes": 90, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["case-study"],
             "company_importance": ci(uber=5, atlassian=4, adobe=4, flipkart=4)},
            {"id": "lld.cases.atm", "label": "Design ATM",
             "description": "State machine + strategy for cash dispensing.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["case-study"]},
            {"id": "lld.cases.book_my_show", "label": "Design BookMyShow",
             "description": "Concurrency around seat locking + payments.",
             "estimated_minutes": 120, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.6,
             "tags": ["case-study"],
             "company_importance": ci(phonepe=5, flipkart=5, atlassian=4, uber=4, paypal=4)},
            {"id": "lld.cases.lru_cache", "label": "Design LRU / LFU Cache",
             "description": "Design-level version of the DSA cache problem.",
             "estimated_minutes": 75, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "prerequisites": ["dsa.linear.linked_list.lru"],
             "tags": ["case-study", "cache"]},
            {"id": "lld.cases.rate_limiter", "label": "Design Rate Limiter (Object-Level)",
             "description": "Token bucket / leaky bucket / fixed window classes.",
             "estimated_minutes": 90, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "tags": ["case-study", "rate-limit"]},
            {"id": "lld.cases.notification", "label": "Design Notification System",
             "description": "Strategy per channel + observer for subscriptions.",
             "estimated_minutes": 90, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.3,
             "tags": ["case-study"]},
         ]},
        # ------------------------------------------------------------------
        # Curriculum sync (2026) — canonical Modules 12 (GRASP), 13 (Clean Code &
        # Craftsmanship), 15 (Refactoring), 16 (Modeling Real Systems), 17 (Concurrency &
        # Thread Safety) and 18 (Production Software Components) were entirely absent. Module
        # 19 (Machine Coding Interviews) is already covered by lld.cases/lld.cat.* below.
        # ------------------------------------------------------------------
        {"id": "lld.craftsmanship", "label": "Craftsmanship & Refactoring",
         "description": "The professional habits that separate working code from good code.",
         "topics": [
            {"id": "lld.craftsmanship.grasp", "label": "GRASP Principles",
             "description": "Information Expert, Creator, Controller, Low Coupling, High Cohesion, "
                            "Protected Variations.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["lld.principles.solid"],
             "tags": ["grasp", "principles"]},
            {"id": "lld.craftsmanship.clean_code", "label": "Clean Code & Craftsmanship",
             "description": "Naming, method/class design, code smells, DRY/KISS/YAGNI, Boy Scout "
                            "Rule, managing technical debt.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["lld.craftsmanship.grasp"],
             "tags": ["clean-code", "code-smells"]},
            {"id": "lld.craftsmanship.refactoring", "label": "Refactoring",
             "description": "Long Method, Large Class, Feature Envy, Primitive Obsession and "
                            "Duplicate Code smells; Extract Method/Class, Replace Conditional with "
                            "Polymorphism, Introduce Parameter Object.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["lld.craftsmanship.clean_code"],
             "tags": ["refactoring", "code-smells"]},
         ]},
        {"id": "lld.production_components", "label": "Production Software Design",
         "description": "Bridging object modeling into layered, thread-safe, production-ready "
                        "architecture. The track's capstone — other subjects' subject-level "
                        "prerequisites point here.",
         "topics": [
            {"id": "lld.production_components.domain_modeling", "label": "Modeling Real Systems",
             "description": "Entity, Value Object, Aggregate/Aggregate Root, Domain Service, "
                            "Repository Pattern, Service Layer, DTO/Mapper, Layered Architecture.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["lld.craftsmanship.refactoring"],
             "tags": ["domain-modeling", "repository-pattern", "dto"]},
            {"id": "lld.production_components.thread_safety", "label": "Concurrency & Thread Safety",
             "description": "Race conditions, deadlocks, reentrant/read-write locks, atomic "
                            "variables, volatile, thread pools, producer-consumer, immutability, "
                            "concurrent collections.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "prerequisites": ["lld.production_components.domain_modeling", "java.concurrency.sync"],
             "tags": ["thread-safety", "concurrency"]},
            {"id": "lld.production_components.infra", "label": "Production Software Components",
             "description": "Dependency Injection & IoC, configuration management, logging "
                            "framework, authentication/authorization modules, caching layer, "
                            "session management, notification framework, plugin architecture, audit "
                            "logging.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["lld.production_components.thread_safety"],
             "tags": ["dependency-injection", "ioc", "logging", "caching"]},
            {"id": "lld.production_components.core", "label": "Production Architecture",
             "description": "Layered, Hexagonal, Clean and Onion architecture; modular monolith; "
                            "event-driven design; Domain-Driven Design (overview); component "
                            "boundaries; evolutionary architecture — the direct bridge into HLD.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "prerequisites": ["lld.production_components.infra"],
             "tags": ["layered-architecture", "hexagonal", "ddd"]},
         ]},
        # ---------------- Categorized Case Studies (extended) ----------------
        {"id": "lld.cat.caching", "label": "Caching · Case Studies",
         "description": "Cache designs that show up in nearly every LLD interview.",
         "topics": [
            lld_case_topic("lld.cat.caching.lru", "Design LRU Cache",
                "HashMap + doubly-linked list; O(1) get/put.",
                difficulty="hard", minutes=75, freq=5, weight=1.7,
                tags=["case-study", "cache", "lru"],
                company=ci(atlassian=5, uber=5, phonepe=5, flipkart=5, paypal=4, stripe=4),
                prereqs=["dsa.linear.linked_list.lru"]),
            lld_case_topic("lld.cat.caching.lfu", "Design LFU Cache",
                "Frequency buckets + linked lists — O(1) with min-freq pointer.",
                difficulty="hard", minutes=90, freq=4, weight=1.6,
                tags=["case-study", "cache", "lfu"],
                company=ci(atlassian=4, uber=4, stripe=4)),
            lld_case_topic("lld.cat.caching.ttl", "Design TTL Cache",
                "Expiration via lazy eviction or background sweeper.",
                difficulty="medium", minutes=60, freq=3, weight=1.3,
                tags=["case-study", "cache", "ttl"]),
         ]},
        {"id": "lld.cat.booking", "label": "Booking Systems · Case Studies",
         "description": "Reservation systems with concurrency and inventory locking.",
         "topics": [
            lld_case_topic("lld.cat.booking.hotel", "Design Hotel Booking",
                "Rooms, availability calendar, holds and payments.",
                minutes=90, freq=3, weight=1.4, tags=["case-study", "booking"],
                company=ci(phonepe=4, flipkart=4, uber=4, paypal=4)),
            lld_case_topic("lld.cat.booking.flight", "Design Flight Booking",
                "Fares, seat inventory, multi-leg itineraries.",
                minutes=90, freq=3, weight=1.4, tags=["case-study", "booking"]),
            lld_case_topic("lld.cat.booking.train", "Design Train Reservation (IRCTC-like)",
                "Coach × berth inventory with waitlist and RAC.",
                minutes=90, freq=3, weight=1.4, tags=["case-study", "booking"],
                company=ci(phonepe=4, flipkart=4, paypal=3)),
            lld_case_topic("lld.cat.booking.restaurant", "Design Restaurant Reservation",
                "Time-slot inventory + table combinations.",
                minutes=75, freq=2, weight=1.2, tags=["case-study", "booking"]),
         ]},
        {"id": "lld.cat.commerce", "label": "Commerce · Case Studies",
         "description": "The building blocks of an e-commerce platform.",
         "topics": [
            lld_case_topic("lld.cat.commerce.cart", "Design Shopping Cart",
                "Line items, promotions, price snapshotting.",
                minutes=75, freq=4, weight=1.4, tags=["case-study", "commerce"],
                company=ci(flipkart=5, phonepe=4, uber=3, paypal=4)),
            lld_case_topic("lld.cat.commerce.inventory", "Design Inventory Management",
                "SKU counts, reservations, oversell prevention.",
                minutes=90, freq=4, weight=1.5, tags=["case-study", "commerce"],
                company=ci(flipkart=5, phonepe=4)),
            lld_case_topic("lld.cat.commerce.warehouse", "Design Warehouse Management",
                "Bins, pick-lists, receiving and dispatch.",
                minutes=90, freq=3, weight=1.3, tags=["case-study", "commerce"]),
            lld_case_topic("lld.cat.commerce.coupon", "Design Coupon Engine",
                "Rules engine + stacking + validation.",
                minutes=75, freq=3, weight=1.3, tags=["case-study", "commerce"],
                company=ci(flipkart=4, phonepe=4, paypal=3)),
            lld_case_topic("lld.cat.commerce.gift_card", "Design Gift Card System",
                "Denominations, redemption ledger, partial usage.",
                minutes=60, freq=2, weight=1.1, tags=["case-study", "commerce"]),
         ]},
        {"id": "lld.cat.communication", "label": "Communication · Case Studies",
         "description": "Messaging primitives at the object-model level.",
         "topics": [
            lld_case_topic("lld.cat.communication.whatsapp", "Design WhatsApp (LLD)",
                "Contacts, chats, messages, delivery status.",
                difficulty="hard", minutes=120, freq=5, weight=1.6,
                tags=["case-study", "messaging"],
                company=ci(atlassian=4, uber=4, phonepe=5, flipkart=4)),
            lld_case_topic("lld.cat.communication.chat_server", "Design Chat Server",
                "Sockets, rooms, presence, message ordering.",
                difficulty="hard", minutes=90, freq=4, weight=1.5,
                tags=["case-study", "messaging"]),
            lld_case_topic("lld.cat.communication.email_service", "Design Email Service",
                "Compose, threads, folders, filters.",
                minutes=90, freq=3, weight=1.3, tags=["case-study", "messaging"]),
            lld_case_topic("lld.cat.communication.notification_queue", "Design Notification Queue",
                "Fan-out per channel with retry + DLQ.",
                minutes=75, freq=4, weight=1.4, tags=["case-study", "messaging"]),
         ]},
        {"id": "lld.cat.scheduling", "label": "Scheduling · Case Studies",
         "description": "Job/task scheduling classes seen in almost every backend role.",
         "topics": [
            lld_case_topic("lld.cat.scheduling.cron", "Design Cron Scheduler",
                "Cron expression parsing + next-fire computation.",
                difficulty="hard", minutes=90, freq=4, weight=1.5,
                tags=["case-study", "scheduler"],
                company=ci(atlassian=4, stripe=4, uber=4, goldman_sachs=4)),
            lld_case_topic("lld.cat.scheduling.task_scheduler", "Design Task Scheduler",
                "In-memory priority scheduler with delays.",
                minutes=75, freq=3, weight=1.3, tags=["case-study", "scheduler"]),
            lld_case_topic("lld.cat.scheduling.job_queue", "Design Job Queue",
                "Durable queue with workers, retries and idempotency.",
                difficulty="hard", minutes=90, freq=4, weight=1.5, tags=["case-study", "scheduler"]),
         ]},
        {"id": "lld.cat.banking", "label": "Banking & Payments · Case Studies",
         "description": "Correctness-critical financial primitives.",
         "topics": [
            lld_case_topic("lld.cat.banking.account", "Design Bank Account",
                "Debit/credit, balance invariants, overdraft rules.",
                minutes=60, freq=3, weight=1.3, tags=["case-study", "banking"],
                company=ci(goldman_sachs=5, paypal=5, phonepe=5)),
            lld_case_topic("lld.cat.banking.wallet", "Design Digital Wallet",
                "Balance, top-ups, holds, ledger entries.",
                minutes=75, freq=4, weight=1.4, tags=["case-study", "banking", "wallet"],
                company=ci(phonepe=5, paypal=5, flipkart=4, uber=4)),
            lld_case_topic("lld.cat.banking.upi", "Design UPI Payment",
                "VPA resolution, request/response, idempotency.",
                difficulty="hard", minutes=90, freq=4, weight=1.6,
                tags=["case-study", "banking", "upi"],
                company=ci(phonepe=5, paypal=4, flipkart=4)),
            lld_case_topic("lld.cat.banking.transaction_engine", "Design Transaction Engine",
                "Double-entry ledger + immutable journal.",
                difficulty="hard", minutes=105, freq=4, weight=1.6,
                tags=["case-study", "banking"],
                company=ci(goldman_sachs=5, stripe=5, paypal=5, phonepe=4)),
         ]},
        {"id": "lld.cat.games", "label": "Games · Case Studies",
         "description": "Classic game rule-modeling problems.",
         "topics": [
            lld_case_topic("lld.cat.games.sudoku", "Design Sudoku",
                "Board, validation, solver hook.",
                minutes=60, freq=2, weight=1.1, tags=["case-study", "game"]),
            lld_case_topic("lld.cat.games.minesweeper", "Design Minesweeper",
                "Grid + BFS uncovering + mine placement.",
                minutes=60, freq=2, weight=1.1, tags=["case-study", "game"]),
            lld_case_topic("lld.cat.games.blackjack", "Design Blackjack",
                "Dealer/player state machine + card deck.",
                minutes=60, freq=2, weight=1.1, tags=["case-study", "game"]),
            lld_case_topic("lld.cat.games.uno", "Design UNO",
                "Card polymorphism + direction/skip rules.",
                minutes=60, freq=2, weight=1.1, tags=["case-study", "game"]),
         ]},
        {"id": "lld.cat.smart", "label": "Smart Systems · Case Studies",
         "description": "Real-world state-machine models.",
         "topics": [
            lld_case_topic("lld.cat.smart.traffic_signal", "Design Traffic Signal",
                "Timed FSM + emergency preemption.",
                minutes=60, freq=2, weight=1.1, tags=["case-study", "fsm"]),
            lld_case_topic("lld.cat.smart.vending_machine", "Design Vending Machine",
                "State pattern + inventory + change dispensing.",
                minutes=75, freq=4, weight=1.4, tags=["case-study", "fsm"],
                company=ci(atlassian=4, adobe=4, phonepe=4)),
            lld_case_topic("lld.cat.smart.coffee_machine", "Design Coffee Machine",
                "Recipes, ingredients, concurrency of orders.",
                minutes=60, freq=3, weight=1.2, tags=["case-study", "fsm"]),
            lld_case_topic("lld.cat.smart.printer", "Design Printer / Print Spooler",
                "Priority queue + retries + status.",
                minutes=60, freq=2, weight=1.1, tags=["case-study"]),
            lld_case_topic("lld.cat.smart.library", "Design Library Management",
                "Books, users, loans, holds, fines.",
                minutes=75, freq=3, weight=1.2, tags=["case-study"],
                company=ci(atlassian=4, oracle=4)),
            lld_case_topic("lld.cat.smart.hospital", "Design Hospital Management",
                "Patients, doctors, appointments, records.",
                minutes=90, freq=3, weight=1.3, tags=["case-study"]),
         ]},
        {"id": "lld.cat.os_inspired", "label": "OS-Inspired · Case Studies",
         "description": "Low-level primitives modeled in application code.",
         "topics": [
            lld_case_topic("lld.cat.os.memory_allocator", "Design Memory Allocator",
                "Free lists / buddy allocator; fragmentation trade-offs.",
                difficulty="hard", minutes=105, freq=3, weight=1.5,
                tags=["case-study", "os-inspired"],
                company=ci(google=4, oracle=4, goldman_sachs=4)),
            lld_case_topic("lld.cat.os.thread_pool", "Design Thread Pool",
                "Worker threads + blocking task queue + shutdown.",
                difficulty="hard", minutes=90, freq=4, weight=1.5,
                tags=["case-study", "concurrency"],
                prereqs=["java.concurrency.executor"],
                company=ci(oracle=5, atlassian=4, stripe=4, goldman_sachs=5)),
            lld_case_topic("lld.cat.os.connection_pool", "Design Connection Pool",
                "Bounded pool with acquire/release semantics.",
                minutes=75, freq=3, weight=1.3, tags=["case-study", "concurrency"]),
            lld_case_topic("lld.cat.os.file_system", "Design File System",
                "inodes, directory tree, permissions.",
                difficulty="hard", minutes=105, freq=3, weight=1.4,
                tags=["case-study", "os-inspired"]),
         ]},
    ],
}


# ---------------------------------------------------------------------------
# HLD
# ---------------------------------------------------------------------------

HLD_TRACK = {
    "id": "hld", "label": "High-Level Design", "icon": "network",
    "description": "Architecting distributed systems at scale.",
    "interview_importance": 4,
    "company_importance": ci(google=5, microsoft=4, atlassian=4, uber=5, adobe=3, linkedin=5,
                              stripe=5, salesforce=3, oracle=3, phonepe=4, flipkart=4,
                              paypal=5, goldman_sachs=4, zoho=3),
    "tags": ["system-design", "distributed"],
    "modules": [
        {"id": "hld.foundations", "label": "Foundations",
         "description": "The vocabulary every system-design round expects.",
         "topics": [
            {"id": "hld.foundations.cap", "label": "CAP Theorem",
             "description": "Consistency vs Availability under partition.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.4,
             # Curriculum sync (2026) — HLD's canonical "# Prerequisites": Programming
             # Fundamentals, Java, DSA, DBMS, OS, CN, LLD. This is HLD's entry leaf.
             "prerequisites": ["pf.professional_engineering.core", "java.enterprise.core",
                              "dsa.advanced.segment_tree.range_sum", "dbms.warehousing.core",
                              "os.modern_engineering.core", "cn.production.core",
                              "lld.production_components.core"],
             "tags": ["cap"]},
            {"id": "hld.foundations.pacelc", "label": "PACELC & Trade-offs",
             "description": "The under-appreciated `else` branch of CAP.",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["hld.foundations.cap"],
             "tags": ["pacelc"]},
            {"id": "hld.foundations.consistency", "label": "Consistency Models",
             "description": "Strong, sequential, eventual, causal.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["consistency"]},
            {"id": "hld.foundations.load_balancing", "label": "Load Balancing",
             "description": "L4 vs L7, round-robin, least-connections, consistent hashing.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.4,
             "prerequisites": ["cn.foundations.tcp_ip"],
             "tags": ["load-balancing"]},
            {"id": "hld.foundations.scalability", "label": "Scalability & Availability",
             "description": "Vertical vs horizontal scaling, SLIs/SLOs, availability math.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["scalability"]},
            {"id": "hld.foundations.napkin_math", "label": "Back-of-the-envelope",
             "description": "QPS, storage, bandwidth estimation.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.4,
             "tags": ["estimation"]},
         ]},
        {"id": "hld.caching", "label": "Caching & CDN",
         "description": "Faster reads and edge acceleration.",
         "topics": [
            {"id": "hld.caching.strategies", "label": "Caching Strategies",
             "description": "Read-through, write-through, write-back, write-around.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["caching"],
             "subtopics": [
                {"id": "hld.caching.strategies.aside", "label": "Cache-Aside"},
                {"id": "hld.caching.strategies.write_through", "label": "Write-Through"},
                {"id": "hld.caching.strategies.write_back", "label": "Write-Back"},
                {"id": "hld.caching.strategies.write_around", "label": "Write-Around"},
             ]},
            {"id": "hld.caching.eviction", "label": "Eviction Policies",
             "description": "LRU, LFU, ARC, FIFO — trade-offs.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["caching", "eviction"]},
            {"id": "hld.caching.redis", "label": "Redis Deep-Dive",
             "description": "Data structures, persistence and clustering.",
             "estimated_minutes": 120, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.6,
             # RC1.3.5B — bridges the previously-broken DSA -> LLD -> HLD
             # caching continuity (LRU Cache case study never connected
             # forward to anything).
             "prerequisites": ["hld.caching.strategies", "lld.cat.caching.lru"],
             "tags": ["redis"],
             "subtopics": [
                {"id": "hld.caching.redis.ttl", "label": "TTL & Eviction"},
                {"id": "hld.caching.redis.persistence", "label": "Persistence · RDB & AOF"},
                {"id": "hld.caching.redis.pubsub", "label": "Pub/Sub & Streams"},
                {"id": "hld.caching.redis.cluster", "label": "Cluster & Sentinel"},
             ]},
            {"id": "hld.caching.cdn", "label": "CDN & Edge",
             "description": "Pop network, cache invalidation, origin shielding.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["cdn"]},
         ]},
        {"id": "hld.databases", "label": "Databases at Scale",
         "description": "Storage-side trade-offs of internet-scale systems.",
         "topics": [
            {"id": "hld.db.sql_vs_nosql", "label": "SQL vs NoSQL",
             "description": "When each shape wins.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["database"]},
            {"id": "hld.db.sharding", "label": "Sharding & Partitioning",
             "description": "Range, hash and directory-based partitioning.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 5, "mastery_weight": 1.7,
             "tags": ["sharding"]},
            {"id": "hld.db.replication", "label": "Replication",
             "description": "Leader-follower vs multi-leader vs leaderless.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "tags": ["replication"]},
            {"id": "hld.db.indexing", "label": "Indexing at Scale",
             "description": "B-tree, LSM tree, inverted index.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["indexing"]},
         ]},
        {"id": "hld.messaging", "label": "Messaging & Streams",
         "description": "Async communication and event-driven backbones.",
         "topics": [
            {"id": "hld.messaging.queues", "label": "Message Queues",
             "description": "Queue vs topic, at-least-once vs at-most-once vs exactly-once.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["queue"]},
            {"id": "hld.messaging.kafka", "label": "Apache Kafka",
             "description": "Partitions, offsets, consumer groups, log-compaction.",
             "estimated_minutes": 120, "difficulty": "hard", "interview_frequency": 5, "mastery_weight": 1.8,
             "prerequisites": ["hld.messaging.queues", "cn.foundations.tcp_ip", "hld.distributed.systems"],
             "tags": ["kafka"],
             "company_importance": ci(linkedin=5, uber=5, stripe=5, atlassian=4, paypal=5, phonepe=4)},
            {"id": "hld.messaging.rabbitmq", "label": "RabbitMQ / AMQP",
             "description": "Exchanges, bindings, routing keys.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["hld.messaging.queues"],
             "tags": ["rabbitmq"]},
            {"id": "hld.messaging.pubsub", "label": "Pub/Sub & Fan-out",
             "description": "Broadcasting to many consumers with low latency.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["pubsub"]},
         ]},
        {"id": "hld.distributed", "label": "Distributed Systems",
         "description": "Consensus, coordination and failure modes.",
         "topics": [
            {"id": "hld.distributed.systems", "label": "Distributed Systems Basics",
             "description": "Fallacies, partial failure, timeouts, retries, idempotency.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["distributed"]},
            {"id": "hld.distributed.consensus", "label": "Consensus · Raft & Paxos",
             "description": "Leader election, log replication, safety proofs.",
             "estimated_minutes": 90, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.6,
             "prerequisites": ["hld.distributed.systems"],
             "tags": ["consensus"]},
            {"id": "hld.distributed.consistent_hashing", "label": "Consistent Hashing",
             "description": "Ring hashing + virtual nodes for balanced sharding.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["hashing", "sharding"]},
            {"id": "hld.distributed.microservices", "label": "Microservices Patterns",
             "description": "Saga, CQRS, service discovery, circuit breaker.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["microservices"]},
            {"id": "hld.distributed.event_sourcing", "label": "Event Sourcing & CQRS",
             "description": "Immutable log as source of truth.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["event-sourcing"]},
            # Curriculum sync (2026) — canonical Module 13 "Consistency & Distributed
            # Transactions" (2PC/Saga/idempotency) had no corresponding topic.
            {"id": "hld.distributed.consistency_patterns", "label": "Consistency & Distributed Transactions",
             "description": "Two-phase & three-phase commit, the Saga pattern, idempotency, "
                            "compensating transactions, ACID vs BASE trade-offs at distributed "
                            "scale.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["hld.distributed.systems", "hld.foundations.consistency"],
             "tags": ["saga", "2pc", "idempotency"]},
         ]},
        {"id": "hld.security", "label": "Security & Reliability",
         "description": "Authn/authz, secrets and resiliency patterns.",
         "topics": [
            {"id": "hld.security.auth", "label": "Auth · JWT / OAuth2 / SSO",
             "description": "Token flow, refresh, PKCE, SAML for enterprise.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["auth"]},
            {"id": "hld.security.rate_limit", "label": "Rate Limiting at Edge",
             "description": "Token bucket, sliding window, distributed limiter design.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["hld.caching.redis"],
             "tags": ["rate-limit"]},
            {"id": "hld.security.resiliency", "label": "Resiliency Patterns",
             "description": "Circuit breaker, bulkhead, retry with backoff, timeouts.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["resiliency"]},
            # Curriculum sync (2026) — canonical Module 18 "Security & Reliability" also names
            # secrets management, Zero Trust and disaster recovery, which had no corresponding
            # topic (only auth/rate-limit/resiliency existed).
            {"id": "hld.security.secrets_compliance", "label": "Secrets, Zero Trust & Disaster Recovery",
             "description": "Secrets management (Vault/KMS), Zero Trust networking, backup strategy "
                            "and disaster recovery, compliance overview (PCI-DSS/SOC2).",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["hld.security.auth"],
             "tags": ["secrets", "zero-trust", "disaster-recovery"]},
         ]},
        # ------------------------------------------------------------------
        # Curriculum sync (2026) — canonical Modules 2 (Architectural Thinking), 10
        # (Communication Patterns), 7 (API Gateway concept), 16 (Cloud-Native Architecture),
        # 17 (Observability & Monitoring concept) and 20 (Software Architecture Mastery) had
        # no corresponding foundational-concept topics (only case studies existed for some).
        # ------------------------------------------------------------------
        {"id": "hld.architecture", "label": "Architectural Thinking & Communication",
         "description": "How to decompose a system and choose how its parts talk to each other.",
         "topics": [
            {"id": "hld.architecture.thinking", "label": "Architectural Thinking",
             "description": "System decomposition, monolith vs microservices at the architecture "
                            "level, coupling & cohesion at system scale, layered vs hexagonal "
                            "system architecture.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["hld.foundations.scalability"],
             "tags": ["architecture", "decomposition"]},
            {"id": "hld.architecture.communication", "label": "Communication Patterns",
             "description": "REST vs gRPC vs GraphQL, synchronous vs asynchronous communication, "
                            "and when to reach for WebSockets/SSE/RPC in a distributed system.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["hld.architecture.thinking"],
             "tags": ["rest", "grpc", "graphql"]},
            {"id": "hld.architecture.api_gateway", "label": "API Gateway & Reverse Proxy",
             "description": "Routing, authentication, rate-limiting and request transformation at "
                            "the edge; Backend-for-Frontend pattern.",
             "estimated_minutes": 35, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["hld.architecture.communication", "hld.security.rate_limit"],
             "tags": ["api-gateway", "reverse-proxy", "bff"]},
         ]},
        {"id": "hld.platform", "label": "Cloud-Native & Platform Engineering",
         "description": "Running distributed systems reliably at cloud scale. The track's capstone "
                        "module.",
         "topics": [
            {"id": "hld.platform.cloud_native", "label": "Cloud-Native Architecture",
             "description": "IaaS/PaaS/SaaS, containers & Kubernetes at HLD scale, auto-scaling, "
                            "Infrastructure as Code, multi-region and multi-cloud deployment.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["hld.architecture.api_gateway"],
             "tags": ["cloud-native", "kubernetes", "iac"]},
            {"id": "hld.platform.observability", "label": "Observability & Monitoring",
             "description": "SLIs/SLOs/SLAs, distributed tracing, metrics & logging pipelines, "
                            "alerting, incident response, root-cause analysis.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["hld.platform.cloud_native"],
             "tags": ["observability", "sli-slo", "tracing"]},
            {"id": "hld.platform.core", "label": "Software Architecture Mastery",
             "description": "Architecture Decision Records, advanced service-mesh patterns, "
                            "platform engineering, continuous architectural evolution.",
             "estimated_minutes": 35, "difficulty": "hard", "interview_frequency": 2, "mastery_weight": 1.2,
             "prerequisites": ["hld.platform.observability"],
             "tags": ["adr", "service-mesh", "platform-engineering"]},
         ]},
        {"id": "hld.cases", "label": "Case Studies · Classics",
         "description": "The evergreen system-design walk-throughs — each with the full 10-part breakdown.",
         "topics": [
            hld_case_topic("hld.cases.url_shortener", "Design a URL Shortener",
                "Base62 encoding, DB sharding, cache layer.",
                difficulty="medium", minutes=75, freq=5, weight=1.5, tags=["case-study"]),
            hld_case_topic("hld.cases.rate_limiter", "Design a Rate Limiter",
                "Global counter, token bucket at scale.",
                minutes=90, freq=5, weight=1.6, tags=["case-study"],
                prereqs=["hld.caching.redis", "hld.security.rate_limit"]),
            hld_case_topic("hld.cases.news_feed", "Design a News Feed",
                "Fan-out on write vs read.",
                minutes=90, freq=5, weight=1.6, tags=["case-study"],
                company=ci(linkedin=5, atlassian=4, uber=4, phonepe=4)),
            hld_case_topic("hld.cases.chat", "Design a Chat / WhatsApp",
                "Online status, delivery receipts, e2e messaging.",
                minutes=120, freq=5, weight=1.7, tags=["case-study"],
                company=ci(uber=5, linkedin=4, phonepe=5, flipkart=4, paypal=4)),
            hld_case_topic("hld.cases.search", "Design a Typeahead / Search",
                "Trie + ranking + caching.",
                minutes=90, freq=4, weight=1.5, tags=["case-study"],
                prereqs=["dsa.trees.tries"]),
            hld_case_topic("hld.cases.uber", "Design Uber / Ride-Sharing",
                "Geo-index, matching, surge pricing.",
                minutes=120, freq=5, weight=1.8, tags=["case-study"],
                company=ci(uber=5, atlassian=4, linkedin=3, phonepe=4)),
            hld_case_topic("hld.cases.netflix", "Design Netflix / YouTube",
                "Video encoding pipeline, CDN, recommendations.",
                minutes=120, freq=4, weight=1.6, tags=["case-study"]),
            hld_case_topic("hld.cases.twitter", "Design Twitter / X",
                "Timeline fanout, celebrity handling.",
                minutes=90, freq=4, weight=1.5, tags=["case-study"]),
            hld_case_topic("hld.cases.instagram", "Design Instagram",
                "Media storage, feed generation.",
                minutes=90, freq=4, weight=1.5, tags=["case-study"]),
            hld_case_topic("hld.cases.dropbox", "Design Dropbox / Google Drive",
                "Chunking, dedup, sync protocol.",
                minutes=120, freq=3, weight=1.4, tags=["case-study"]),
            hld_case_topic("hld.cases.payment", "Design a Payment System",
                "Idempotency, ledgers, reconciliation.",
                minutes=120, freq=4, weight=1.6, tags=["case-study"],
                company=ci(stripe=5, paypal=5, phonepe=5, flipkart=4, goldman_sachs=4)),
         ]},
        # ---------------- Categorized Case Studies (extended) ----------------
        {"id": "hld.cat.storage", "label": "Storage · Case Studies",
         "description": "Object stores, file sync and blob services.",
         "topics": [
            hld_case_topic("hld.cat.storage.google_drive", "Design Google Drive",
                "Metadata service, blob store, chunk-level sync.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "storage"]),
            hld_case_topic("hld.cat.storage.dropbox", "Design Dropbox (Deep-Dive)",
                "Rolling-hash dedup, block cache, LAN sync.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "storage"]),
            hld_case_topic("hld.cat.storage.s3", "Design Amazon S3",
                "Erasure coding, consistent hashing, versioning.",
                minutes=150, freq=4, weight=1.7, tags=["case-study", "storage"],
                company=ci(google=4, stripe=4, uber=4, atlassian=4)),
         ]},
        {"id": "hld.cat.messaging", "label": "Messaging · Case Studies",
         "description": "Real-time chat and streaming platforms.",
         "topics": [
            hld_case_topic("hld.cat.messaging.slack", "Design Slack",
                "Channels, threads, presence, search.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "messaging"],
                company=ci(atlassian=5, stripe=4, linkedin=4)),
            hld_case_topic("hld.cat.messaging.discord", "Design Discord",
                "Voice + text; low-latency fan-out.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "messaging"]),
            hld_case_topic("hld.cat.messaging.teams", "Design MS Teams",
                "Enterprise chat + meetings + files.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "messaging"],
                company=ci(microsoft=5, atlassian=4)),
            hld_case_topic("hld.cat.messaging.kafka", "Design Kafka (System-Level)",
                "Broker cluster, partitions, ISR replication.",
                minutes=150, freq=4, weight=1.8, tags=["case-study", "kafka"],
                prereqs=["hld.messaging.kafka"],
                company=ci(linkedin=5, uber=5, stripe=5, paypal=5, phonepe=4)),
         ]},
        {"id": "hld.cat.search", "label": "Search · Case Studies",
         "description": "Indexes, ranking and query serving.",
         "topics": [
            hld_case_topic("hld.cat.search.elasticsearch", "Design Elasticsearch",
                "Inverted index, shards, near-real-time refresh.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "search"],
                company=ci(linkedin=5, atlassian=4, uber=4)),
            hld_case_topic("hld.cat.search.google_search", "Design Google Search",
                "Crawling, indexing, ranking, serving stack.",
                minutes=150, freq=4, weight=1.8, tags=["case-study", "search"],
                company=ci(google=5, microsoft=4)),
            hld_case_topic("hld.cat.search.autocomplete", "Design Autocomplete / Typeahead",
                "Prefix trie + popularity + personalization.",
                minutes=90, freq=4, weight=1.5, tags=["case-study", "search"],
                prereqs=["dsa.trees.tries"]),
         ]},
        {"id": "hld.cat.streaming", "label": "Streaming · Case Studies",
         "description": "Audio/video streaming at planetary scale.",
         "topics": [
            hld_case_topic("hld.cat.streaming.spotify", "Design Spotify",
                "Catalog, playback, recommendations, playlists.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "streaming"]),
            hld_case_topic("hld.cat.streaming.netflix", "Design Netflix (Deep-Dive)",
                "Open Connect CDN, ABR streaming, encoding pipeline.",
                minutes=150, freq=4, weight=1.7, tags=["case-study", "streaming"]),
            hld_case_topic("hld.cat.streaming.live", "Design Live Streaming",
                "Ingest, transcoding, HLS/DASH, low-latency.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "streaming"]),
            hld_case_topic("hld.cat.streaming.zoom", "Design Zoom",
                "SFU vs MCU, jitter buffer, screen share.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "streaming"]),
         ]},
        {"id": "hld.cat.finance", "label": "Finance · Case Studies",
         "description": "Financial-grade correctness and idempotency.",
         "topics": [
            hld_case_topic("hld.cat.finance.upi", "Design UPI (System-Level)",
                "Payer PSP ↔ NPCI ↔ Payee PSP flow with idempotency.",
                minutes=120, freq=4, weight=1.7, tags=["case-study", "finance", "upi"],
                company=ci(phonepe=5, paypal=5, flipkart=4, stripe=4)),
            hld_case_topic("hld.cat.finance.wallet", "Design Digital Wallet (System-Level)",
                "Balance service, ledger, reconciliation.",
                minutes=120, freq=4, weight=1.7, tags=["case-study", "finance", "wallet"],
                company=ci(phonepe=5, paypal=5, flipkart=4)),
            hld_case_topic("hld.cat.finance.payment_gateway", "Design a Payment Gateway",
                "Merchant onboarding, tokenization, PCI scope.",
                minutes=120, freq=5, weight=1.8, tags=["case-study", "finance"],
                company=ci(stripe=5, paypal=5, phonepe=5, goldman_sachs=4)),
            hld_case_topic("hld.cat.finance.ledger", "Design a Financial Ledger",
                "Double-entry, append-only journal, audit.",
                minutes=105, freq=4, weight=1.6, tags=["case-study", "finance"],
                company=ci(stripe=5, paypal=5, goldman_sachs=5, phonepe=4)),
         ]},
        {"id": "hld.cat.infra", "label": "Infrastructure · Case Studies",
         "description": "Platform services every backend engineer touches.",
         "topics": [
            hld_case_topic("hld.cat.infra.api_gateway", "Design API Gateway",
                "Routing, auth, rate-limit, request transformation.",
                minutes=105, freq=4, weight=1.6, tags=["case-study", "infra"],
                prereqs=["hld.security.rate_limit"],
                company=ci(atlassian=4, stripe=4, uber=4, linkedin=4)),
            hld_case_topic("hld.cat.infra.cdn", "Design a CDN",
                "PoPs, anycast, cache hierarchy, purge.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "infra", "cdn"]),
            hld_case_topic("hld.cat.infra.distributed_cache", "Design a Distributed Cache",
                "Consistent hashing, replication, cache stampede.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "infra", "cache"],
                prereqs=["hld.distributed.consistent_hashing"]),
            hld_case_topic("hld.cat.infra.logging", "Design a Logging System",
                "Ingest pipeline, indexing, retention tiers.",
                minutes=105, freq=3, weight=1.4, tags=["case-study", "infra", "logging"]),
            hld_case_topic("hld.cat.infra.monitoring", "Design a Monitoring System",
                "Metrics + traces + alerts stack.",
                minutes=120, freq=4, weight=1.5, tags=["case-study", "infra", "monitoring"]),
            hld_case_topic("hld.cat.infra.metrics", "Design a Metrics Platform",
                "Time-series DB, cardinality control, query engine.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "infra", "metrics"]),
         ]},
        {"id": "hld.cat.social", "label": "Social · Case Studies",
         "description": "Feed generation, ranking and social graph.",
         "topics": [
            hld_case_topic("hld.cat.social.linkedin", "Design LinkedIn",
                "Social graph, feed, connections, messaging.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "social"],
                company=ci(linkedin=5, microsoft=4, atlassian=3)),
            hld_case_topic("hld.cat.social.facebook_feed", "Design Facebook Feed",
                "Ranking, edge-rank, hybrid fan-out.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "social"]),
            hld_case_topic("hld.cat.social.instagram_stories", "Design Instagram Stories",
                "24h ephemeral content, viewer tracking.",
                minutes=105, freq=3, weight=1.4, tags=["case-study", "social"]),
            hld_case_topic("hld.cat.social.twitter_timeline", "Design Twitter Timeline",
                "Push vs pull, celebrity fan-out hybrid.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "social"]),
         ]},
        {"id": "hld.cat.ecommerce", "label": "E-Commerce · Case Studies",
         "description": "The systems behind a marketplace.",
         "topics": [
            hld_case_topic("hld.cat.ecommerce.amazon_cart", "Design Amazon Cart",
                "Cart service, price snapshot, checkout.",
                minutes=105, freq=4, weight=1.5, tags=["case-study", "commerce"],
                company=ci(flipkart=5, phonepe=4, uber=3)),
            hld_case_topic("hld.cat.ecommerce.inventory", "Design Inventory Service",
                "Multi-warehouse counts, reservation, oversell prevention.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "commerce"],
                company=ci(flipkart=5, phonepe=4)),
            hld_case_topic("hld.cat.ecommerce.recommendation", "Design Recommendation Engine",
                "Offline training, online serving, cold start.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "ml-systems"],
                company=ci(linkedin=5, flipkart=4, atlassian=3)),
            hld_case_topic("hld.cat.ecommerce.order_service", "Design Order Service",
                "State machine + saga across payment/inventory.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "commerce"],
                prereqs=["hld.distributed.microservices"]),
         ]},
        {"id": "hld.cat.maps", "label": "Maps · Case Studies",
         "description": "Geo-indexing and dispatch systems.",
         "topics": [
            hld_case_topic("hld.cat.maps.google_maps_nearby", "Design Google Maps Nearby / Yelp",
                "Geo-hash, quad-tree, radius queries.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "geo"]),
            hld_case_topic("hld.cat.maps.uber_dispatch", "Design Uber Dispatch",
                "Driver matching, ETA, surge pricing.",
                minutes=120, freq=5, weight=1.8, tags=["case-study", "geo"],
                company=ci(uber=5, atlassian=3)),
         ]},
        {"id": "hld.cat.misc", "label": "Misc · Case Studies",
         "description": "Developer-facing platforms and collaboration tools.",
         "topics": [
            hld_case_topic("hld.cat.misc.github", "Design GitHub",
                "Git storage, PRs, webhooks, CI hooks.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "devtools"]),
            hld_case_topic("hld.cat.misc.google_docs", "Design Google Docs",
                "CRDTs / OT for collaborative editing.",
                minutes=120, freq=4, weight=1.7, tags=["case-study", "collab"],
                company=ci(google=4, atlassian=5, microsoft=4)),
            hld_case_topic("hld.cat.misc.collab_editor", "Design a Collaborative Editor",
                "OT vs CRDT, cursor sync, presence.",
                minutes=120, freq=3, weight=1.5, tags=["case-study", "collab"]),
            hld_case_topic("hld.cat.misc.web_crawler", "Design a Web Crawler",
                "URL frontier, dedup, politeness, sharded workers.",
                minutes=120, freq=4, weight=1.6, tags=["case-study", "crawler"]),
            hld_case_topic("hld.cat.misc.online_compiler", "Design an Online Compiler",
                "Sandboxing, quotas, judge queue.",
                minutes=105, freq=3, weight=1.4, tags=["case-study", "devtools"]),
         ]},
    ],
}


# ---------------------------------------------------------------------------
# OS
# ---------------------------------------------------------------------------

OS_TRACK = {
    "id": "operating_systems", "label": "Operating Systems", "icon": "cpu",
    "description": "How processes, threads and memory really work under your program.",
    "interview_importance": 3,
    "company_importance": ci(google=3, microsoft=4, atlassian=3, uber=3, adobe=3, linkedin=3,
                              stripe=3, salesforce=3, oracle=4, phonepe=3, flipkart=3,
                              paypal=3, goldman_sachs=4, zoho=4),
    "tags": ["os"],
    "modules": [
        # RC1.3.5B — Curriculum-foundation gap: nothing taught kernel vs
        # user mode / what an OS actually is before diving into processes.
        {"id": "os.foundations", "label": "Foundations",
         "description": "What an operating system actually does, before processes, memory or files.",
         "topics": [
            {"id": "os.foundations.intro", "label": "What Is an Operating System?",
             "description": "Kernel vs user mode, system calls, the OS as a resource manager.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             # Curriculum sync (2026) — OS's canonical "# Prerequisites" section: Programming
             # Fundamentals, Java, Data Structures & Algorithms. This is OS's entry leaf.
             "prerequisites": ["pf.professional_engineering.core", "java.enterprise.core", "dsa.advanced.segment_tree.range_sum"],
             "tags": ["os", "foundations", "kernel"]},
         ]},
        {"id": "os.processes", "label": "Processes & Threads",
         "description": "Concurrency at the OS level.",
         "topics": [
            {"id": "os.processes.basics", "label": "Process vs Thread",
             "description": "Address spaces, context switches, PCB.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.3,
             "prerequisites": ["os.foundations.intro"],
             "tags": ["process", "thread"]},
            {"id": "os.processes.scheduling", "label": "Process Scheduling",
             "description": "FCFS, SJF, Round-Robin, MLFQ, CFS.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["scheduling"]},
            {"id": "os.processes.sync", "label": "Semaphores, Mutex & Monitors",
             "description": "Producer-consumer, readers-writers, dining philosophers.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.5,
             "prerequisites": ["os.processes.basics"],
             "tags": ["synchronization"]},
            {"id": "os.processes.deadlocks", "label": "Deadlocks",
             "description": "Necessary conditions, prevention, avoidance (Banker's).",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["os.processes.sync"],
             "tags": ["deadlock"]},
            {"id": "os.processes.ipc", "label": "Inter-Process Communication",
             "description": "Pipes, shared memory, message queues, sockets.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["ipc"]},
         ]},
        {"id": "os.memory", "label": "Memory Management",
         "description": "How virtual memory maps to physical RAM.",
         "topics": [
            {"id": "os.memory.paging", "label": "Paging",
             "description": "Page tables, TLB, multi-level paging.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["paging"]},
            {"id": "os.memory.virtual", "label": "Virtual Memory",
             "description": "Demand paging, page replacement (LRU/Clock).",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["os.memory.paging"],
             "tags": ["virtual-memory"]},
            {"id": "os.memory.segmentation", "label": "Segmentation",
             "description": "Segmented vs paged memory; hybrids.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["segmentation"]},
         ]},
        {"id": "os.filesystems", "label": "File Systems & I/O",
         "description": "How storage is structured and accessed.",
         "topics": [
            {"id": "os.fs.basics", "label": "File System Fundamentals",
             "description": "inodes, directories, journaling.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["filesystem"]},
            {"id": "os.io.models", "label": "I/O Models",
             "description": "Blocking, non-blocking, multiplexed (select/epoll), async.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["io"]},
         ]},
        # ------------------------------------------------------------------
        # Curriculum sync (2026) — canonical Modules 12-19 (Level 3 Intermediate tail through
        # Level 4 Advanced) were entirely absent: the doc gives these subjects rich, non-
        # boilerplate "Major Areas" content (unlike DSA/DBMS), so real gaps here are genuine
        # sync debt, not invented curriculum.
        # ------------------------------------------------------------------
        {"id": "os.security", "label": "Security & Protection",
         "description": "How the OS protects processes, users, files and memory from each other.",
         "topics": [
            {"id": "os.security.core", "label": "Access Control, Isolation & Sandboxing",
             "description": "Authentication vs authorization, protection domains, user/kernel mode, "
                            "access matrix, ACLs, capabilities, process isolation, memory protection, "
                            "secure boot, sandboxing (SELinux/AppArmor).",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["os.io.models"],
             "tags": ["security", "access-control", "sandboxing"]},
         ]},
        {"id": "os.multiprocessor", "label": "Multiprocessor Systems",
         "description": "Scheduling and coordinating execution across multiple CPU cores.",
         "topics": [
            {"id": "os.multiprocessor.core", "label": "SMP, NUMA & Cache Coherence",
             "description": "Symmetric/asymmetric multiprocessing, multi-core systems, NUMA, CPU "
                            "affinity, cache coherence, false sharing, inter-processor communication.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["os.security.core"],
             "tags": ["smp", "numa", "cache-coherence"]},
         ]},
        {"id": "os.distributed", "label": "Distributed Operating Systems",
         "description": "Coordinating computation and resources across multiple machines.",
         "topics": [
            {"id": "os.distributed.core", "label": "RPC, Clock Sync & Distributed Mutual Exclusion",
             "description": "Network transparency, RPC, distributed file systems, logical/vector "
                            "clocks, distributed mutual exclusion, consensus (intro), replication, "
                            "fault tolerance.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["os.multiprocessor.core"],
             "tags": ["distributed-os", "rpc", "clocks"]},
         ]},
        {"id": "os.virtualization", "label": "Virtualization & Containers",
         "description": "How VMs and containers share hardware efficiently.",
         "topics": [
            {"id": "os.virtualization.core", "label": "Hypervisors, Namespaces & cgroups",
             "description": "Type-1 vs Type-2 hypervisors, full vs para virtualization, VMs vs "
                            "containers, Linux namespaces, cgroups, Docker architecture, OCI, "
                            "Kubernetes overview.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["os.distributed.core"],
             "tags": ["virtualization", "containers", "docker", "cgroups"]},
         ]},
        {"id": "os.kernel", "label": "Kernel Architecture & Internals",
         "description": "How the kernel itself is designed and how it boots.",
         "topics": [
            {"id": "os.kernel.core", "label": "Monolithic vs Microkernel & Boot Process",
             "description": "Monolithic, microkernel, hybrid and modular kernel designs; boot "
                            "process, interrupt/exception handling, kernel threads/modules, kernel "
                            "synchronization and memory management.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["os.virtualization.core"],
             "tags": ["kernel", "monolithic", "microkernel"]},
         ]},
        {"id": "os.performance", "label": "Performance Engineering",
         "description": "Measuring and optimizing OS-level performance under real workloads.",
         "topics": [
            {"id": "os.performance.core", "label": "Profiling, Bottlenecks & Capacity Planning",
             "description": "CPU/memory utilization, throughput vs latency, context-switch overhead, "
                            "system profiling, load average, CPU-bound vs IO-bound workloads, "
                            "capacity planning.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["os.kernel.core"],
             "tags": ["performance", "profiling", "bottlenecks"]},
         ]},
        {"id": "os.reliability", "label": "Reliability & Fault Tolerance",
         "description": "How the OS stays available and recovers from failure.",
         "topics": [
            {"id": "os.reliability.core", "label": "Checkpointing, Journaling & Disaster Recovery",
             "description": "Reliability vs availability, error detection, failure recovery, "
                            "checkpointing, journaling, crash recovery, redundancy, disaster recovery.",
             "estimated_minutes": 35, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["os.performance.core"],
             "tags": ["reliability", "fault-tolerance", "journaling"]},
         ]},
        {"id": "os.modern_engineering", "label": "OS in Modern Engineering",
         "description": "Bridging OS concepts with cloud, backend and production engineering. The "
                        "track's capstone — other subjects' subject-level prerequisites point here.",
         "topics": [
            {"id": "os.modern_engineering.core", "label": "OS in Cloud, Kubernetes & Production Troubleshooting",
             "description": "OS concepts in backend/cloud engineering, containers and microservices, "
                            "Kubernetes scheduling, resource isolation, syscalls in backend "
                            "applications, production troubleshooting.",
             "estimated_minutes": 35, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["os.reliability.core"],
             "tags": ["cloud", "kubernetes", "production"]},
         ]},
    ],
}


# ---------------------------------------------------------------------------
# DBMS
# ---------------------------------------------------------------------------

DBMS_TRACK = {
    "id": "dbms", "label": "Databases", "icon": "database",
    "description": "SQL fundamentals, indexing internals and NoSQL landscapes.",
    "interview_importance": 4,
    "company_importance": ci(google=3, microsoft=4, atlassian=4, uber=4, adobe=3, linkedin=4,
                              stripe=4, salesforce=4, oracle=5, phonepe=4, flipkart=4,
                              paypal=5, goldman_sachs=4, zoho=5),
    "tags": ["database", "sql"],
    "modules": [
        {"id": "dbms.relational", "label": "Relational Databases",
         "description": "ACID, indexing and normalization.",
         "topics": [
            # RC1.3.5B — Curriculum-foundation gap: Keys & ER-Modelling are
            # the actual starting point of relational-DB literacy; ACID and
            # indexing previously assumed them without ever teaching them.
            {"id": "dbms.relational.keys", "label": "Keys · Primary, Foreign & Candidate",
             "description": "Primary/candidate/foreign/composite keys, referential integrity — "
                            "the vocabulary every schema and join question builds on.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 4, "mastery_weight": 1.2,
             # Curriculum sync (2026) — DBMS's canonical "Prerequisite Subjects": Programming
             # Fundamentals, Java. This is DBMS's entry leaf.
             "prerequisites": ["pf.professional_engineering.core", "java.enterprise.core"],
             "tags": ["keys", "foundations"]},
            {"id": "dbms.relational.er_model", "label": "ER Modelling",
             "description": "Entities, relationships, cardinality and converting an ER diagram into tables.",
             "estimated_minutes": 40, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["dbms.relational.keys"],
             "tags": ["er-model", "foundations"]},
            {"id": "dbms.relational.acid", "label": "Transactions & ACID",
             "description": "Atomicity, Consistency, Isolation, Durability.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "prerequisites": ["dbms.relational.keys"],
             "tags": ["acid"]},
            {"id": "dbms.relational.indexing", "label": "Indexing Strategies",
             "description": "B+ tree, hash, bitmap, covering index.",
             "estimated_minutes": 75, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.6,
             "prerequisites": ["dbms.relational.keys"],
             "tags": ["indexing"]},
            {"id": "dbms.relational.normalization", "label": "Normalization",
             "description": "1NF → BCNF and when to denormalize.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "prerequisites": ["dbms.relational.er_model"],
             "tags": ["normalization"]},
            {"id": "dbms.relational.joins", "label": "Joins & Query Optimization",
             "description": "Nested-loop, hash, merge joins; EXPLAIN plans.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["dbms.relational.indexing", "dbms.relational.keys"],
             "tags": ["joins", "optimizer"]},
            {"id": "dbms.relational.sql", "label": "SQL Deep-Dive",
             "description": "Window functions, CTEs, GROUP BY vs PARTITION BY.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["sql"],
             "company_importance": ci(oracle=5, salesforce=5, phonepe=4, paypal=5, goldman_sachs=5)},
         ]},
        {"id": "dbms.concurrency", "label": "Concurrency & Isolation",
         "description": "How the DB stays correct under parallel load.",
         "topics": [
            {"id": "dbms.concurrency.isolation", "label": "Isolation Levels",
             "description": "Read-uncommitted → Serializable and their anomalies.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "prerequisites": ["dbms.relational.acid"],
             "tags": ["isolation"]},
            {"id": "dbms.concurrency.control", "label": "Concurrency Control",
             "description": "2PL, MVCC, optimistic locking.",
             "estimated_minutes": 60, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.4,
             "tags": ["concurrency"]},
            {"id": "dbms.concurrency.deadlocks", "label": "DB Deadlocks",
             "description": "Detection, prevention and wait-for graphs.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["deadlock"]},
         ]},
        {"id": "dbms.nosql", "label": "NoSQL",
         "description": "The non-relational family.",
         "topics": [
            {"id": "dbms.nosql.kv", "label": "Key-Value Stores",
             "description": "Redis, DynamoDB, memcached.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.2,
             "tags": ["nosql", "kv"]},
            {"id": "dbms.nosql.document", "label": "Document Stores",
             "description": "MongoDB, Couchbase; schema-on-read.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["nosql", "mongo"]},
            {"id": "dbms.nosql.column", "label": "Column-Family Stores",
             "description": "Cassandra, HBase, BigTable.",
             "estimated_minutes": 30, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["nosql", "cassandra"]},
            {"id": "dbms.nosql.graph", "label": "Graph Databases",
             "description": "Neo4j; property-graph model.",
             "estimated_minutes": 25, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["nosql", "graph"]},
         ]},
        {"id": "dbms.scaling", "label": "Scaling",
         "description": "Horizontal scaling of persistence.",
         "topics": [
            {"id": "dbms.scaling.sharding", "label": "Sharding",
             "description": "Range, hash, directory-based.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["sharding"]},
            {"id": "dbms.scaling.replication", "label": "Replication",
             "description": "Master-slave, master-master, quorum reads/writes.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["replication"]},
         ]},
        # Curriculum sync (2026) — canonical Modules 11-12 "Storage Internals" / "Database
        # Architecture" are named in the source doc's module list but the doc supplies no
        # granular "Major Areas" content for them (boilerplate placeholder, like every other
        # DBMS module) — only the module names themselves are canonical. Added as minimal,
        # traceable stubs; no fine-grained content is invented beyond well-established DB
        # engineering vocabulary.
        {"id": "dbms.internals", "label": "Storage & Architecture Internals",
         "description": "How a database engine is put together under the query layer.",
         "topics": [
            {"id": "dbms.internals.storage", "label": "Storage Internals",
             "description": "Page/block layout, heap files, buffer pool, write-ahead logging (WAL).",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 2, "mastery_weight": 1.1,
             "prerequisites": ["dbms.relational.indexing"],
             "tags": ["storage-internals", "wal"]},
            {"id": "dbms.internals.architecture", "label": "Database Architecture",
             "description": "Query parser, planner/optimizer, executor and storage-engine layering "
                            "inside a typical RDBMS.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "tags": ["architecture"]},
         ]},
        # Curriculum sync (2026) — canonical Module 17 "Data Warehousing" (same boilerplate-only
        # doc treatment as above).
        {"id": "dbms.warehousing", "label": "Data Warehousing",
         "description": "Analytical (OLAP) storage vs transactional (OLTP) storage. The track's "
                        "capstone — other subjects' subject-level prerequisites point here.",
         "topics": [
            {"id": "dbms.warehousing.core", "label": "OLAP, Star Schema & ETL",
             "description": "OLTP vs OLAP, star/snowflake schema, fact/dimension tables, ETL "
                            "pipelines.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 1.0,
             "prerequisites": ["dbms.internals.architecture"],
             "tags": ["olap", "data-warehouse", "etl"]},
         ]},
    ],
}


# ---------------------------------------------------------------------------
# COMPUTER NETWORKS
# ---------------------------------------------------------------------------

CN_TRACK = {
    "id": "computer_networks", "label": "Computer Networks", "icon": "wifi",
    "description": "How bytes get from your browser to a backend and back.",
    "interview_importance": 3,
    "company_importance": ci(google=3, microsoft=3, atlassian=3, uber=4, adobe=3, linkedin=3,
                              stripe=3, salesforce=3, oracle=3, phonepe=3, flipkart=3,
                              paypal=3, goldman_sachs=3, zoho=4),
    "tags": ["networking"],
    "modules": [
        {"id": "cn.foundations", "label": "Foundations",
         "description": "Layered model and the transport protocols.",
         "topics": [
            {"id": "cn.foundations.osi", "label": "OSI vs TCP-IP Model",
             "description": "Layers, PDUs, encapsulation.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 4, "mastery_weight": 1.1,
             # Curriculum sync (2026) — CN's canonical "Prerequisite Subjects": Programming
             # Fundamentals, Java, Data Structures & Algorithms, Operating Systems. This is CN's
             # entry leaf.
             "prerequisites": ["pf.professional_engineering.core", "java.enterprise.core",
                              "dsa.advanced.segment_tree.range_sum", "os.modern_engineering.core"],
             "tags": ["osi"]},
            {"id": "cn.foundations.tcp_ip", "label": "TCP / IP",
             "description": "3-way handshake, flow control, congestion control.",
             "estimated_minutes": 60, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["tcp"]},
            {"id": "cn.foundations.udp", "label": "UDP & Use-Cases",
             "description": "Best-effort transport; when to prefer UDP.",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 0.9,
             "tags": ["udp"]},
            {"id": "cn.foundations.http_https", "label": "HTTP & HTTPS",
             "description": "Verbs, status codes, headers, cookies.",
             "estimated_minutes": 45, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.4,
             "tags": ["http"]},
            {"id": "cn.foundations.http2_http3", "label": "HTTP/2 & HTTP/3",
             "description": "Multiplexing, header compression, QUIC.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["cn.foundations.http_https"],
             "tags": ["http2", "http3"]},
            {"id": "cn.foundations.dns", "label": "DNS Resolution",
             "description": "Recursive vs iterative queries, records, propagation.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 4, "mastery_weight": 1.2,
             "tags": ["dns"]},
         ]},
        {"id": "cn.advanced", "label": "Advanced",
         "description": "Application-layer plumbing.",
         "topics": [
            {"id": "cn.advanced.tls_ssl", "label": "TLS / SSL",
             "description": "Handshake, cert chains, certificate pinning.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["cn.foundations.tcp_ip"],
             "tags": ["tls"]},
            {"id": "cn.advanced.load_balancing", "label": "Load Balancing (Network POV)",
             "description": "L4 vs L7, DSR, health-checks.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["load-balancing"]},
            {"id": "cn.advanced.cdn", "label": "CDN & Edge",
             "description": "Anycast, PoPs, cache hierarchy.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["cdn"]},
            {"id": "cn.advanced.websockets", "label": "WebSockets & Long-Poll",
             "description": "Full-duplex over TCP; when to pick which.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["websocket"]},
         ]},
        {"id": "cn.security", "label": "Security & Reliability",
         "description": "Perimeter and abuse-defense at the network layer.",
         "topics": [
            {"id": "cn.security.firewalls", "label": "Firewalls & NAT",
             "description": "Stateful vs stateless firewalls, NAT traversal.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["firewall"]},
            {"id": "cn.security.ddos", "label": "DDoS Protection",
             "description": "Rate limiting, scrubbing, anycast.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["ddos"]},
         ]},
        # ------------------------------------------------------------------
        # Curriculum sync (2026) — canonical Modules 5, 7, 8, 11, 12, 13, 16, 17, 18(partial), 19
        # were entirely absent despite the CN doc being richly authored (v2.0, non-boilerplate).
        # ------------------------------------------------------------------
        {"id": "cn.addressing", "label": "Addressing & the Data Link Layer",
         "description": "How devices are identified at Layer 2 and Layer 3.",
         "topics": [
            {"id": "cn.addressing.ip", "label": "IP Addressing & Subnetting",
             "description": "IPv4 & IPv6, CIDR notation, subnetting, NAT, PAT, ICMP.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "prerequisites": ["cn.foundations.tcp_ip"],
             "tags": ["ip-addressing", "cidr", "subnetting", "nat"]},
            {"id": "cn.addressing.datalink", "label": "Data Link Layer & Network Devices",
             "description": "MAC addressing, ARP, Ethernet, VLANs, CRC, and the devices (hubs, "
                            "switches, routers, access points) that make up a network.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["cn.addressing.ip"],
             "tags": ["mac", "arp", "vlan", "network-devices"]},
         ]},
        {"id": "cn.routing_switching", "label": "Routing, Switching & Network Services",
         "description": "How packets find their way and how core network services support them.",
         "topics": [
            {"id": "cn.routing_switching.routing", "label": "Routing & Switching",
             "description": "RIP, OSPF, BGP, ECMP routing; MAC learning, CAM table, VLAN trunking, "
                            "Spanning Tree Protocol.",
             "estimated_minutes": 45, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["cn.addressing.datalink"],
             "tags": ["routing", "bgp", "ospf", "switching", "stp"]},
            {"id": "cn.routing_switching.services", "label": "Network Services & Transport Internals",
             "description": "DHCP, reverse proxy; sliding-window flow control, congestion avoidance, "
                            "sockets and ports underneath the TCP handshake.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "prerequisites": ["cn.foundations.dns"],
             "tags": ["dhcp", "proxy", "congestion-control", "sockets"]},
         ]},
        {"id": "cn.cloud_networking", "label": "Cloud & Distributed Networking",
         "description": "How networking works once workloads move into the cloud and microservices.",
         "topics": [
            {"id": "cn.cloud_networking.cloud", "label": "Cloud Networking",
             "description": "VPCs, public/private subnets, security groups vs NACLs, NAT gateway, "
                            "VPC peering, hybrid cloud connectivity.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["cn.routing_switching.services"],
             "tags": ["vpc", "cloud-networking", "security-groups"]},
            {"id": "cn.cloud_networking.distributed", "label": "Distributed Networking & Modern Protocols",
             "description": "Service discovery, API gateway, service mesh, Kubernetes networking, "
                            "sidecar pattern, gRPC and MQTT.",
             "estimated_minutes": 40, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["cn.cloud_networking.cloud"],
             "tags": ["service-mesh", "api-gateway", "grpc"]},
         ]},
        {"id": "cn.production", "label": "Networking in Production Systems",
         "description": "Bridging networking theory with real-world production architectures. The "
                        "track's capstone — other subjects' subject-level prerequisites point here.",
         "topics": [
            {"id": "cn.production.core", "label": "CDN Architecture, Global LB & Network Observability",
             "description": "End-to-end request lifecycle, CDN architecture, global load balancing "
                            "and geo-routing, multi-region deployment, network observability.",
             "estimated_minutes": 40, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "prerequisites": ["cn.cloud_networking.distributed"],
             "tags": ["cdn", "global-load-balancing", "observability"]},
         ]},
    ],
}


# ---------------------------------------------------------------------------
# PROJECTS · Behavioral · Resume (new "beyond-code" tracks)
# ---------------------------------------------------------------------------

PROJECTS_TRACK = {
    "id": "projects", "label": "Projects", "icon": "hammer",
    "description": "Portfolio-worthy projects that make your resume actually stand out.",
    "interview_importance": 3,
    "company_importance": ci(google=3, microsoft=3, atlassian=4, uber=3, adobe=3, linkedin=4,
                              stripe=4, salesforce=3, oracle=3, phonepe=3, flipkart=3,
                              paypal=3, goldman_sachs=3, zoho=4),
    "tags": ["projects", "portfolio"],
    "modules": [
        {"id": "projects.build", "label": "Build",
         "description": "Ship something end-to-end you can talk about for 20 minutes.",
         "topics": [
            {"id": "projects.build.url_shortener", "label": "Ship a URL Shortener",
             "description": "Full-stack app with a real DB, cache and auth.",
             "estimated_minutes": 600, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["fullstack"]},
            {"id": "projects.build.chat_app", "label": "Ship a Chat App",
             "description": "WebSockets, rooms, presence and message history.",
             "estimated_minutes": 720, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "tags": ["realtime"]},
            {"id": "projects.build.ecommerce", "label": "Ship a Mini E-Commerce",
             "description": "Cart, checkout, order state machine, payments (Stripe test).",
             "estimated_minutes": 900, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "tags": ["fullstack", "commerce"]},
            {"id": "projects.build.saas_dashboard", "label": "Ship a SaaS Dashboard",
             "description": "Auth, RBAC, billing, analytics — a mini Linear/Vercel.",
             "estimated_minutes": 900, "difficulty": "hard", "interview_frequency": 3, "mastery_weight": 1.3,
             "tags": ["saas"]},
         ]},
        {"id": "projects.showcase", "label": "Showcase",
         "description": "How to talk about what you built.",
         "topics": [
            {"id": "projects.showcase.readme", "label": "Write a Great README",
             "description": "Purpose, screenshots, architecture, run instructions.",
             "estimated_minutes": 60, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 0.9,
             "tags": ["storytelling"]},
            {"id": "projects.showcase.arch_diagram", "label": "Draw an Architecture Diagram",
             "description": "System-design style diagram + component call-outs.",
             "estimated_minutes": 90, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["storytelling"]},
            {"id": "projects.showcase.demo_video", "label": "Record a 90-Second Demo",
             "description": "Loom-style walk-through recruiters actually watch.",
             "estimated_minutes": 45, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.8,
             "tags": ["storytelling"]},
         ]},
        {"id": "projects.deploy", "label": "Deploy & Operate",
         "description": "Production concerns interviewers love asking about.",
         "topics": [
            {"id": "projects.deploy.ci_cd", "label": "CI / CD Pipeline",
             "description": "GitHub Actions → build → test → deploy.",
             "estimated_minutes": 120, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["devops"]},
            {"id": "projects.deploy.observability", "label": "Observability",
             "description": "Structured logs + metrics + one dashboard.",
             "estimated_minutes": 90, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["devops"]},
        ]},
    ],
}


BEHAVIORAL_TRACK = {
    "id": "behavioral", "label": "Behavioral", "icon": "message-circle",
    "description": "Stories, salary conversations and the human side of the interview.",
    "interview_importance": 4,
    "company_importance": ci(google=5, microsoft=4, atlassian=5, uber=4, adobe=4, linkedin=5,
                              stripe=5, salesforce=4, oracle=3, phonepe=3, flipkart=3,
                              paypal=4, goldman_sachs=4, zoho=3),
    "tags": ["behavioral", "communication"],
    "modules": [
        {"id": "behavioral.framework", "label": "Framework",
         "description": "The structure interviewers score you against.",
         "topics": [
            {"id": "behavioral.framework.star", "label": "STAR Method",
             "description": "Situation / Task / Action / Result — 90-second stories.",
             "estimated_minutes": 45, "difficulty": "easy", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["framework"]},
            {"id": "behavioral.framework.carl", "label": "CARL & Other Variants",
             "description": "Alternatives for reflection-heavy questions.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["framework"]},
         ]},
        {"id": "behavioral.stories", "label": "Signature Stories",
         "description": "The 6-8 stories that answer 80% of behavioral questions.",
         "topics": [
            {"id": "behavioral.stories.leadership", "label": "Leadership Story",
             "description": "A time you led without authority.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.4,
             "tags": ["story"]},
            {"id": "behavioral.stories.conflict", "label": "Conflict Story",
             "description": "Disagreement with a teammate — resolution and lessons.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.4,
             "tags": ["story"]},
            {"id": "behavioral.stories.failure", "label": "Failure Story",
             "description": "What broke, what you did, what you learned.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.4,
             "tags": ["story"]},
            {"id": "behavioral.stories.ambiguity", "label": "Ambiguous Problem Story",
             "description": "Made a call with incomplete information.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.3,
             "tags": ["story"]},
            {"id": "behavioral.stories.impact", "label": "Impact Story",
             "description": "A time your work moved a metric.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.5,
             "tags": ["story"]},
         ]},
        {"id": "behavioral.company_values", "label": "Company Values",
         "description": "Company-specific behavioral loops.",
         "topics": [
            {"id": "behavioral.values.amazon_lp", "label": "Amazon Leadership Principles",
             "description": "16 LPs; expect 2-3 stories per interviewer.",
             "estimated_minutes": 120, "difficulty": "medium", "interview_frequency": 5, "mastery_weight": 1.6,
             "tags": ["amazon"],
             "company_importance": ci(google=2, microsoft=3, atlassian=3, uber=3, adobe=3, linkedin=3,
                                       stripe=3, salesforce=3, oracle=3, phonepe=3, flipkart=3,
                                       paypal=3, goldman_sachs=3, zoho=3)},
            {"id": "behavioral.values.googleyness", "label": "Googleyness",
             "description": "Comfort with ambiguity, bias for action, collaboration.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 4, "mastery_weight": 1.2,
             "tags": ["google"],
             "company_importance": ci(google=5)},
         ]},
        {"id": "behavioral.negotiation", "label": "Offer & Negotiation",
         "description": "The 10-minute conversation worth ~$50k over 4 years.",
         "topics": [
            {"id": "behavioral.negotiation.competing_offers", "label": "Competing Offers",
             "description": "How to leverage them without burning bridges.",
             "estimated_minutes": 45, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.2,
             "tags": ["negotiation"]},
            {"id": "behavioral.negotiation.scripts", "label": "Negotiation Scripts",
             "description": "Exact wording for base / stock / sign-on asks.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["negotiation"]},
         ]},
    ],
}


RESUME_TRACK = {
    "id": "resume", "label": "Resume & LinkedIn", "icon": "file-text",
    "description": "The one-page artifact recruiters spend 7 seconds on.",
    "interview_importance": 3,
    "company_importance": ci(google=3, microsoft=3, atlassian=4, uber=3, adobe=3, linkedin=5,
                              stripe=3, salesforce=3, oracle=3, phonepe=3, flipkart=3,
                              paypal=3, goldman_sachs=3, zoho=3),
    "tags": ["resume", "linkedin"],
    "modules": [
        {"id": "resume.craft", "label": "Craft",
         "description": "The mechanics of a screen-passing resume.",
         "topics": [
            {"id": "resume.craft.format", "label": "One-Page Format",
             "description": "Section order, whitespace, font choices that actually work.",
             "estimated_minutes": 45, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["format"]},
            {"id": "resume.craft.action_verbs", "label": "Action Verbs & Metrics",
             "description": "Every bullet: verb + what + measurable impact.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 4, "mastery_weight": 1.2,
             "tags": ["writing"]},
            {"id": "resume.craft.ats", "label": "ATS Compatibility",
             "description": "Beat the parser: no tables, no columns, plain fonts.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["ats"]},
            {"id": "resume.craft.tailoring", "label": "Job-Specific Tailoring",
             "description": "Swap 3-5 keywords per JD; keep the story consistent.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.1,
             "tags": ["writing"]},
         ]},
        {"id": "resume.linkedin", "label": "LinkedIn",
         "description": "The passive-recruiter-magnet channel.",
         "topics": [
            {"id": "resume.linkedin.headline", "label": "Headline & About",
             "description": "The two fields recruiters actually search.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["linkedin"]},
            {"id": "resume.linkedin.projects", "label": "Featured Projects",
             "description": "Pin 2-3 items above the fold with visuals.",
             "estimated_minutes": 20, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.8,
             "tags": ["linkedin"]},
            {"id": "resume.linkedin.recos", "label": "Recommendations",
             "description": "Give first — receive back within a week.",
             "estimated_minutes": 30, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.8,
             "tags": ["linkedin"]},
         ]},
        {"id": "resume.cover", "label": "Cover Letters & Outreach",
         "description": "The message that gets the recruiter to read your resume.",
         "topics": [
            {"id": "resume.cover.letter", "label": "Cover Letter Template",
             "description": "Three-paragraph structure that references the JD.",
             "estimated_minutes": 45, "difficulty": "easy", "interview_frequency": 2, "mastery_weight": 0.9,
             "tags": ["writing"]},
            {"id": "resume.cover.cold_outreach", "label": "Cold Outreach",
             "description": "DM template + follow-up cadence.",
             "estimated_minutes": 30, "difficulty": "medium", "interview_frequency": 3, "mastery_weight": 1.0,
             "tags": ["outreach"]},
        ]},
    ],
}


TRACKS: list[dict] = [PF_TRACK, DSA_TRACK, JAVA_TRACK, LLD_TRACK, HLD_TRACK, OS_TRACK, DBMS_TRACK, CN_TRACK,
                       PROJECTS_TRACK, BEHAVIORAL_TRACK, RESUME_TRACK]


# ---------------------------------------------------------------------------
# Post-processing — attach ambient metadata to every node
# ---------------------------------------------------------------------------

_DEFAULT_INTERVIEW_FREQUENCY = 3
_DEFAULT_MASTERY_WEIGHT = 1.0
_DEFAULT_ESTIMATED_MINUTES = 30

# RC1.3.7 Phase 5 — derived (never fabricated) leaf-level metadata.
# `interview_importance` was previously authored ONLY on the 10 track
# objects (a UI label there) and always absent on topic/subtopic/node
# leaves — `ranking.py`'s urgency bonus already reads
# `float(node.get("interview_importance") or 0.0)` expecting the SAME 0-5
# numeric scale as `interview_frequency`, so it was silently a permanent
# no-op for every real candidate. Stamping the numeric value here (mirrored
# from the node's own `interview_frequency`, itself already populated on
# essentially every node) activates that existing, previously-dead ranking
# term for the first time — purely additive, backward compatible (old
# behavior was "always +0 from this term"; the field's type/scale is
# unchanged from what ranking.py already expected).
def _default_interview_importance(n: dict) -> int:
    return int(n.get("interview_frequency", _DEFAULT_INTERVIEW_FREQUENCY))


def _default_learning_objectives(n: dict, label: str) -> list[str]:
    """Template objectives strictly from fields already authored on the node.

    Never invents curriculum content — only restates the node's own label,
    pattern and problem linkage as learner-facing objective statements, so
    every node has non-empty `learning_objectives` (RC1.3.7 Phase 5) without
    fabricating new pedagogical facts.
    """
    objectives = [f"Explain the core idea behind {label}."]
    pattern = n.get("pattern")
    if pattern:
        objectives.append(f"Recognize when to apply the {pattern} pattern in an interview problem.")
    if n.get("problem_ids"):
        objectives.append(f"Independently solve the practice problems mapped to {label}.")
    objectives.append(f"Discuss the complexity and trade-offs of {label} out loud, interview-style.")
    return objectives
_DEFAULT_DIFFICULTY = "medium"

# ---------------------------------------------------------------------------
# RC1.3.5B · Part E — Learning stages
# ---------------------------------------------------------------------------
# Purely derived from the already-authored module taxonomy (no new per-node
# guesswork): every module id below was authored well before this pass and
# its pedagogical position in its track is unambiguous from its content.
# `learning_stage` is a UI/journey-grouping label only — it is never read by
# unlock/ranking/ROI logic, so it cannot change any gating behavior.
_MODULE_LEARNING_STAGE: dict[str, str] = {
    # Programming Fundamentals (2026 curriculum sync — mirrors its own strictly
    # sequential "Unlocks" progression: syntax/mechanics -> core control-flow ->
    # complexity/quality practices -> professional-engineering mindset).
    "pf.intro": "foundation", "pf.computer_basics": "foundation", "pf.execution": "foundation",
    "pf.problem_solving": "foundation", "pf.variables": "foundation", "pf.data_types": "foundation",
    "pf.operators": "foundation", "pf.io": "foundation",
    "pf.control_flow": "core", "pf.functions": "core", "pf.arrays": "core", "pf.strings": "core",
    "pf.memory": "core", "pf.error_handling": "core", "pf.modular": "core", "pf.recursion": "core",
    "pf.complexity": "intermediate", "pf.searching": "intermediate", "pf.sorting": "intermediate",
    "pf.paradigms": "intermediate", "pf.code_quality": "intermediate", "pf.debugging": "intermediate",
    "pf.testing": "intermediate",
    "pf.swe_basics": "advanced", "pf.engineering_mindset": "advanced", "pf.design_thinking": "advanced",
    "pf.performance_awareness": "advanced", "pf.security_awareness": "advanced",
    "pf.professional_engineering": "advanced",
    # DSA
    "dsa.foundations": "foundation", "dsa.windows_search": "core",
    "dsa.linear_structures": "core", "dsa.trees_graphs": "intermediate",
    "dsa.priority": "intermediate", "dsa.dp_backtracking": "advanced",
    "dsa.advanced": "advanced",
    # Java
    "java.basics": "foundation", "java.oop": "core", "java.collections": "core",
    "java.generics_exceptions": "intermediate", "java.streams_lambdas": "intermediate",
    "java.concurrency": "advanced", "java.jvm": "advanced", "java.io_nio": "intermediate",
    # Java (2026 curriculum sync additions)
    "java.datetime_reflection": "intermediate", "java.modern": "advanced", "java.enterprise": "advanced",
    # LLD
    "lld.principles": "foundation", "lld.patterns": "core",
    "lld.uml_modelling": "core", "lld.cases": "interview",
    # LLD (2026 curriculum sync additions)
    "lld.craftsmanship": "core", "lld.production_components": "advanced",
    # HLD
    "hld.foundations": "foundation", "hld.caching": "core", "hld.databases": "core",
    "hld.messaging": "intermediate", "hld.distributed": "advanced",
    "hld.security": "advanced", "hld.cases": "interview",
    # HLD (2026 curriculum sync additions)
    "hld.architecture": "advanced", "hld.platform": "advanced",
    # OS
    "os.foundations": "foundation", "os.processes": "core",
    "os.memory": "intermediate", "os.filesystems": "intermediate",
    # OS (2026 curriculum sync additions)
    "os.security": "intermediate", "os.multiprocessor": "intermediate",
    "os.distributed": "advanced", "os.virtualization": "advanced", "os.kernel": "advanced",
    "os.performance": "advanced", "os.reliability": "advanced", "os.modern_engineering": "advanced",
    # DBMS
    "dbms.relational": "foundation", "dbms.concurrency": "intermediate",
    "dbms.nosql": "core", "dbms.scaling": "advanced",
    # DBMS (2026 curriculum sync additions)
    "dbms.internals": "advanced", "dbms.warehousing": "advanced",
    # Computer Networks
    "cn.foundations": "foundation", "cn.advanced": "intermediate", "cn.security": "advanced",
    # Computer Networks (2026 curriculum sync additions)
    "cn.addressing": "intermediate", "cn.routing_switching": "intermediate",
    "cn.cloud_networking": "advanced", "cn.production": "advanced",
}
_LEARNING_STAGE_MODULE_PREFIXES: list[tuple[str, str]] = [
    ("lld.cat.", "interview"), ("hld.cat.", "interview"),
]
_LEARNING_STAGE_TRACK_FALLBACK = {
    "projects": "company_specific", "behavioral": "company_specific", "resume": "company_specific",
}


def _infer_learning_stage(track_id: str, module_id: str) -> str:
    if module_id in _MODULE_LEARNING_STAGE:
        return _MODULE_LEARNING_STAGE[module_id]
    for prefix, stage in _LEARNING_STAGE_MODULE_PREFIXES:
        if module_id.startswith(prefix):
            return stage
    return _LEARNING_STAGE_TRACK_FALLBACK.get(track_id, "core")


# ---------------------------------------------------------------------------
# Curriculum Sync Phase 2 — metadata-only prerequisite/unlock/level/source
# annotations (docs/curriculum/governance/01-curriculum-synchronization-contract.md).
# None of this is read by roadmap.py's unlock/ranking/ROI engines (which only
# ever consult `prerequisites`/`learning_stage`) — it is purely additive,
# queryable curriculum metadata layered on top of the existing, already-
# enforced graph. A later phase may choose to enforce it at runtime.
# ---------------------------------------------------------------------------

# Mirrors docs/curriculum/governance/00-curriculum-principles.md's canonical
# 5-level framework (Foundation/Basic/Intermediate/Advanced/Expert), derived
# from the already-existing `learning_stage` enum — never a second source of
# truth for pedagogical position, just a relabeling into the constitution's
# own vocabulary.
_CURRICULUM_LEVEL_LABELS: dict[str, str] = {
    "foundation": "Foundation",
    "core": "Basic",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
    "interview": "Expert",
    "company_specific": "Expert",
}


def _curriculum_level_label(stage: str) -> str:
    return _CURRICULUM_LEVEL_LABELS.get(stage, "Intermediate")


# Canonical subject dependency DAG (Curriculum Sync Phase 2 enrichment):
# Programming Fundamentals is the sole root. Java is the common gateway
# subject. DSA/DBMS/Operating Systems/Computer Networks all branch directly
# off Java (no artificial ordering between them). LLD depends on Java, DSA
# and Operating Systems. HLD depends on Java, DBMS, Operating Systems,
# Computer Networks and LLD. This replaces the earlier, too-restrictive
# linear chain with the true multi-parent curriculum dependency graph.
# Projects/Behavioral/Resume are intentionally absent \u2014 independent
# career-readiness tracks kept outside the academic prerequisite graph.
_SUBJECT_PREREQUISITES: dict[str, list[str]] = {
    "programming_fundamentals": [],
    "java": ["programming_fundamentals"],
    "dsa": ["java"],
    "dbms": ["java"],
    "operating_systems": ["java"],
    "computer_networks": ["java"],
    "lld": ["java", "dsa", "operating_systems"],
    "hld": ["java", "dbms", "operating_systems", "computer_networks", "lld"],
}

# Subjects that must remain isolated from the academic prerequisite graph
# (independent career-readiness tracks, per curriculum sync request item 3).
_ISOLATED_SUBJECTS: frozenset[str] = frozenset({"projects", "behavioral", "resume"})

# Future-ready, roadmap-wide programming-language metadata (item 4). Advisory
# only \u2014 not read by onboarding or any runtime engine. Structured as a list
# so additional languages can be appended later without changing the
# roadmap's structure. Java is the only supported language today.
_LANGUAGE_SUPPORT_METADATA: dict = {
    "primary_language_supported": "java",
    "supported_languages": ["java"],
    "language_family": {"java": "jvm_object_oriented"},
}

# Canonical curriculum markdown each subject track was generated from —
# traceability only, not a live parser (docs/curriculum/subjects/0N-*.md).
_SUBJECT_SOURCE_ANCHOR: dict[str, str] = {
    "programming_fundamentals": "docs/curriculum/subjects/01-programming-fundamentals.md",
    "java": "docs/curriculum/subjects/02-java.md",
    "dsa": "docs/curriculum/subjects/03-dsa.md",
    "dbms": "docs/curriculum/subjects/04-dbms.md",
    "operating_systems": "docs/curriculum/subjects/05-operating-systems.md",
    "computer_networks": "docs/curriculum/subjects/06-computer-networks.md",
    "lld": "docs/curriculum/subjects/07-lld.md",
    "hld": "docs/curriculum/subjects/08-hld.md",
}


def _collect_production_application(node: dict) -> list[str]:
    """Companies whose authored `company_importance` for a descendant leaf is
    genuinely differentiated from the flat default — never fabricated, just
    surfaces already-authored per-node company signal at module granularity
    as "which real companies' production interviews this content is
    demonstrably weighted toward"."""
    companies: set[str] = set()

    def visit(n: dict) -> None:
        for company, weight in (n.get("company_importance") or {}).items():
            if weight != _DEFAULT_INTERVIEW_FREQUENCY:
                companies.add(company)
        for key in ("modules", "topics", "subtopics", "learning_nodes"):
            for c in n.get(key, []) or []:
                visit(c)

    visit(node)
    return sorted(companies)


def _stamp_defaults(n: dict, *, track_id: str, module_id: str, category_id: str, level: str, order: int) -> None:
    """Attach metadata every node needs. Never overwrites explicit values."""
    n.setdefault("description", "")
    n.setdefault("difficulty", _DEFAULT_DIFFICULTY)
    n.setdefault("estimated_minutes", _DEFAULT_ESTIMATED_MINUTES)
    n.setdefault("interview_frequency", _DEFAULT_INTERVIEW_FREQUENCY)
    n.setdefault("mastery_weight", _DEFAULT_MASTERY_WEIGHT)
    n.setdefault("prerequisites", [])
    n.setdefault("related", [])
    n.setdefault("company_importance", {c: _DEFAULT_INTERVIEW_FREQUENCY for c in COMPANIES})
    n.setdefault("tags", [])
    n["track"] = track_id
    n["module"] = module_id
    n["category"] = category_id
    n["level"] = level
    n["order"] = order
    n["revision_bucket"] = n.get("revision_bucket", "green")
    n["status"] = n.get("status", "available" if level in ("track", "module") else "locked")
    n["version"] = VERSION
    if level in ("topic", "subtopic", "node"):
        n.setdefault("learning_stage", _infer_learning_stage(track_id, module_id))
        n.setdefault("interview_importance", _default_interview_importance(n))
        n.setdefault("learning_objectives", _default_learning_objectives(n, n.get("label", n["id"])))
        n.setdefault("curriculum_level", _curriculum_level_label(n["learning_stage"]))
    # Phase 3C.1 freeze: activity_type + assessment_type are curriculum metadata
    # stamped onto EVERY node here (build-time), so no runtime module infers them.
    stamp_node(n, track_id)



def _walk_and_stamp(track: dict) -> None:
    track_id = track["id"]
    _stamp_defaults(track, track_id=track_id, module_id="", category_id="", level="track", order=0)
    for m_idx, module in enumerate(track.get("modules", []) or []):
        _stamp_defaults(module, track_id=track_id, module_id=module["id"], category_id="", level="module", order=m_idx)
        for t_idx, topic in enumerate(module.get("topics", []) or []):
            _stamp_defaults(topic, track_id=track_id, module_id=module["id"], category_id=topic["id"], level="topic", order=t_idx)
            # subtopics
            for st_idx, sub in enumerate(topic.get("subtopics", []) or []):
                _stamp_defaults(sub, track_id=track_id, module_id=module["id"], category_id=topic["id"], level="subtopic", order=st_idx)
                for ln_idx, ln in enumerate(sub.get("learning_nodes", []) or []):
                    _stamp_defaults(ln, track_id=track_id, module_id=module["id"], category_id=topic["id"], level="node", order=ln_idx)
            # learning nodes directly on topic
            for ln_idx, ln in enumerate(topic.get("learning_nodes", []) or []):
                _stamp_defaults(ln, track_id=track_id, module_id=module["id"], category_id=topic["id"], level="node", order=ln_idx)


def _validate_dag(all_ids: set[str], all_nodes: list[dict]) -> None:
    """Verify all prerequisites reference known IDs and there are no cycles."""
    graph: dict[str, list[str]] = {}
    for n in all_nodes:
        deps = n.get("prerequisites") or []
        for d in deps:
            if d not in all_ids:
                raise ValueError(f"Node '{n['id']}' references unknown prerequisite '{d}'")
        graph[n["id"]] = list(deps)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in graph}

    def dfs(u: str, path: list[str]) -> None:
        color[u] = GRAY
        for v in graph.get(u, []):
            if color.get(v, WHITE) == GRAY:
                raise ValueError(f"Cycle detected in prerequisites: {' -> '.join(path + [u, v])}")
            if color.get(v, WHITE) == WHITE:
                dfs(v, path + [u])
        color[u] = BLACK

    for nid in list(graph.keys()):
        if color[nid] == WHITE:
            dfs(nid, [])


def _validate_metadata_integrity(all_nodes: list[dict], all_ids: set[str]) -> None:
    """RC1.3.7 Phase 10 \u2014 catch broken refs and invalid mappings at build time.

    Complements `_validate_dag` (which only checks `prerequisites`): verifies
    every hand- or auto-authored `related` id resolves to a real node, and
    every `company_importance` key is one of the canonical `COMPANIES` (the
    `amazon=` leak this replaces was exactly this class of bug).
    """
    valid_companies = set(COMPANIES)
    broken_related: list[tuple[str, str]] = []
    invalid_company_keys: list[tuple[str, str]] = []
    for n in all_nodes:
        for rid in n.get("related") or []:
            if rid not in all_ids:
                broken_related.append((n["id"], rid))
        for key in (n.get("company_importance") or {}):
            if key not in valid_companies:
                invalid_company_keys.append((n["id"], key))
    if broken_related:
        raise ValueError(f"Nodes reference unknown 'related' ids: {broken_related[:10]}")
    if invalid_company_keys:
        raise ValueError(f"Nodes contain invalid company_importance keys: {invalid_company_keys[:10]}")


def _collect_all_nodes(tracks: list[dict]) -> list[dict]:
    out: list[dict] = []

    def visit(n: dict) -> None:
        out.append(n)
        for key in ("modules", "topics", "subtopics", "learning_nodes"):
            for c in n.get(key, []) or []:
                visit(c)

    for t in tracks:
        visit(t)
    return out


# ---------------------------------------------------------------------------
# RC1.3.5B · Part C — Prerequisite-graph repairs
# ---------------------------------------------------------------------------

def _leaf_entry_id(node_id: str, by_id: dict) -> str | None:
    """Resolve any node id to its first real leaf.

    Container nodes (a topic with `subtopics`/`learning_nodes`, e.g. an HLD
    case study's 10-part breakdown or a GoF pattern's 5-part breakdown) are
    never themselves atomic learning nodes — only their leaves are (see
    `roadmap.RoadmapEngine._is_learning_node`). This walks the *first*
    child repeatedly until it reaches a node with no children, which is
    exactly the node authors intend a reader to start with.
    """
    seen: set[str] = set()
    current = node_id
    while True:
        if current in seen or current not in by_id:
            return None
        seen.add(current)
        n = by_id[current]
        children = n.get("subtopics") or n.get("learning_nodes") or []
        if not children:
            return current
        current = children[0]["id"]


def _all_leaf_ids(node_id: str, by_id: dict) -> list[str]:
    """Resolve any node id to EVERY real descendant leaf reachable from it.

    Container nodes (a topic with `subtopics`/`learning_nodes`, e.g. an HLD
    case study's 10-part breakdown or a GoF pattern's 5-part breakdown) are
    never themselves atomic learning nodes — only their leaves are (see
    `roadmap.RoadmapEngine._is_learning_node`). Unlike `_leaf_entry_id`
    (which only walks the first child chain), this walks every branch —
    required so a container-authored prerequisite gates the WHOLE subtree,
    not just its first sibling branch (RC1.3.6A: previously only
    `dsa.dp.1d.*` inherited `dsa.dp.core`'s gate while `dsa.dp.unbounded.*`
    / `dsa.dp.2d.*` / etc. stayed silently prerequisite-free).
    """
    out: list[str] = []
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        if current in seen or current not in by_id:
            continue
        seen.add(current)
        n = by_id[current]
        children = n.get("subtopics") or n.get("learning_nodes") or []
        if children:
            stack.extend(c["id"] for c in children)
        else:
            out.append(current)
    return out


def _propagate_container_prerequisites(all_nodes: list[dict], by_id: dict) -> None:
    """Make container-level `prerequisites` authoring actually enforceable.

    A `prerequisites` list authored on a non-leaf topic (e.g.
    `dsa.foundations.hashing` requiring `java.collections.hashmap`, or an
    HLD case study requiring `hld.caching.redis`) was previously dead
    metadata: `roadmap.is_unlocked` only ever inspects leaf learning nodes,
    so nothing enforced it. This resolves both sides of every such edge
    down to real leaves — EVERY leaf reachable under the container inherits
    the requirement (RC1.3.6A: fixed from only the first-child-chain leaf),
    and any prerequisite id that itself points at a container is resolved
    to *its* first entry leaf — so every authored edge becomes a real,
    enforceable leaf-to-leaf dependency. Purely additive: it only appends
    ids to a leaf's existing `prerequisites` list, never removes any, never
    duplicates an id already present, and never lets a leaf list itself.
    """
    for n in all_nodes:
        children = n.get("subtopics") or n.get("learning_nodes") or []
        prereqs = n.get("prerequisites") or []
        if not children or not prereqs:
            continue
        leaf_ids = [lid for lid in _all_leaf_ids(n["id"], by_id) if lid != n["id"]]
        if not leaf_ids:
            continue
        resolved_prereqs: list[str] = []
        for pid in prereqs:
            resolved = _leaf_entry_id(pid, by_id) or pid
            if resolved not in resolved_prereqs:
                resolved_prereqs.append(resolved)
        for leaf_id in leaf_ids:
            entry = by_id.get(leaf_id)
            if entry is None:
                continue
            existing = list(entry.get("prerequisites") or [])
            for resolved in resolved_prereqs:
                if resolved != leaf_id and resolved not in existing:
                    existing.append(resolved)
            entry["prerequisites"] = existing


# Case-study modules whose leaf topics previously had zero prerequisites in
# large numbers (RC1.3.5A: 97.6% of LLD case studies, ~most HLD case
# studies) — each gets its foundational gate wired in one deterministic
# pass instead of hand-editing every individual case study.
_LLD_CASE_STUDY_MODULE_PREFIXES = ("lld.cases", "lld.cat.")
_HLD_CASE_STUDY_MODULE_PREFIXES = ("hld.cases", "hld.cat.")


def _wire_case_study_prerequisites(all_nodes: list[dict]) -> None:
    """Give every previously-isolated LLD/HLD case study its foundational gate.

    Only touches topics whose `prerequisites` list is still empty after
    authoring (never overrides an explicitly authored prerequisite, e.g.
    `lld.cases.lru_cache` keeps its `dsa.linear.linked_list.lru` edge).
    Runs before `_propagate_container_prerequisites` so HLD case studies
    (which have a 10-part `subtopics` breakdown and are therefore
    containers, not leaves) get this new edge correctly resolved down to
    their `.problem` entry leaf.
    """
    for n in all_nodes:
        if n.get("level") != "topic" or (n.get("prerequisites") or []):
            continue
        module_id = n.get("module") or ""
        if module_id.startswith(_LLD_CASE_STUDY_MODULE_PREFIXES):
            n["prerequisites"] = ["lld.principles.solid.dip"]
        elif module_id.startswith(_HLD_CASE_STUDY_MODULE_PREFIXES):
            n["prerequisites"] = ["hld.foundations.scalability", "hld.foundations.cap"]


def _auto_link_related(tracks: list[dict], all_nodes: list[dict]) -> None:
    """Populate `related` for every node so the Deep Topic UI has real edges.

    Three signal sources, deduped and capped to keep the UI readable:
      1. Sibling nodes at the same level (same immediate parent).
      2. Pattern-mates across the whole graph (same `pattern` field).
      3. Reverse prerequisite edges — if A prereqs B, then A is related to B.
    """
    by_id = {n["id"]: n for n in all_nodes}

    # Build parent → children map.
    parent_of: dict[str, str] = {}

    def index_children(parent_id: str, kids: list[dict]) -> None:
        for k in kids or []:
            parent_of[k["id"]] = parent_id
            for key in ("modules", "topics", "subtopics", "learning_nodes"):
                index_children(k["id"], k.get(key) or [])

    for t in tracks:
        for key in ("modules", "topics", "subtopics", "learning_nodes"):
            index_children(t["id"], t.get(key) or [])

    # 1. Sibling links.
    siblings_by_parent: dict[str, list[str]] = {}
    for nid, pid in parent_of.items():
        siblings_by_parent.setdefault(pid, []).append(nid)

    # 2. Pattern buckets.
    pattern_buckets: dict[str, list[str]] = {}
    for n in all_nodes:
        pat = n.get("pattern")
        if pat:
            pattern_buckets.setdefault(pat, []).append(n["id"])

    # 3. Reverse prereq edges.
    reverse_prereqs: dict[str, list[str]] = {}
    for n in all_nodes:
        for pre in n.get("prerequisites") or []:
            reverse_prereqs.setdefault(pre, []).append(n["id"])

    LEAF_LEVELS = {"topic", "subtopic", "node"}
    MAX_RELATED = 8

    for n in all_nodes:
        if n.get("level") not in LEAF_LEVELS:
            continue
        already = set(n.get("related") or [])
        pid = parent_of.get(n["id"])
        siblings = [x for x in siblings_by_parent.get(pid, []) if x != n["id"]] if pid else []
        pattern_mates = [x for x in pattern_buckets.get(n.get("pattern") or "", []) if x != n["id"]]
        rev = reverse_prereqs.get(n["id"], [])

        # Merge in priority order: reverse-deps first (strongest signal),
        # then siblings, then pattern-mates. Dedup and cap.
        ordered: list[str] = []
        for src in (rev, siblings, pattern_mates):
            for x in src:
                if x in already or x in ordered:
                    continue
                if x not in by_id:
                    continue
                ordered.append(x)
                if len(ordered) >= MAX_RELATED:
                    break
            if len(ordered) >= MAX_RELATED:
                break

        n["related"] = list(n.get("related") or []) + ordered


def _annotate_curriculum_sync_metadata(tracks: list[dict]) -> None:
    """Curriculum Sync Phase 2 \u2014 stamp subject/module/topic prerequisite
    DAG edges, unlock chains, advisory next-subject recommendations,
    curriculum level, production application and source anchors. Purely
    metadata: nothing here is read by roadmap.py's unlock/ranking/ROI
    engines, so runtime gating behavior is unchanged.

    Subject-level dependency is the hardcoded canonical DAG in
    `_SUBJECT_PREREQUISITES` (subjects may have multiple parents, e.g. LLD
    and HLD); module/topic-level chains are derived purely from each
    track's own already-authored module/topic order plus that subject DAG
    \u2014 deterministic, nothing invented.
    """
    by_track = {t["id"]: t for t in tracks}
    module_by_id = {
        m["id"]: m for t in tracks for m in (t.get("modules") or [])
    }

    subject_unlocks: dict[str, list[str]] = {tid: [] for tid in by_track}
    for tid, prereqs in _SUBJECT_PREREQUISITES.items():
        for p in prereqs:
            subject_unlocks.setdefault(p, []).append(tid)

    for track in tracks:
        tid = track["id"]
        track["subject_prerequisites"] = list(_SUBJECT_PREREQUISITES.get(tid, []))
        track["subject_unlocks"] = list(subject_unlocks.get(tid, []))
        # Advisory-only navigation hint (item 2). Mirrors subject_unlocks
        # today but is a deliberately separate field name so a later phase
        # can diverge "what this unlocks" from "what we recommend next"
        # without touching the enforced/derived unlock chain.
        track["recommended_next_subjects"] = list(subject_unlocks.get(tid, []))
        anchor = _SUBJECT_SOURCE_ANCHOR.get(tid)
        track["source_anchor"] = anchor

        modules = track.get("modules") or []
        for m_idx, module in enumerate(modules):
            module_prereqs: list[str] = []
            if m_idx > 0:
                module_prereqs.append(modules[m_idx - 1]["id"])
            else:
                # First module of a subject: link to the LAST module of
                # EVERY prerequisite subject (a DAG node may have several
                # parents, e.g. LLD/HLD), not just a single predecessor.
                for prev_track_id in _SUBJECT_PREREQUISITES.get(tid) or []:
                    prev_modules = by_track.get(prev_track_id, {}).get("modules") or []
                    if prev_modules:
                        module_prereqs.append(prev_modules[-1]["id"])
            module["module_prerequisites"] = module_prereqs
            module["curriculum_level"] = _curriculum_level_label(_infer_learning_stage(tid, module["id"]))
            module["production_application"] = _collect_production_application(module)
            module_anchor = f"{anchor}#module-{m_idx + 1}" if anchor else None
            module["source_anchor"] = module_anchor

            topics = module.get("topics") or []
            for t_idx, topic in enumerate(topics):
                topic_prereqs: list[str] = []
                if t_idx > 0:
                    topic_prereqs.append(topics[t_idx - 1]["id"])
                else:
                    for prev_module_id in module_prereqs:
                        prev_module = module_by_id.get(prev_module_id)
                        prev_topics = (prev_module or {}).get("topics") or []
                        if prev_topics:
                            topic_prereqs.append(prev_topics[-1]["id"])
                topic["topic_prerequisites"] = topic_prereqs
                topic["source_anchor"] = module_anchor


def _validate_curriculum_sync_metadata(tracks: list[dict], all_ids: set[str]) -> None:
    """Curriculum Sync Phase 2 validation: prerequisite-graph integrity,
    unlock-chain correctness, no broken references, metadata completeness.
    """
    track_ids = {t["id"] for t in tracks}
    module_ids = {m["id"] for t in tracks for m in (t.get("modules") or [])}
    topic_ids = {
        top["id"] for t in tracks for m in (t.get("modules") or []) for top in (m.get("topics") or [])
    }

    # --- Subject-level graph integrity ---
    for t in tracks:
        for pid in t.get("subject_prerequisites") or []:
            if pid not in track_ids:
                raise ValueError(f"Track '{t['id']}' has unknown subject_prerequisites entry '{pid}'")
        for uid in t.get("subject_unlocks") or []:
            if uid not in track_ids:
                raise ValueError(f"Track '{t['id']}' has unknown subject_unlocks entry '{uid}'")
        for rid in t.get("recommended_next_subjects") or []:
            if rid not in track_ids:
                raise ValueError(f"Track '{t['id']}' has unknown recommended_next_subjects entry '{rid}'")

    # Career-readiness tracks must stay outside the academic prerequisite
    # graph entirely: no prerequisites/unlocks/recommendations in or out.
    for t in tracks:
        tid = t["id"]
        if tid in _ISOLATED_SUBJECTS:
            if t.get("subject_prerequisites") or t.get("subject_unlocks") or t.get("recommended_next_subjects"):
                raise ValueError(f"Isolated subject '{tid}' must have no academic prerequisite edges")
        else:
            if any(pid in _ISOLATED_SUBJECTS for pid in t.get("subject_prerequisites") or []):
                raise ValueError(f"Subject '{tid}' must not depend on an isolated career-readiness track")
            if any(uid in _ISOLATED_SUBJECTS for uid in t.get("subject_unlocks") or []):
                raise ValueError(f"Subject '{tid}' must not unlock an isolated career-readiness track")

    # Root subject: Programming Fundamentals must have zero prerequisites.
    pf = next((t for t in tracks if t["id"] == "programming_fundamentals"), None)
    if pf is None or pf.get("subject_prerequisites"):
        raise ValueError("'programming_fundamentals' must exist with empty subject_prerequisites")

    # Unlock chains must be the exact reverse of the prerequisite chain.
    by_track_id = {t["id"]: t for t in tracks}
    for t in tracks:
        for pid in t.get("subject_prerequisites") or []:
            if t["id"] not in (by_track_id[pid].get("subject_unlocks") or []):
                raise ValueError(f"'{pid}' subject_unlocks is missing reverse edge to '{t['id']}'")

    # No cycles in the subject-level dependency graph (a true DAG may have
    # multiple parents per node, e.g. LLD/HLD \u2014 the DFS below already
    # handles that generically).
    color: dict[str, int] = {t["id"]: 0 for t in tracks}

    def dfs(u: str, path: list[str]) -> None:
        color[u] = 1
        for v in by_track_id[u].get("subject_prerequisites") or []:
            if color.get(v) == 1:
                raise ValueError(f"Cycle in subject_prerequisites: {' -> '.join(path + [u, v])}")
            if color.get(v) == 0:
                dfs(v, path + [u])
        color[u] = 2

    for t in tracks:
        if color[t["id"]] == 0:
            dfs(t["id"], [])

    # --- Module/topic level: no broken references, no cycles ---
    for t in tracks:
        for module in t.get("modules") or []:
            for mid in module.get("module_prerequisites") or []:
                if mid not in module_ids:
                    raise ValueError(f"Module '{module['id']}' has unknown module_prerequisites entry '{mid}'")
            for req_key in ("curriculum_level", "production_application", "source_anchor", "module_prerequisites"):
                if req_key not in module:
                    raise ValueError(f"Module '{module['id']}' missing required metadata '{req_key}'")
            for topic in module.get("topics") or []:
                for tid2 in topic.get("topic_prerequisites") or []:
                    if tid2 not in topic_ids:
                        raise ValueError(f"Topic '{topic['id']}' has unknown topic_prerequisites entry '{tid2}'")
                for req_key in ("curriculum_level", "topic_prerequisites"):
                    if req_key not in topic:
                        raise ValueError(f"Topic '{topic['id']}' missing required metadata '{req_key}'")

    module_color: dict[str, int] = {mid: 0 for mid in module_ids}
    module_by_id_prereqs = {
        m["id"]: (m.get("module_prerequisites") or [])
        for t in tracks for m in (t.get("modules") or [])
    }

    def module_dfs(u: str, path: list[str]) -> None:
        module_color[u] = 1
        for v in module_by_id_prereqs.get(u, []):
            if module_color.get(v) == 1:
                raise ValueError(f"Cycle in module_prerequisites: {' -> '.join(path + [u, v])}")
            if module_color.get(v) == 0:
                module_dfs(v, path + [u])
        module_color[u] = 2

    for mid in list(module_ids):
        if module_color[mid] == 0:
            module_dfs(mid, [])


def _validate_language_support_metadata(language_support: dict) -> None:
    """Curriculum Sync Phase 2 validation for the future-ready, roadmap-wide
    programming-language metadata (item 4) — structural sanity only."""
    supported = language_support.get("supported_languages") or []
    primary = language_support.get("primary_language_supported")
    if primary is not None and primary not in supported:
        raise ValueError(f"primary_language_supported '{primary}' not present in supported_languages")
    for lang in (language_support.get("language_family") or {}):
        if lang not in supported:
            raise ValueError(f"language_family entry '{lang}' not present in supported_languages")


def build() -> dict:
    for track in TRACKS:
        _walk_and_stamp(track)

    all_nodes = _collect_all_nodes(TRACKS)
    ids = {n["id"] for n in all_nodes}
    if len(ids) != len(all_nodes):
        # find duplicates for error message
        seen: set[str] = set()
        dupes = []
        for n in all_nodes:
            if n["id"] in seen:
                dupes.append(n["id"])
            seen.add(n["id"])
        raise ValueError(f"Duplicate node ids: {dupes}")
    by_id = {n["id"]: n for n in all_nodes}
    _wire_case_study_prerequisites(all_nodes)
    _propagate_container_prerequisites(all_nodes, by_id)
    _validate_dag(ids, all_nodes)
    _auto_link_related(TRACKS, all_nodes)
    _validate_metadata_integrity(all_nodes, ids)
    _annotate_curriculum_sync_metadata(TRACKS)
    _validate_curriculum_sync_metadata(TRACKS, ids)
    _validate_language_support_metadata(_LANGUAGE_SUPPORT_METADATA)

    return {
        "version": VERSION,
        "generated_at": GENERATED_AT,
        "companies": COMPANIES,
        "tracks": TRACKS,
        "language_support": _LANGUAGE_SUPPORT_METADATA,
        "stats": {
            "total_nodes": len(all_nodes),
            "tracks": len(TRACKS),
        },
    }


def main() -> None:
    payload = build()
    out_path = Path(__file__).resolve().parent.parent / "data" / f"roadmap_{VERSION}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=False)
    print(f"Wrote {out_path}  ({payload['stats']['total_nodes']} nodes, {payload['stats']['tracks']} tracks)")


if __name__ == "__main__":
    main()
