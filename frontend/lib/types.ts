// ── Core Types for Marginalia Frontend ──────────────────────────────────────

export interface AnchorDetail {
  text: string;
  anchor_type: string;
}

export interface SentenceResult {
  text: string;
  anchor_count: number;
  anchors: AnchorDetail[];
  is_hallucinated: boolean;
  hallucination_reason?: string;
}

export interface SpecificityResult {
  score: number;
  anchors_per_100_words: number;
  total_anchors: number;
  sentences: SentenceResult[];
}

export interface AsymmetryResult {
  score: number;
  sim_abstract: number;
  sim_body: number;
  asymmetry_ratio: number;
  hallucinated_sentences: string[];
}

export interface BatchDNAResult {
  score: number | null;
  cluster_id: number | null;
  cluster_size: number | null;
  available: boolean;
  reason?: string;
}

export interface GhostScore {
  overall: number;
  label: string;
  confidence_low: number;
  confidence_high: number;
  specificity: SpecificityResult;
  asymmetry: AsymmetryResult;
  batch_dna: BatchDNAResult;
  explanation: string;
}

export interface ReviewerSummary {
  reviewer_id: string;
  total_reviews: number;
  avg_ghost_score: number;
  has_dna_cluster: boolean;
  drift_detected: boolean;
}

export interface ConferenceScanResult {
  venue_id: string;
  total_papers: number;
  total_reviews: number;
  flagged_count: number;
  flagged_percent: number;
  collusion_count?: number;
  top_suspect_reviewers: ReviewerSummary[];
  score_distribution: number[];
  avg_score?: number;
  message?: string;
}

export interface ScanProgressEvent {
  type: "progress" | "complete" | "error";
  message?: string;
  percent?: number;
  data?: ConferenceScanResult;
  error?: string;
}

export interface ReviewerProfileReview {
  review_id: string;
  paper_id: string;
  paper_title: string;
  venue_id: string;
  timestamp: number;
  specificity_score: number;
  anchor_count: number;
  cluster_id: number | null;
  cluster_size: number | null;
  ghost_score: number;
}

export interface ReviewerProfile {
  reviewer_id: string;
  total_reviews: number;
  avg_ghost_score: number;
  drift_detected: boolean;
  drift_strength: number;
  drift_point: number | null;
  cluster_count: number;
  time_on_task_score?: number;
  burst_detected?: boolean;
  burst_window_seconds?: number | null;
  implausible_count?: number;
  reviews: ReviewerProfileReview[];
}

export interface RecentAnalysisItem {
  id: number;
  paper_arxiv_id: string | null;
  overall_score: number;
  label: string;
  specificity_score: number;
  asymmetry_score: number;
  batch_dna_score: number | null;
  created_at: string;
}

export const SCORE_COLORS = {
  human: "#22c55e",
  uncertain: "#ea580c",
  ai: "#ef4444",
} as const;

export function getScoreColor(score: number): string {
  if (score < 40) return SCORE_COLORS.human;
  if (score < 65) return SCORE_COLORS.uncertain;
  return SCORE_COLORS.ai;
}

export function getScoreLabel(score: number): string {
  if (score < 25) return "Likely Human";
  if (score < 50) return "Uncertain — Lean Human";
  if (score < 70) return "Uncertain — Lean AI";
  if (score < 85) return "Likely AI-Generated";
  return "Almost Certainly AI";
}
