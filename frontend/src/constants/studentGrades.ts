/**
 * Student grade / division options for onboarding and profile editing.
 * Grade 5 is split into 5A and 5B only (school structure).
 */
export const STUDENT_GRADE_OPTIONS: readonly string[] = [
  'Pre-Nursery',
  'Nursery',
  'KG',
  ...[1, 2, 3, 4].map((n) => `Grade ${n}`),
  'Grade 5A',
  'Grade 5B',
  ...[6, 7, 8, 9, 10, 11, 12].map((n) => `Grade ${n}`),
];
