export interface DetectedEntities {
  streets: string[];
  places: string[];
  businesses: string[];
  times: string[];
  coordinates: { lat: number; lon: number }[];
}

export interface VulnerabilityFinding {
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  finding: string;
  evidence_count: number;
}

export interface StaticLandmark {
  type: "street" | "coordinates";
  value: string | { lat: number; lon: number } | { noise_count: number };
  appearances: number;
  percentage: number;
  classification: string;
  signal?: "routine_exposure" | "anomalous_disclosure";
}

export interface EntityTriplet {
  location: string;
  time: string | null;
  day: string | null;
  activity: string | null;
  entry_count: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  detail?: string;
  similarity?: number;
  percentage?: number;
  classification?: string;
  cluster_id?: number | null;
  cluster_name?: string | null;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  label: string;
}

export interface ExposureMap {
  total_data_points: number;
  unique_streets: number;
  known_locations: number;
  unique_businesses: number;
  tracked_activities: number;
  day_patterns: number;
}

export interface TimeContext {
  source: "exif" | "text_keyword";
  period: string;
  day_of_week?: string;
  hour?: number;
  datetime?: string;
  keyword?: string;
  window?: string;
}

export interface AnalysisSignals {
  draft_text_length: number;
  ocr_text: string | null;
  ocr_high_value: unknown[] | null;
  exif_metadata: Record<string, unknown> | null;
  time_context: TimeContext | null;
  merged_length: number;
}

export interface ClusterSummary {
  id: number;
  name: string;
  size: number;
  risk_score: number;
  top_terms: string[];
  is_target: boolean;
}

export interface ClusteringResult {
  n_clusters: number;
  draft_cluster_id: number;
  draft_cluster_name: string;
  draft_hits_target: boolean;
  cluster_confidence: number;
  clusters: ClusterSummary[];
}

export interface AnalyzeThreatEmpty {
  status: "empty";
  message: string;
  web: { nodes: GraphNode[]; edges: GraphEdge[] };
  exposure_map: ExposureMap;
}

export interface AnalyzeThreatInitializing {
  status: "initializing";
  message: string;
  detected_entities: DetectedEntities;
  vulnerability_map: VulnerabilityFinding[];
  breach_probability: number;
  final_conclusion: string;
  web: { nodes: GraphNode[]; edges: GraphEdge[] };
  exposure_map: ExposureMap;
}

export interface AnalyzeThreatAnalyzed {
  status: "analyzed";
  detected_entities: DetectedEntities;
  category_similarity: Record<string, number>;
  breach_probability: number;
  vulnerability_map: VulnerabilityFinding[];
  static_landmarks: StaticLandmark[];
  entity_triplets: EntityTriplet[];
  final_conclusion: string;
  signals: AnalysisSignals;
  web: { nodes: GraphNode[]; edges: GraphEdge[] };
  exposure_map: ExposureMap;
  clustering?: ClusteringResult;
}

export type AnalyzeThreatResult =
  | AnalyzeThreatEmpty
  | AnalyzeThreatInitializing
  | AnalyzeThreatAnalyzed;

export interface FootprintEntryDict {
  id: string;
  label: string;
  text: string;
  entities: DetectedEntities;
  metadata: Record<string, unknown>;
  time_context: TimeContext | null;
  has_gps: boolean;
  ingested_at: string;
}

export interface FootprintResponse {
  exposure_map: ExposureMap;
  entries: FootprintEntryDict[];
}

export interface IngestManualEmpty {
  status: "empty";
  message: string;
}

export interface IngestManualSecured {
  status: "secured";
  message: string;
  entry: FootprintEntryDict;
  detected_entities: DetectedEntities;
  exposure_map: ExposureMap;
  final_conclusion: string;
}

export type IngestManualResult = IngestManualEmpty | IngestManualSecured;

export interface IngestExportSynced {
  status: "synced";
  posts_available: number;
  posts_ingested: number;
  posts_skipped: number;
  exposure_map: ExposureMap;
}

export interface IngestExportError {
  status: "error";
  message: string;
}

export type IngestExportResult = IngestExportSynced | IngestExportError;

export interface ScoreHistoryEntryDict {
  timestamp: string;
  breach_probability: number;
  severity_counts: Record<"critical" | "high" | "medium" | "low", number>;
  entity_counts: Record<string, number>;
}

export interface ScoreHistoryResponse {
  history: ScoreHistoryEntryDict[];
}
