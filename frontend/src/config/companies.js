// Target companies for onboarding + settings.
//
// The canonical company list (ids, display names, accents) is GENERATED from
// the single backend registry (backend/company_intelligence/registry.json) via
// `python backend/scripts/compile_companies.py`. Do NOT hand-edit company ids
// here — edit the registry and recompile. `others` is a UI-only pseudo-company
// and is intentionally appended after the canonical list.
import GENERATED from './companies.generated.json';

export const TARGET_COMPANIES = [
  ...GENERATED.companies.map((c) => ({ id: c.id, name: c.name, accent: c.accent })),
  { id: 'others', name: 'Others', accent: '#94A3B8' },
];

export const POSITIONS = [
  { id: 'student',      label: 'Student',      hint: 'Currently in college / bootcamp' },
  { id: '0-1',          label: '0–1 Years',    hint: 'Fresh graduate / early career' },
  { id: '1-3',          label: '1–3 Years',    hint: 'Building fundamentals' },
  { id: '3-5',          label: '3–5 Years',    hint: 'Growing into senior IC' },
  { id: '5+',           label: '5+ Years',     hint: 'Senior / staff engineer' },
];

// Order mirrors the Knowledge Base's canonical subject order (see
// SUBJECT_ORDER in pages/knowledge/KnowledgeBase.jsx), filtered to only the
// subjects the onboarding self-assessment actually rates.
export const SELF_ASSESSMENT_TOPICS = [
  { key: 'programming_fundamentals', label: 'Programming Fundamentals' },
  { key: 'java',                     label: 'Java' },
  { key: 'dsa',                      label: 'Data Structures & Algorithms' },
  { key: 'dbms',                     label: 'DBMS' },
  { key: 'operating_systems',        label: 'Operating Systems' },
  { key: 'computer_networks',        label: 'Computer Networks' },
  { key: 'lld',                      label: 'Low-Level Design (LLD)' },
  { key: 'hld',                      label: 'High-Level Design (HLD)' },
];
