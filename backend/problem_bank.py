"""Curated Problem Bank.

Internal catalog of coding problems mapped by pattern. Each problem has a
LeetCode URL (linked externally — we do NOT scrape). Mission Engine V2 picks
from this catalog based on topic/pattern and user history.
"""

# Pattern → domain mapping helps drill-down knowledge tree
PATTERN_TO_DOMAIN = {
    "arrays":             ("dsa", "Arrays"),
    "hashing":            ("dsa", "Hashing"),
    "sliding_window":     ("dsa", "Sliding Window"),
    "two_pointers":       ("dsa", "Two Pointers"),
    "binary_search":      ("dsa", "Binary Search"),
    "stack":              ("dsa", "Stack"),
    "linked_list":        ("dsa", "Linked List"),
    "trees":              ("dsa", "Trees & Recursion"),
    "graphs":             ("dsa", "Graphs"),
    "heap":               ("dsa", "Heaps & Priority Queues"),
    "dynamic_programming": ("dsa", "Dynamic Programming"),
    "backtracking":       ("dsa", "Backtracking"),
    "greedy":             ("dsa", "Greedy"),
    "strings":            ("dsa", "Strings"),
    "bit_manipulation":   ("dsa", "Bit Manipulation"),
    "intervals":          ("dsa", "Intervals"),
    # Sprint 2 additions
    "queue":                ("dsa", "Queue"),
    "trie":                 ("dsa", "Trie"),
    "union_find":           ("dsa", "Union Find"),
    "recursion":            ("dsa", "Recursion"),
    "sorting":              ("dsa", "Sorting"),
    "segment_tree":         ("dsa", "Segment Tree"),
}

# Prerequisite knowledge — used for root-cause analysis. When a user fails a
# pattern, we surface these prerequisites as revision blocks.
PATTERN_PREREQUISITES = {
    "heap":                 [("java", "Comparator & Comparable"), ("dsa", "Trees & Recursion")],
    "sliding_window":       [("dsa", "Two Pointers"), ("dsa", "Hashing")],
    "graphs":               [("dsa", "BFS & DFS"), ("dsa", "Stack")],
    "dynamic_programming":  [("dsa", "Recursion"), ("dsa", "Arrays")],
    "backtracking":         [("dsa", "Recursion")],
    "trees":                [("dsa", "Recursion")],
    "binary_search":        [("dsa", "Arrays")],
    "intervals":            [("dsa", "Sorting")],
    "linked_list":          [("dsa", "Two Pointers")],
    "strings":              [("dsa", "Hashing")],
     # Sprint 2 additions
    "queue":                [("dsa", "Arrays")],
    "trie":                 [("dsa", "Strings")],
    "union_find":           [("dsa", "Graphs")],
    "recursion":            [],
    "sorting":              [("dsa", "Arrays")],
    "segment_tree":         [("dsa", "Arrays")],
}

# -------------------------------------------------------
# Canonical metadata enums
# -------------------------------------------------------

DIFFICULTIES = (
    "easy",
    "medium",
    "hard",
)

LEARNING_STAGES = (
    "foundation",
    "core",
    "advanced",
)

FREQUENCIES = (
    "low",
    "medium",
    "high",
    "very_high",
)

# -------------------------------------------------------
# Supported Companies (Canonical Registry)
# -------------------------------------------------------
# Keys are stored in the problem bank.
# Values are displayed in the UI.
#
# Add new companies here whenever PrepOS expands.
# -------------------------------------------------------

COMPANIES = {
    # ================= FAANG & Big Tech =================
    "google": "Google",
    "amazon": "Amazon",
    "microsoft": "Microsoft",
    "meta": "Meta",
    "apple": "Apple",
    "netflix": "Netflix",
    "uber": "Uber",
    "airbnb": "Airbnb",

    # ================= Enterprise / Cloud =================
    "adobe": "Adobe",
    "atlassian": "Atlassian",
    "linkedin": "LinkedIn",
    "salesforce": "Salesforce",
    "oracle": "Oracle",
    "servicenow": "ServiceNow",
    "intuit": "Intuit",
    "nvidia": "NVIDIA",

    # ================= FinTech =================
    "stripe": "Stripe",
    "paypal": "PayPal",
    "razorpay": "Razorpay",
    "phonepe": "PhonePe",

    # ================= Indian Product Companies =================
    "flipkart": "Flipkart",
    "zoho": "Zoho",
    "walmart": "Walmart Global Tech",

    # ================= Finance =================
    "goldman_sachs": "Goldman Sachs",
    "jpmorgan": "JPMorgan Chase",
    "american_express": "American Express",

    # ================= Others =================
    "others": "Others",
}


