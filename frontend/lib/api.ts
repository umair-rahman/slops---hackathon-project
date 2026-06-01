// ── API Client for Marginalia Backend ───────────────────────────────────────

import type {
  GhostScore,
  RecentAnalysisItem,
  ReviewerProfile,
  ScanProgressEvent,
} from "./types";

// API Base URL — Railway production backend
const API_BASE = "https://slops-hackathon-project-production.up.railway.app";

export async function analyzeReview(params: {
  review_text: string;
  paper_arxiv_id?: string;
  paper_url?: string;
}): Promise<GhostScore> {
  const res = await fetch(`${API_BASE}/api/analyze/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<GhostScore>;
}

export async function analyzeBatch(params: {
  reviews: { review_id?: string; review_text: string }[];
  paper_arxiv_id?: string;
}): Promise<GhostScore[]> {
  const res = await fetch(`${API_BASE}/api/analyze/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}

export function scanConference(
  venueId: string,
  maxPapers: number = 50,
  onEvent: (event: ScanProgressEvent) => void,
  onError: (error: Error) => void
): () => void {
  const url = `${API_BASE}/api/scan/conference?venue_id=${encodeURIComponent(venueId)}&max_papers=${maxPapers}`;
  const es = new EventSource(url);

  es.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as ScanProgressEvent;
      onEvent(event);
      if (event.type === "complete" || event.type === "error") {
        es.close();
      }
    } catch {
      onError(new Error("Failed to parse SSE event"));
    }
  };

  es.onerror = () => {
    onError(new Error("SSE connection failed"));
    es.close();
  };

  return () => es.close();
}

export async function getReviewerProfile(reviewerId: string): Promise<ReviewerProfile> {
  const url = `${API_BASE}/api/reviewer/${encodeURIComponent(reviewerId)}`;
  const res = await fetch(url);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}

export async function getRecentAnalyses(limit: number = 10): Promise<{
  count: number;
  items: RecentAnalysisItem[];
}> {
  const res = await fetch(`${API_BASE}/api/history/recent?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