# --- Curated problem list ---
# Fields: id (stable slug), title, difficulty, pattern, estimated_minutes, leetcode_url, tags
PROBLEMS = [
    # ================= Sliding Window =================
    {
        "id": "lc-3",
        "leetcode_id": 3,
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/longest-substring-without-repeating-characters/",
        "tags": [
            "hashing",
            "strings"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "microsoft",
            "uber",
            "atlassian",
            "linkedin",
            "adobe"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-209",
        "leetcode_id": 209,
        "title": "Minimum Size Subarray Sum",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/minimum-size-subarray-sum/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "google"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-643",
        "leetcode_id": 643,
        "title": "Maximum Average Subarray I",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/maximum-average-subarray-i/",
        "tags": [],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "low",
        "companies": [
            "others"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-424",
        "leetcode_id": 424,
        "title": "Longest Repeating Character Replacement",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/longest-repeating-character-replacement/",
        "tags": [
            "hashing",
            "strings"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "microsoft",
            "atlassian"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-567",
        "leetcode_id": 567,
        "title": "Permutation in String",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/permutation-in-string/",
        "tags": [
            "hashing",
            "strings"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-438",
        "leetcode_id": 438,
        "title": "Find All Anagrams in a String",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/find-all-anagrams-in-a-string/",
        "tags": [
            "hashing",
            "strings"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "microsoft"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1004",
        "leetcode_id": 1004,
        "title": "Max Consecutive Ones III",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/max-consecutive-ones-iii/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "google"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-904",
        "leetcode_id": 904,
        "title": "Fruit Into Baskets",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/fruit-into-baskets/",
        "tags": [
            "variable_window",
            "hashing"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-76",
        "leetcode_id": 76,
        "title": "Minimum Window Substring",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/minimum-window-substring/",
        "tags": [
            "hashing",
            "strings"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "microsoft",
            "uber",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-239",
        "leetcode_id": 239,
        "title": "Sliding Window Maximum",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "sliding_window",
        "primary_pattern": "sliding_window",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/sliding-window-maximum/",
        "tags": [
            "heap",
            "deque"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "microsoft",
            "uber",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": True
    },
       # ================= Two Pointers =================
    {
        "id": "lc-167",
        "leetcode_id": 167,
        "title": "Two Sum II - Input Array Is Sorted",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/",
        "tags": [
            "binary_search"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-11",
        "leetcode_id": 11,
        "title": "Container With Most Water",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/container-with-most-water/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "neetcode150",
            "leetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-125",
        "leetcode_id": 125,
        "title": "Valid Palindrome",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/valid-palindrome/",
        "tags": [
            "strings"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-26",
        "leetcode_id": 26,
        "title": "Remove Duplicates from Sorted Array",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/remove-duplicates-from-sorted-array/",
        "tags": [
            "fast_slow_pointers",
            "in_place"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "amazon",
            "google",
            "meta",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-977",
        "leetcode_id": 977,
        "title": "Squares of a Sorted Array",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/squares-of-a-sorted-array/",
        "tags": [
            "opposite_pointers",
            "sorted_arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "meta",
            "amazon",
            "google"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": False
    },
    {
        "id": "lc-15",
        "leetcode_id": 15,
        "title": "3Sum",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/3sum/",
        "tags": [
            "sorting",
            "arrays"
        ],
        "prerequisite_patterns": [
            "sorting",
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "microsoft",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-680",
        "leetcode_id": 680,
        "title": "Valid Palindrome II",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/valid-palindrome-ii/",
        "tags": [
            "strings"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "meta"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-42",
        "leetcode_id": 42,
        "title": "Trapping Rain Water",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "two_pointers",
        "primary_pattern": "two_pointers",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/trapping-rain-water/",
        "tags": [
            "stack",
            "dynamic_programming"
        ],
        "prerequisite_patterns": [
            "stack"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
       # ================= Arrays =================
    {
        "id": "lc-53",
        "leetcode_id": 53,
        "title": "Maximum Subarray",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/maximum-subarray/",
        "tags": [
            "kadane",
            "dynamic_programming"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-121",
        "leetcode_id": 121,
        "title": "Best Time to Buy and Sell Stock",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/",
        "tags": [
            "greedy"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "amazon",
            "google",
            "microsoft",
            "meta",
            "apple",
            "flipkart"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-189",
        "leetcode_id": 189,
        "title": "Rotate Array",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/rotate-array/",
        "tags": [
            "math"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "microsoft",
            "google"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-283",
        "leetcode_id": 283,
        "title": "Move Zeroes",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/move-zeroes/",
        "tags": [
            "two_pointers"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-238",
        "leetcode_id": 238,
        "title": "Product of Array Except Self",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/product-of-array-except-self/",
        "tags": [
            "prefix_product"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "amazon",
            "google",
            "meta",
            "microsoft",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-152",
        "leetcode_id": 152,
        "title": "Maximum Product Subarray",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/maximum-product-subarray/",
        "tags": [
            "dynamic_programming"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-73",
        "leetcode_id": 73,
        "title": "Set Matrix Zeroes",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/set-matrix-zeroes/",
        "tags": [
            "matrix",
            "in_place"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": False
    },
    {
        "id": "lc-48",
        "leetcode_id": 48,
        "title": "Rotate Image",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/rotate-image/",
        "tags": [
            "matrix",
            "in_place"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-54",
        "leetcode_id": 54,
        "title": "Spiral Matrix",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/spiral-matrix/",
        "tags": [
            "matrix",
            "simulation"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-1109",
        "leetcode_id": 1109,
        "title": "Corporate Flight Bookings",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/corporate-flight-bookings/",
        "tags": [
            "prefix_sum"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
        {
        "id": "lc-41",
        "leetcode_id": 41,
        "title": "First Missing Positive",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "arrays",
        "primary_pattern": "arrays",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/first-missing-positive/",
        "tags": [
            "in_place_hashing",
            "index_mapping"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    # ================= Hashing =================
    {
        "id": "lc-1",
        "leetcode_id": 1,
        "title": "Two Sum",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/two-sum/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "uber",
            "linkedin",
            "atlassian",
            "stripe",
            "phonepe",
            "flipkart"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-217",
        "leetcode_id": 217,
        "title": "Contains Duplicate",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 10,
        "leetcode_url": "https://leetcode.com/problems/contains-duplicate/",
        "tags": [
            "hash_set"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-205",
        "leetcode_id": 205,
        "title": "Isomorphic Strings",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/isomorphic-strings/",
        "tags": [
            "hash_map",
            "character_mapping"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-49",
        "leetcode_id": 49,
        "title": "Group Anagrams",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/group-anagrams/",
        "tags": [
            "strings"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-347",
        "leetcode_id": 347,
        "title": "Top K Frequent Elements",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/top-k-frequent-elements/",
        "tags": [
            "heap"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "microsoft",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-128",
        "leetcode_id": 128,
        "title": "Longest Consecutive Sequence",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/longest-consecutive-sequence/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-36",
        "leetcode_id": 36,
        "title": "Valid Sudoku",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "hashing",
        "primary_pattern": "hashing",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/valid-sudoku/",
        "tags": [
            "hash_set",
            "matrix_validation"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
   # ================= Binary Search =================
    {
        "id": "lc-704",
        "leetcode_id": 704,
        "title": "Binary Search",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/binary-search/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
        {
        "id": "lc-74",
        "leetcode_id": 74,
        "title": "Search a 2D Matrix",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/search-a-2d-matrix/",
        "tags": [
            "matrix",
            "binary_search"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": False
    },
    {
        "id": "lc-35",
        "leetcode_id": 35,
        "title": "Search Insert Position",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/search-insert-position/",
        "tags": [
            "arrays",
            "search"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-33",
        "leetcode_id": 33,
        "title": "Search in Rotated Sorted Array",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/search-in-rotated-sorted-array/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-153",
        "leetcode_id": 153,
        "title": "Find Minimum in Rotated Sorted Array",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/",
        "tags": [
            "arrays"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-540",
        "leetcode_id": 540,
        "title": "Single Element in a Sorted Array",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/single-element-in-a-sorted-array/",
        "tags": [
            "binary_search",
            "sorted_array"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-981",
        "leetcode_id": 981,
        "title": "Time Based Key-Value Store",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/time-based-key-value-store/",
        "tags": [
            "binary_search",
            "hashing",
            "design"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-875",
        "leetcode_id": 875,
        "title": "Koko Eating Bananas",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/koko-eating-bananas/",
        "tags": [
            "binary_search_on_answer"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "linkedin"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-410",
        "leetcode_id": 410,
        "title": "Split Array Largest Sum",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/split-array-largest-sum/",
        "tags": [
            "binary_search_on_answer",
            "greedy"
        ],
        "prerequisite_patterns": [
            "arrays",
            "greedy"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "apple"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-4",
        "leetcode_id": 4,
        "title": "Median of Two Sorted Arrays",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/median-of-two-sorted-arrays/",
        "tags": [
            "partitioning"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "apple",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-1011",
        "leetcode_id": 1011,
        "title": "Capacity To Ship Packages Within D Days",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/capacity-to-ship-packages-within-d-days/",
        "tags": [
            "binary_search_on_answer",
            "greedy"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": False
    },
    {
        "id": "lc-1482",
        "leetcode_id": 1482,
        "title": "Minimum Number of Days to Make m Bouquets",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "binary_search",
        "primary_pattern": "binary_search",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/minimum-number-of-days-to-make-m-bouquets/",
        "tags": [
            "binary_search_on_answer",
            "greedy"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
   # ================= Stack =================
    {
        "id": "lc-20",
        "leetcode_id": 20,
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/valid-parentheses/",
        "tags": [
            "parentheses"
        ],
        "prerequisite_patterns": [],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "atlassian",
            "oracle"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-155",
        "leetcode_id": 155,
        "title": "Min Stack",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/min-stack/",
        "tags": [
            "design"
        ],
        "prerequisite_patterns": [
            "stack"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-71",
        "leetcode_id": 71,
        "title": "Simplify Path",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/simplify-path/",
        "tags": [
            "stack_simulation",
            "strings"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-739",
        "leetcode_id": 739,
        "title": "Daily Temperatures",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/daily-temperatures/",
        "tags": [
            "monotonic_stack"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-853",
        "leetcode_id": 853,
        "title": "Car Fleet",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/car-fleet/",
        "tags": [
            "sorting"
        ],
        "prerequisite_patterns": [
            "sorting",
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-150",
        "leetcode_id": 150,
        "title": "Evaluate Reverse Polish Notation",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/evaluate-reverse-polish-notation/",
        "tags": [
            "expression_evaluation",
            "stack_simulation"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-394",
        "leetcode_id": 394,
        "title": "Decode String",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/decode-string/",
        "tags": [
            "stack",
            "parsing"
        ],
        "prerequisite_patterns": [
            "stack"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-84",
        "leetcode_id": 84,
        "title": "Largest Rectangle in Histogram",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/largest-rectangle-in-histogram/",
        "tags": [
            "monotonic_stack"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-402",
        "leetcode_id": 402,
        "title": "Remove K Digits",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/remove-k-digits/",
        "tags": [
            "monotonic_stack",
            "greedy",
            "strings"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-224",
        "leetcode_id": 224,
        "title": "Basic Calculator",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "stack",
        "primary_pattern": "stack",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/basic-calculator/",
        "tags": [
            "math",
            "string",
            "recursion"
        ],
        "prerequisite_patterns": [
            "stack"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [],
        "representative": True
    },
       # ================= Linked List =================
    {
        "id": "lc-206",
        "leetcode_id": 206,
        "title": "Reverse Linked List",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/reverse-linked-list/",
        "tags": [
            "pointer_manipulation"
        ],
        "prerequisite_patterns": [],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-21",
        "leetcode_id": 21,
        "title": "Merge Two Sorted Lists",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/merge-two-sorted-lists/",
        "tags": [
            "dummy_node"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-141",
        "leetcode_id": 141,
        "title": "Linked List Cycle",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/linked-list-cycle/",
        "tags": [
            "fast_slow_pointer"
        ],
        "prerequisite_patterns": [
            "two_pointers"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-19",
        "leetcode_id": 19,
        "title": "Remove Nth Node From End of List",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/remove-nth-node-from-end-of-list/",
        "tags": [
            "fast_slow_pointer"
        ],
        "prerequisite_patterns": [
            "two_pointers"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-143",
        "leetcode_id": 143,
        "title": "Reorder List",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/reorder-list/",
        "tags": [
            "fast_slow_pointer",
            "reverse"
        ],
        "prerequisite_patterns": [
            "two_pointers"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-138",
        "leetcode_id": 138,
        "title": "Copy List with Random Pointer",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/copy-list-with-random-pointer/",
        "tags": [
            "hashing",
            "pointer_manipulation"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-146",
        "leetcode_id": 146,
        "title": "LRU Cache",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/lru-cache/",
        "tags": [
            "design",
            "hashing",
            "doubly_linked_list"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "linkedin",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-23",
        "leetcode_id": 23,
        "title": "Merge k Sorted Lists",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/merge-k-sorted-lists/",
        "tags": [
            "heap",
            "divide_and_conquer"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-25",
        "leetcode_id": 25,
        "title": "Reverse Nodes in k-Group",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "linked_list",
        "primary_pattern": "linked_list",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/reverse-nodes-in-k-group/",
        "tags": [
            "pointer_manipulation",
            "linked_list_reversal"
        ],
        "prerequisite_patterns": [
            "linked_list"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    # ================= Trees =================
    {
        "id": "lc-104",
        "leetcode_id": 104,
        "title": "Maximum Depth of Binary Tree",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/maximum-depth-of-binary-tree/",
        "tags": [
            "depth_first_search",
            "recursion"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-100",
        "leetcode_id": 100,
        "title": "Same Tree",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/same-tree/",
        "tags": [
            "depth_first_search",
            "recursion"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-226",
        "leetcode_id": 226,
        "title": "Invert Binary Tree",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/invert-binary-tree/",
        "tags": [
            "depth_first_search",
            "recursion"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-700",
        "leetcode_id": 700,
        "title": "Search in a Binary Search Tree",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/search-in-a-binary-search-tree/",
        "tags": [
            "tree",
            "binary search tree",
            "binary tree"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-701",
        "leetcode_id": 701,
        "title": "Insert into a Binary Search Tree",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/insert-into-a-binary-search-tree/",
        "tags": [
            "tree",
            "binary search tree",
            "binary tree"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-102",
        "leetcode_id": 102,
        "title": "Binary Tree Level Order Traversal",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/binary-tree-level-order-traversal/",
        "tags": [
            "breadth_first_search",
            "queue"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-98",
        "leetcode_id": 98,
        "title": "Validate Binary Search Tree",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/validate-binary-search-tree/",
        "tags": [
            "binary_search_tree",
            "depth_first_search"
        ],
        "prerequisite_patterns": [
            "binary_search"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-230",
        "leetcode_id": 230,
        "title": "Kth Smallest Element in a BST",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/kth-smallest-element-in-a-bst/",
        "tags": [
            "binary_search_tree",
            "inorder"
        ],
        "prerequisite_patterns": [
            "binary_search"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-236",
        "leetcode_id": 236,
        "title": "Lowest Common Ancestor of a Binary Tree",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/",
        "tags": [
            "depth_first_search",
            "recursion"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-543",
        "leetcode_id": 543,
        "title": "Diameter of Binary Tree",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/diameter-of-binary-tree/",
        "tags": [
            "depth_first_search",
            "tree_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-199",
        "leetcode_id": 199,
        "title": "Binary Tree Right Side View",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/binary-tree-right-side-view/",
        "tags": [
            "breadth_first_search",
            "depth_first_search"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-572",
        "leetcode_id": 572,
        "title": "Subtree of Another Tree",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/subtree-of-another-tree/",
        "tags": [
            "depth_first_search",
            "tree_comparison"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-235",
        "leetcode_id": 235,
        "title": "Lowest Common Ancestor of a Binary Search Tree",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-search-tree/",
        "tags": [
            "tree",
            "depth-first search",
            "binary search tree",
            "binary tree"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "meta"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-105",
        "leetcode_id": 105,
        "title": "Construct Binary Tree from Preorder and Inorder Traversal",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/",
        "tags": [
            "recursion",
            "construction"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-124",
        "leetcode_id": 124,
        "title": "Binary Tree Maximum Path Sum",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/binary-tree-maximum-path-sum/",
        "tags": [
            "tree_dp",
            "depth_first_search"
        ],
        "prerequisite_patterns": [
            "dynamic_programming",
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-297",
        "leetcode_id": 297,
        "title": "Serialize and Deserialize Binary Tree",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/serialize-and-deserialize-binary-tree/",
        "tags": [
            "depth_first_search",
            "breadth_first_search",
            "serialization"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-114",
        "leetcode_id": 114,
        "title": "Flatten Binary Tree to Linked List",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/flatten-binary-tree-to-linked-list/",
        "tags": [
            "depth_first_search",
            "tree_transformation"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-450",
        "leetcode_id": 450,
        "title": "Delete Node in a BST",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/delete-node-in-a-bst/",
        "tags": [
            "tree",
            "binary search tree",
            "binary tree"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "medium",
        "companies": [
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-669",
        "leetcode_id": 669,
        "title": "Trim a Binary Search Tree",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "trees",
        "primary_pattern": "trees",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/trim-a-binary-search-tree/",
        "tags": [
            "tree",
            "depth-first search",
            "binary search tree",
            "binary tree"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
      # ================= Graphs =================
    {
        "id": "lc-200",
        "leetcode_id": 200,
        "title": "Number of Islands",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/number-of-islands/",
        "tags": [
            "depth_first_search",
            "breadth_first_search",
            "grid"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-133",
        "leetcode_id": 133,
        "title": "Clone Graph",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/clone-graph/",
        "tags": [
            "depth_first_search",
            "breadth_first_search",
            "hashing"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-684",
        "leetcode_id": 684,
        "title": "Redundant Connection",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/redundant-connection/",
        "tags": [
            "union_find",
            "disjoint_set_union"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-261",
        "leetcode_id": 261,
        "title": "Graph Valid Tree",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/graph-valid-tree/",
        "tags": [
            "union_find",
            "depth_first_search"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "linkedin"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-733",
        "leetcode_id": 733,
        "title": "Flood Fill",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/flood-fill/",
        "tags": [
            "array",
            "depth-first search",
            "breadth-first search",
            "matrix"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-207",
        "leetcode_id": 207,
        "title": "Course Schedule",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/course-schedule/",
        "tags": [
            "topological_sort",
            "depth_first_search",
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-417",
        "leetcode_id": 417,
        "title": "Pacific Atlantic Water Flow",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/pacific-atlantic-water-flow/",
        "tags": [
            "depth_first_search",
            "grid"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-994",
        "leetcode_id": 994,
        "title": "Rotting Oranges",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/rotting-oranges/",
        "tags": [
            "multi_source_bfs",
            "grid"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-269",
        "leetcode_id": 269,
        "title": "Alien Dictionary",
        "difficulty": "hard",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/alien-dictionary/",
        "tags": [
            "topological_sort",
            "depth_first_search",
            "breadth_first_search"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "meta",
            "airbnb",
            "amazon"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1466",
        "leetcode_id": 1466,
        "title": "Reorder Routes to Make All Paths Lead to the City Zero",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/reorder-routes-to-make-all-paths-lead-to-the-city-zero/",
        "tags": [
            "depth_first_search",
            "tree",
            "directed_graph"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1129",
        "leetcode_id": 1129,
        "title": "Shortest Path with Alternating Colors",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/shortest-path-with-alternating-colors/",
        "tags": [
            "breadth_first_search",
            "state_space_search"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1514",
        "leetcode_id": 1514,
        "title": "Path with Maximum Probability",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/path-with-maximum-probability/",
        "tags": [
            "dijkstra",
            "heap",
            "weighted_graph"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-210",
        "leetcode_id": 210,
        "title": "Course Schedule II",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/course-schedule-ii/",
        "tags": [
            "depth-first search",
            "breadth-first search",
            "graph",
            "topological sort"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-743",
        "leetcode_id": 743,
        "title": "Network Delay Time",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/network-delay-time/",
        "tags": [
            "dijkstra",
            "heap"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "apple"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-127",
        "leetcode_id": 127,
        "title": "Word Ladder",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/word-ladder/",
        "tags": [
            "breadth_first_search",
            "shortest_path"
        ],
        "prerequisite_patterns": [
            "graphs",
            "hashing"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-787",
        "leetcode_id": 787,
        "title": "Cheapest Flights Within K Stops",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/cheapest-flights-within-k-stops/",
        "tags": [
            "bellman_ford",
            "dijkstra",
            "weighted_graph"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "uber"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1631",
        "leetcode_id": 1631,
        "title": "Path With Minimum Effort",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/path-with-minimum-effort/",
        "tags": [
            "dijkstra",
            "grid",
            "heap",
            "weighted_graph"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1584",
        "leetcode_id": 1584,
        "title": "Min Cost to Connect All Points",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/min-cost-to-connect-all-points/",
        "tags": [
            "minimum_spanning_tree",
            "prim_algorithm",
            "heap"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-332",
        "leetcode_id": 332,
        "title": "Reconstruct Itinerary",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/reconstruct-itinerary/",
        "tags": [
            "eulerian_path",
            "depth_first_search",
            "lexicographical_order"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "uber"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1489",
        "leetcode_id": 1489,
        "title": "Find Critical and Pseudo-Critical Edges in Minimum Spanning Tree",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "graphs",
        "primary_pattern": "graphs",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/find-critical-and-pseudo-critical-edges-in-minimum-spanning-tree/",
        "tags": [
            "union find",
            "graph",
            "sorting",
            "minimum spanning tree",
            "biconnected component"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
       # ================= Heap =================
    {
        "id": "lc-703",
        "leetcode_id": 703,
        "title": "Kth Largest Element in a Stream",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/kth-largest-element-in-a-stream/",
        "tags": [
            "priority_queue",
            "streaming",
            "design"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-215",
        "leetcode_id": 215,
        "title": "Kth Largest Element in an Array",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/kth-largest-element-in-an-array/",
        "tags": [
            "priority_queue",
            "top_k",
            "quickselect"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-1046",
        "leetcode_id": 1046,
        "title": "Last Stone Weight",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/last-stone-weight/",
        "tags": [
            "priority_queue",
            "simulation"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "google"
        ],
        "source_lists": [
            "leetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-973",
        "leetcode_id": 973,
        "title": "K Closest Points to Origin",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/k-closest-points-to-origin/",
        "tags": [
            "heap",
            "geometry"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-378",
        "leetcode_id": 378,
        "title": "Kth Smallest Element in a Sorted Matrix",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/kth-smallest-element-in-a-sorted-matrix/",
        "tags": [
            "priority_queue",
            "min_heap"
        ],
        "prerequisite_patterns": [
            "binary_search"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-692",
        "leetcode_id": 692,
        "title": "Top K Frequent Words",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/top-k-frequent-words/",
        "tags": [
            "heap",
            "hashing",
            "custom_sort"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-295",
        "leetcode_id": 295,
        "title": "Find Median from Data Stream",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/find-median-from-data-stream/",
        "tags": [
            "dual_heap",
            "streaming",
            "design"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "linkedin"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-621",
        "leetcode_id": 621,
        "title": "Task Scheduler",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/task-scheduler/",
        "tags": [
            "priority_queue",
            "max_heap",
            "simulation"
        ],
        "prerequisite_patterns": [
            "max_heap",
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-355",
        "leetcode_id": 355,
        "title": "Design Twitter",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/design-twitter/",
        "tags": [
            "design",
            "heap",
            "hashing"
        ],
        "prerequisite_patterns": [
            "hashing",
            "heap"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-767",
        "leetcode_id": 767,
        "title": "Reorganize String",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/reorganize-string/",
        "tags": [
            "priority_queue",
            "max_heap",
            "strings"
        ],
        "prerequisite_patterns": [
            "max_heap",
            "strings"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-502",
        "leetcode_id": 502,
        "title": "IPO",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/ipo/",
        "tags": [
            "priority_queue",
            "max_heap",
            "sorting"
        ],
        "prerequisite_patterns": [
            "max_heap",
            "sorting"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "linkedin"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-480",
        "leetcode_id": 480,
        "title": "Sliding Window Median",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "heap",
        "primary_pattern": "heap",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/sliding-window-median/",
        "tags": [
            "array",
            "hash table",
            "sliding window",
            "heap (priority queue)"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
        # ================= Dynamic Programming =================
    {
        "id": "lc-70",
        "leetcode_id": 70,
        "title": "Climbing Stairs",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/climbing-stairs/",
        "tags": [
            "1d_dp"
        ],
        "prerequisite_patterns": [],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-198",
        "leetcode_id": 198,
        "title": "House Robber",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/house-robber/",
        "tags": [
            "1d_dp"
        ],
        "prerequisite_patterns": [],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-416",
        "leetcode_id": 416,
        "title": "Partition Equal Subset Sum",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/partition-equal-subset-sum/",
        "tags": [
            "zero_one_knapsack",
            "subset_sum"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-494",
        "leetcode_id": 494,
        "title": "Target Sum",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/target-sum/",
        "tags": [
            "zero_one_knapsack",
            "subset_sum"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-746",
        "leetcode_id": 746,
        "title": "Min Cost Climbing Stairs",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/min-cost-climbing-stairs/",
        "tags": [
            "array",
            "dynamic programming"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-213",
        "leetcode_id": 213,
        "title": "House Robber II",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/house-robber-ii/",
        "tags": [
            "1d_dp",
            "circular_array"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google"
        ],
        "source_lists": [
            "blind75",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-322",
        "leetcode_id": 322,
        "title": "Coin Change",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/coin-change/",
        "tags": [
            "unbounded_knapsack"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-300",
        "leetcode_id": 300,
        "title": "Longest Increasing Subsequence",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/longest-increasing-subsequence/",
        "tags": [
            "sequence_dp"
        ],
        "prerequisite_patterns": [
            "binary_search"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-518",
        "leetcode_id": 518,
        "title": "Coin Change II",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/coin-change-ii/",
        "tags": [
            "unbounded_knapsack",
            "coin_change"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-97",
        "leetcode_id": 97,
        "title": "Interleaving String",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/interleaving-string/",
        "tags": [
            "two_dimensional_dynamic_programming",
            "string_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-115",
        "leetcode_id": 115,
        "title": "Distinct Subsequences",
        "difficulty": "hard",
        "learning_stage": "core",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/distinct-subsequences/",
        "tags": [
            "string_dynamic_programming",
            "two_dimensional_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-1143",
        "leetcode_id": 1143,
        "title": "Longest Common Subsequence",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/longest-common-subsequence/",
        "tags": [
            "2d_dp",
            "sequence_dp"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-62",
        "leetcode_id": 62,
        "title": "Unique Paths",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/unique-paths/",
        "tags": [
            "grid_dp"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-64",
        "leetcode_id": 64,
        "title": "Minimum Path Sum",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/minimum-path-sum/",
        "tags": [
            "grid_dp"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-139",
        "leetcode_id": 139,
        "title": "Word Break",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/word-break/",
        "tags": [
            "1d_dp",
            "strings"
        ],
        "prerequisite_patterns": [
            "dynamic_programming",
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-72",
        "leetcode_id": 72,
        "title": "Edit Distance",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/edit-distance/",
        "tags": [
            "2d_dp",
            "strings"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-174",
        "leetcode_id": 174,
        "title": "Dungeon Game",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/dungeon-game/",
        "tags": [
            "reverse_dynamic_programming",
            "grid_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-312",
        "leetcode_id": 312,
        "title": "Burst Balloons",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 50,
        "leetcode_url": "https://leetcode.com/problems/burst-balloons/",
        "tags": [
            "interval_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-10",
        "leetcode_id": 10,
        "title": "Regular Expression Matching",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 55,
        "leetcode_url": "https://leetcode.com/problems/regular-expression-matching/",
        "tags": [
            "string_dynamic_programming",
            "pattern_matching"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-123",
        "leetcode_id": 123,
        "title": "Best Time to Buy and Sell Stock III",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/",
        "tags": [
            "state_machine_dynamic_programming",
            "stock_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-188",
        "leetcode_id": 188,
        "title": "Best Time to Buy and Sell Stock IV",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 50,
        "leetcode_url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iv/",
        "tags": [
            "state_machine_dynamic_programming",
            "stock_dynamic_programming"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-847",
        "leetcode_id": 847,
        "title": "Shortest Path Visiting All Nodes",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "dynamic_programming",
        "primary_pattern": "dynamic_programming",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/shortest-path-visiting-all-nodes/",
        "tags": [
            "bit manipulation",
            "breadth-first search",
            "graph",
            "bitmask",
            "shortest path"
        ],
        "prerequisite_patterns": [
            "graphs",
            "dynamic_programming"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
        # ================= Backtracking =================
    {
        "id": "lc-78",
        "leetcode_id": 78,
        "title": "Subsets",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/subsets/",
        "tags": [
            "depth_first_search",
            "combinations"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-46",
        "leetcode_id": 46,
        "title": "Permutations",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/permutations/",
        "tags": [
            "depth_first_search",
            "permutations"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-39",
        "leetcode_id": 39,
        "title": "Combination Sum",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/combination-sum/",
        "tags": [
            "depth_first_search",
            "combinations"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-79",
        "leetcode_id": 79,
        "title": "Word Search",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/word-search/",
        "tags": [
            "grid",
            "depth_first_search"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-131",
        "leetcode_id": 131,
        "title": "Palindrome Partitioning",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/palindrome-partitioning/",
        "tags": [
            "strings",
            "partitioning"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-51",
        "leetcode_id": 51,
        "title": "N-Queens",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/n-queens/",
        "tags": [
            "constraint_satisfaction",
            "depth_first_search"
        ],
        "prerequisite_patterns": [
            "backtracking"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-37",
        "leetcode_id": 37,
        "title": "Sudoku Solver",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "backtracking",
        "primary_pattern": "backtracking",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/sudoku-solver/",
        "tags": [
            "array",
            "hash table",
            "backtracking",
            "matrix"
        ],
        "prerequisite_patterns": [
            "backtracking"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
        # ================= Greedy =================
    {
        "id": "lc-55",
        "leetcode_id": 55,
        "title": "Jump Game",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/jump-game/",
        "tags": [
            "reachability"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-122",
        "leetcode_id": 122,
        "title": "Best Time to Buy and Sell Stock II",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-ii/",
        "tags": [
            "stock",
            "local_optimum"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "very_high",
        "companies": [
            "amazon",
            "google",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-455",
        "leetcode_id": 455,
        "title": "Assign Cookies",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/assign-cookies/",
        "tags": [
            "array",
            "greedy",
            "sorting"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-605",
        "leetcode_id": 605,
        "title": "Can Place Flowers",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/can-place-flowers/",
        "tags": [
            "array",
            "greedy"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-45",
        "leetcode_id": 45,
        "title": "Jump Game II",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/jump-game-ii/",
        "tags": [
            "reachability"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-134",
        "leetcode_id": 134,
        "title": "Gas Station",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/gas-station/",
        "tags": [
            "simulation"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-763",
        "leetcode_id": 763,
        "title": "Partition Labels",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/partition-labels/",
        "tags": [
            "strings"
        ],
        "prerequisite_patterns": [
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-1029",
        "leetcode_id": 1029,
        "title": "Two City Scheduling",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/two-city-scheduling/",
        "tags": [
            "sorting",
            "opportunity_cost"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-678",
        "leetcode_id": 678,
        "title": "Valid Parenthesis String",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/valid-parenthesis-string/",
        "tags": [
            "parentheses",
            "range_tracking"
        ],
        "prerequisite_patterns": [
            "stack"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-135",
        "leetcode_id": 135,
        "title": "Candy",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "greedy",
        "primary_pattern": "greedy",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/candy/",
        "tags": [
            "array",
            "greedy"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Intervals =================
    {
        "id": "lc-56",
        "leetcode_id": 56,
        "title": "Merge Intervals",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/merge-intervals/",
        "tags": [
            "sorting",
            "overlap"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-57",
        "leetcode_id": 57,
        "title": "Insert Interval",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/insert-interval/",
        "tags": [
            "sorting",
            "merge"
        ],
        "prerequisite_patterns": [
            "intervals"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-252",
        "leetcode_id": 252,
        "title": "Meeting Rooms",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/meeting-rooms/",
        "tags": [
            "sorting"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "lintcode"
        ],
        "representative": False
    },
    {
        "id": "lc-253",
        "leetcode_id": 253,
        "title": "Meeting Rooms II",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/meeting-rooms-ii/",
        "tags": [
            "heap",
            "sorting"
        ],
        "prerequisite_patterns": [
            "heap"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "meta",
            "linkedin"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-986",
        "leetcode_id": 986,
        "title": "Interval List Intersections",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/interval-list-intersections/",
        "tags": [
            "two_pointers",
            "interval_intersection"
        ],
        "prerequisite_patterns": [
            "two_pointers"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "meta",
            "amazon"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-1288",
        "leetcode_id": 1288,
        "title": "Remove Covered Intervals",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/remove-covered-intervals/",
        "tags": [
            "sorting",
            "interval_coverage"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "medium",
        "companies": [
            "google"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-452",
        "leetcode_id": 452,
        "title": "Minimum Number of Arrows to Burst Balloons",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/minimum-number-of-arrows-to-burst-balloons/",
        "tags": [
            "greedy",
            "sorting"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-435",
        "leetcode_id": 435,
        "title": "Non-overlapping Intervals",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "intervals",
        "primary_pattern": "intervals",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/non-overlapping-intervals/",
        "tags": [
            "greedy",
            "sorting"
        ],
        "prerequisite_patterns": [
            "greedy"
        ],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
       # ================= Strings =================
    {
        "id": "lc-14",
        "leetcode_id": 14,
        "title": "Longest Common Prefix",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/longest-common-prefix/",
        "tags": [
            "prefix"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-271",
        "leetcode_id": 271,
        "title": "Encode and Decode Strings",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/encode-and-decode-strings/",
        "tags": [
            "serialization",
            "design"
        ],
        "prerequisite_patterns": [],
        "frequency": "medium",
        "companies": [
            "google",
            "meta"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-6",
        "leetcode_id": 6,
        "title": "Zigzag Conversion",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/zigzag-conversion/",
        "tags": [
            "simulation",
            "index_manipulation"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-5",
        "leetcode_id": 5,
        "title": "Longest Palindromic Substring",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/longest-palindromic-substring/",
        "tags": [
            "palindrome",
            "expand_around_center",
            "dynamic_programming"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-43",
        "leetcode_id": 43,
        "title": "Multiply Strings",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/multiply-strings/",
        "tags": [
            "string_arithmetic",
            "simulation"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-647",
        "leetcode_id": 647,
        "title": "Palindromic Substrings",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/palindromic-substrings/",
        "tags": [
            "palindrome",
            "expand_around_center",
            "dynamic_programming"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "google"
        ],
        "source_lists": [
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-151",
        "leetcode_id": 151,
        "title": "Reverse Words in a String",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/reverse-words-in-a-string/",
        "tags": [
            "parsing",
            "two_pointers"
        ],
        "prerequisite_patterns": [
            "two_pointers"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-8",
        "leetcode_id": 8,
        "title": "String to Integer (atoi)",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/string-to-integer-atoi/",
        "tags": [
            "parsing",
            "simulation"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-28",
        "leetcode_id": 28,
        "title": "Find the Index of the First Occurrence in a String",
        "difficulty": "easy",
        "learning_stage": "advanced",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/find-the-index-of-the-first-occurrence-in-a-string/",
        "tags": [
            "two pointers",
            "string",
            "string matching"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-68",
        "leetcode_id": 68,
        "title": "Text Justification",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "strings",
        "primary_pattern": "strings",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/text-justification/",
        "tags": [
            "array",
            "string",
            "simulation"
        ],
        "prerequisite_patterns": [
            "strings"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Bit Manipulation =================
    {
        "id": "lc-136",
        "leetcode_id": 136,
        "title": "Single Number",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/single-number/",
        "tags": [
            "xor"
        ],
        "prerequisite_patterns": [],
        "frequency": "very_high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta",
            "apple"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150",
            "striver"
        ],
        "representative": True
    },
    {
        "id": "lc-191",
        "leetcode_id": 191,
        "title": "Number of 1 Bits",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/number-of-1-bits/",
        "tags": [
            "bit_count"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-338",
        "leetcode_id": 338,
        "title": "Counting Bits",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/counting-bits/",
        "tags": [
            "dynamic_programming",
            "bit_count"
        ],
        "prerequisite_patterns": [
            "dynamic_programming"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": False
    },
    {
        "id": "lc-190",
        "leetcode_id": 190,
        "title": "Reverse Bits",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/reverse-bits/",
        "tags": [
            "bit_operations"
        ],
        "prerequisite_patterns": [],
        "frequency": "medium",
        "companies": [
            "google",
            "microsoft",
            "apple"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-268",
        "leetcode_id": 268,
        "title": "Missing Number",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/missing-number/",
        "tags": [
            "xor",
            "math"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "high",
        "companies": [
            "google",
            "amazon",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "blind75",
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
        {
        "id": "lc-260",
        "leetcode_id": 260,
        "title": "Single Number III",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/single-number-iii/",
        "tags": [
            "xor",
            "bit_partitioning"
        ],
        "prerequisite_patterns": [
            "bit_manipulation"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-371",
        "leetcode_id": 371,
        "title": "Sum of Two Integers",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/sum-of-two-integers/",
        "tags": [
            "bit_operations",
            "simulation"
        ],
        "prerequisite_patterns": [],
        "frequency": "medium",
        "companies": [
            "google",
            "amazon",
            "microsoft"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-137",
        "leetcode_id": 137,
        "title": "Single Number II",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/single-number-ii/",
        "tags": [
            "bit_counting",
            "state_machine"
        ],
        "prerequisite_patterns": [
            "bit_manipulation"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google",
            "microsoft",
            "meta"
        ],
        "source_lists": [
            "leetcode150",
            "neetcode150"
        ],
        "representative": True
    },
    {
        "id": "lc-201",
        "leetcode_id": 201,
        "title": "Bitwise AND of Numbers Range",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "bit_manipulation",
        "primary_pattern": "bit_manipulation",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/bitwise-and-of-numbers-range/",
        "tags": [
            "bit manipulation"
        ],
        "prerequisite_patterns": [
            "bit_manipulation"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Queue =================
    {
        "id": "lc-232",
        "leetcode_id": 232,
        "title": "Implement Queue using Stacks",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "queue",
        "primary_pattern": "queue",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/implement-queue-using-stacks/",
        "tags": [
            "stack",
            "design",
            "queue"
        ],
        "prerequisite_patterns": [
            "stack"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-225",
        "leetcode_id": 225,
        "title": "Implement Stack using Queues",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "queue",
        "primary_pattern": "queue",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/implement-stack-using-queues/",
        "tags": [
            "queue",
            "design",
            "stack"
        ],
        "prerequisite_patterns": [
            "queue"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-933",
        "leetcode_id": 933,
        "title": "Number of Recent Calls",
        "difficulty": "easy",
        "learning_stage": "core",
        "pattern": "queue",
        "primary_pattern": "queue",
        "estimated_minutes": 20,
        "leetcode_url": "https://leetcode.com/problems/number-of-recent-calls/",
        "tags": [
            "design",
            "queue",
            "data stream"
        ],
        "prerequisite_patterns": [
            "queue"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-649",
        "leetcode_id": 649,
        "title": "Dota2 Senate",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "queue",
        "primary_pattern": "queue",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/dota2-senate/",
        "tags": [
            "string",
            "greedy",
            "queue"
        ],
        "prerequisite_patterns": [
            "queue"
        ],
        "frequency": "low",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-622",
        "leetcode_id": 622,
        "title": "Design Circular Queue",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "queue",
        "primary_pattern": "queue",
        "estimated_minutes": 40,
        "leetcode_url": "https://leetcode.com/problems/design-circular-queue/",
        "tags": [
            "design",
            "queue",
            "array",
            "linked list"
        ],
        "prerequisite_patterns": [
            "queue"
        ],
        "frequency": "medium",
        "companies": [
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Trie =================
    {
        "id": "lc-208",
        "leetcode_id": 208,
        "title": "Implement Trie (Prefix Tree)",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "trie",
        "primary_pattern": "trie",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/implement-trie-prefix-tree/",
        "tags": [
            "hash table",
            "string",
            "design",
            "trie"
        ],
        "prerequisite_patterns": [
            "trees"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-211",
        "leetcode_id": 211,
        "title": "Design Add and Search Words Data Structure",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trie",
        "primary_pattern": "trie",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/design-add-and-search-words-data-structure/",
        "tags": [
            "string",
            "depth-first search",
            "design",
            "trie"
        ],
        "prerequisite_patterns": [
            "trie"
        ],
        "frequency": "medium",
        "companies": [
            "meta"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-648",
        "leetcode_id": 648,
        "title": "Replace Words",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "trie",
        "primary_pattern": "trie",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/replace-words/",
        "tags": [
            "array",
            "hash table",
            "string",
            "trie"
        ],
        "prerequisite_patterns": [
            "trie"
        ],
        "frequency": "low",
        "companies": [
            "uber"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-212",
        "leetcode_id": 212,
        "title": "Word Search II",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "trie",
        "primary_pattern": "trie",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/word-search-ii/",
        "tags": [
            "array",
            "string",
            "backtracking",
            "trie",
            "matrix"
        ],
        "prerequisite_patterns": [
            "trie",
            "backtracking"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-1268",
        "leetcode_id": 1268,
        "title": "Search Suggestions System",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "trie",
        "primary_pattern": "trie",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/search-suggestions-system/",
        "tags": [
            "array",
            "string",
            "trie",
            "sorting",
            "heap (priority queue)"
        ],
        "prerequisite_patterns": [
            "trie"
        ],
        "frequency": "high",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Union Find =================
    {
        "id": "lc-547",
        "leetcode_id": 547,
        "title": "Number of Provinces",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "union_find",
        "primary_pattern": "union_find",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/number-of-provinces/",
        "tags": [
            "depth-first search",
            "breadth-first search",
            "union find",
            "graph"
        ],
        "prerequisite_patterns": [
            "graphs"
        ],
        "frequency": "high",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-721",
        "leetcode_id": 721,
        "title": "Accounts Merge",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "union_find",
        "primary_pattern": "union_find",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/accounts-merge/",
        "tags": [
            "array",
            "hash table",
            "string",
            "depth-first search",
            "breadth-first search",
            "union find"
        ],
        "prerequisite_patterns": [
            "union_find",
            "hashing"
        ],
        "frequency": "high",
        "companies": [
            "facebook",
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-685",
        "leetcode_id": 685,
        "title": "Redundant Connection II",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "union_find",
        "primary_pattern": "union_find",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/redundant-connection-ii/",
        "tags": [
            "depth-first search",
            "breadth-first search",
            "union find",
            "graph"
        ],
        "prerequisite_patterns": [
            "union_find"
        ],
        "frequency": "medium",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    # ================= Recursion =================
    {
        "id": "lc-509",
        "leetcode_id": 509,
        "title": "Fibonacci Number",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "recursion",
        "primary_pattern": "recursion",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/fibonacci-number/",
        "tags": [
            "math",
            "dynamic programming",
            "recursion",
            "memoization"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-344",
        "leetcode_id": 344,
        "title": "Reverse String",
        "difficulty": "easy",
        "learning_stage": "foundation",
        "pattern": "recursion",
        "primary_pattern": "recursion",
        "estimated_minutes": 15,
        "leetcode_url": "https://leetcode.com/problems/reverse-string/",
        "tags": [
            "two pointers",
            "string"
        ],
        "prerequisite_patterns": [],
        "frequency": "medium",
        "companies": [
            "apple"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-50",
        "leetcode_id": 50,
        "title": "Pow(x, n)",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "recursion",
        "primary_pattern": "recursion",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/powx-n/",
        "tags": [
            "math",
            "recursion"
        ],
        "prerequisite_patterns": [
            "recursion"
        ],
        "frequency": "high",
        "companies": [
            "facebook"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-95",
        "leetcode_id": 95,
        "title": "Unique Binary Search Trees II",
        "difficulty": "medium",
        "learning_stage": "advanced",
        "pattern": "recursion",
        "primary_pattern": "recursion",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/unique-binary-search-trees-ii/",
        "tags": [
            "dynamic programming",
            "backtracking",
            "tree",
            "binary search tree",
            "binary tree"
        ],
        "prerequisite_patterns": [
            "recursion",
            "trees"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Sorting =================
    {
        "id": "lc-912",
        "leetcode_id": 912,
        "title": "Sort an Array",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "sorting",
        "primary_pattern": "sorting",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/sort-an-array/",
        "tags": [
            "array",
            "divide and conquer",
            "sorting",
            "heap (priority queue)",
            "merge sort",
            "bucket sort",
            "radix sort"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "amazon",
            "microsoft"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-75",
        "leetcode_id": 75,
        "title": "Sort Colors",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "sorting",
        "primary_pattern": "sorting",
        "estimated_minutes": 25,
        "leetcode_url": "https://leetcode.com/problems/sort-colors/",
        "tags": [
            "array",
            "two pointers",
            "sorting"
        ],
        "prerequisite_patterns": [],
        "frequency": "high",
        "companies": [
            "facebook",
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-179",
        "leetcode_id": 179,
        "title": "Largest Number",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "sorting",
        "primary_pattern": "sorting",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/largest-number/",
        "tags": [
            "array",
            "string",
            "greedy",
            "sorting"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "high",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-164",
        "leetcode_id": 164,
        "title": "Maximum Gap",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "sorting",
        "primary_pattern": "sorting",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/maximum-gap/",
        "tags": [
            "array",
            "sorting",
            "bucket sort",
            "radix sort"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "medium",
        "companies": [],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-493",
        "leetcode_id": 493,
        "title": "Reverse Pairs",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "sorting",
        "primary_pattern": "sorting",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/reverse-pairs/",
        "tags": [
            "array",
            "binary search",
            "divide and conquer",
            "binary indexed tree",
            "segment tree",
            "merge sort",
            "ordered set"
        ],
        "prerequisite_patterns": [
            "sorting"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    # ================= Segment Tree =================
    {
        "id": "lc-307",
        "leetcode_id": 307,
        "title": "Range Sum Query - Mutable",
        "difficulty": "medium",
        "learning_stage": "foundation",
        "pattern": "segment_tree",
        "primary_pattern": "segment_tree",
        "estimated_minutes": 35,
        "leetcode_url": "https://leetcode.com/problems/range-sum-query-mutable/",
        "tags": [
            "array",
            "design",
            "binary indexed tree",
            "segment tree"
        ],
        "prerequisite_patterns": [
            "arrays"
        ],
        "frequency": "medium",
        "companies": [
            "amazon"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-729",
        "leetcode_id": 729,
        "title": "My Calendar I",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "segment_tree",
        "primary_pattern": "segment_tree",
        "estimated_minutes": 30,
        "leetcode_url": "https://leetcode.com/problems/my-calendar-i/",
        "tags": [
            "array",
            "binary search",
            "design",
            "interval tree",
            "ordered set"
        ],
        "prerequisite_patterns": [
            "segment_tree"
        ],
        "frequency": "high",
        "companies": [
            "google"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-731",
        "leetcode_id": 731,
        "title": "My Calendar II",
        "difficulty": "medium",
        "learning_stage": "core",
        "pattern": "segment_tree",
        "primary_pattern": "segment_tree",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/my-calendar-ii/",
        "tags": [
            "array",
            "binary search",
            "design",
            "interval tree",
            "ordered set"
        ],
        "prerequisite_patterns": [
            "segment_tree"
        ],
        "frequency": "medium",
        "companies": [
            "google"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-732",
        "leetcode_id": 732,
        "title": "My Calendar III",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "segment_tree",
        "primary_pattern": "segment_tree",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/my-calendar-iii/",
        "tags": [
            "array",
            "binary search",
            "design",
            "segment tree",
            "interval tree",
            "ordered set"
        ],
        "prerequisite_patterns": [
            "segment_tree"
        ],
        "frequency": "medium",
        "companies": [
            "google"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-315",
        "leetcode_id": 315,
        "title": "Count of Smaller Numbers After Self",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "segment_tree",
        "primary_pattern": "segment_tree",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/count-of-smaller-numbers-after-self/",
        "tags": [
            "array",
            "binary search",
            "divide and conquer",
            "binary indexed tree",
            "segment tree",
            "merge sort",
            "ordered set"
        ],
        "prerequisite_patterns": [
            "segment_tree",
            "sorting"
        ],
        "frequency": "high",
        "companies": [
            "amazon",
            "google"
        ],
        "source_lists": [],
        "representative": True
    },
    {
        "id": "lc-699",
        "leetcode_id": 699,
        "title": "Falling Squares",
        "difficulty": "hard",
        "learning_stage": "advanced",
        "pattern": "segment_tree",
        "primary_pattern": "segment_tree",
        "estimated_minutes": 45,
        "leetcode_url": "https://leetcode.com/problems/falling-squares/",
        "tags": [
            "array",
            "segment tree",
            "ordered set"
        ],
        "prerequisite_patterns": [
            "segment_tree"
        ],
        "frequency": "medium",
        "companies": [
            "riot games"
        ],
        "source_lists": [],
        "representative": True
    }
]

# ---------------------------------------------------------------------------
# Derived registries — computed once at module load, O(1) lookups at runtime
# ---------------------------------------------------------------------------

# Inverse of PATTERN_TO_DOMAIN: display label → internal pattern key.
# e.g. "Sliding Window" → "sliding_window"
# Used by mission_engine._pattern_from_subtopic() to translate UI subtopic
# selections into problem-bank pattern keys.
# Contract: dict, accessed via .get(sub) — no change from original.
SUBTOPIC_TO_PATTERN: dict = {
    label: pat for pat, (_, label) in PATTERN_TO_DOMAIN.items()
}

# Internal index — built once at module load for O(1) performance.
# Private: consumers use the public function APIs below.
from collections import defaultdict as _defaultdict

_by_pattern_index: "_defaultdict[str, list]" = _defaultdict(list)
for _prob in PROBLEMS:
    _by_pattern_index[_prob["pattern"]].append(_prob)

_by_pattern_index = dict(_by_pattern_index)  # freeze to plain dict

_pattern_counts_index: dict = {
    pat: len(probs) for pat, probs in _by_pattern_index.items()
}

# O(1) lookup by problem id string (e.g. "lc-76").
_problems_index: dict = {p["id"]: p for p in PROBLEMS}


# ---------------------------------------------------------------------------
# Public callable API — every consumer calls these as functions.
#
# Original contract (pre-Sprint work):
#   problems_by_pattern(pattern: str) -> list[dict]
#   pattern_counts()                  -> dict[str, int]
#   problem_by_id(problem_id: str)    -> dict | None
#
# All three are called with parentheses throughout the codebase:
#   - mission_engine.py imports problems_by_pattern
#   - assessment_generator.py: problem_bank.problems_by_pattern(pattern)
#   - routes_missions.py: pattern_counts()
#   - routes_missions.py: problem_by_id(pid)
#   - routes_roadmap.py: problem_by_id(pid)
# ---------------------------------------------------------------------------

def problems_by_pattern(pattern: str) -> list:
    """Return all problems for *pattern* in canonical curriculum order.

    Returns an empty list for unknown patterns — never raises KeyError.
    """
    return list(_by_pattern_index.get(pattern, []))


def pattern_counts() -> dict:
    """Return a dict mapping every pattern key to its problem count."""
    return dict(_pattern_counts_index)


def problem_by_id(problem_id: str) -> dict | None:
    """Return the problem dict for *problem_id*, or None if not found."""
    return _problems_index.get(problem_id)
