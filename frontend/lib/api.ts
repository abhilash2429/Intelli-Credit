/**
 * Unified API client for legacy endpoints + new /api/v1 contract.
 */

import axios from 'axios';

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1']);
const DEFAULT_TIMEOUT_MS = 20000;
const UPLOAD_TIMEOUT_MS = 240000;

function normalizeBase(base: string): string {
  return String(base || '').replace(/\/+$/, '');
}

function isLocalHost(hostname: string): boolean {
  return LOCAL_HOSTNAMES.has(hostname);
}

function inferInitialApiBase(): string {
  const envBase = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (envBase) return normalizeBase(envBase);

  if (typeof window !== 'undefined' && isLocalHost(window.location.hostname)) {
    // Prefer local uvicorn default first; retry logic can fall back to 8001.
    return 'http://localhost:8000';
  }

  return 'http://localhost:8000';
}

let activeApiBase = inferInitialApiBase();

function setActiveApiBase(base: string): void {
  const normalized = normalizeBase(base);
  if (normalized) {
    activeApiBase = normalized;
  }
}

function getActiveApiBase(): string {
  return activeApiBase;
}

function buildApiBaseCandidates(): string[] {
  const candidates: string[] = [];
  const add = (base?: string | null) => {
    if (!base) return;
    const normalized = normalizeBase(base);
    if (normalized && !candidates.includes(normalized)) {
      candidates.push(normalized);
    }
  };

  add(getActiveApiBase());
  add(process.env.NEXT_PUBLIC_API_URL?.trim());

  if (typeof window !== 'undefined' && isLocalHost(window.location.hostname)) {
    const host = window.location.hostname;
    add(`http://${host}:8001`);
    add(`http://${host}:8000`);
    add('http://localhost:8001');
    add('http://localhost:8000');
    add('http://127.0.0.1:8001');
    add('http://127.0.0.1:8000');
  }

  return candidates;
}

const api = axios.create({ timeout: DEFAULT_TIMEOUT_MS });

api.interceptors.request.use((config) => {
  if (!config.baseURL) {
    config.baseURL = getActiveApiBase();
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if (response?.config?.baseURL) {
      setActiveApiBase(String(response.config.baseURL));
    }
    return response;
  },
  async (error) => {
    const cfg = error?.config as any;
    if (!cfg) {
      return Promise.reject(error);
    }

    const status = Number(error?.response?.status || 0);
    const code = String(error?.code || '');
    const urlPath = String(cfg?.url || '');
    const shouldRetry404 = status === 404 && urlPath.includes('/api/v1/');
    const shouldRetry =
      !error?.response ||
      code === 'ERR_NETWORK' ||
      code === 'ECONNABORTED' ||
      shouldRetry404 ||
      status >= 500;

    if (!shouldRetry || cfg.__baseRetryAttempted) {
      return Promise.reject(error);
    }

    const attempted = new Set<string>();
    if (cfg.baseURL) attempted.add(normalizeBase(String(cfg.baseURL)));
    attempted.add(getActiveApiBase());

    for (const base of buildApiBaseCandidates()) {
      if (attempted.has(base)) continue;
      attempted.add(base);
      try {
        const retryConfig = {
          ...cfg,
          baseURL: base,
          timeout: DEFAULT_TIMEOUT_MS,
          __baseRetryAttempted: true,
        };
        const response = await axios.request(retryConfig);
        setActiveApiBase(base);
        return response;
      } catch {
        // Try next candidate base.
      }
    }

    return Promise.reject(error);
  }
);

export interface ResponseMeta {
  request_id: string;
  timestamp: string;
  processing_time_ms: number;
}

export interface APIEnvelope<T> {
  status: 'success' | 'error' | 'processing';
  data: T;
  meta: ResponseMeta;
}

// ----------------- Legacy Types -----------------

export interface IngestResponse {
  company_id: string;
  company_name: string;
  file_paths: string[];
  file_count: number;
}

export interface PipelineResponse {
  run_id: string;
  status: string;
}

export interface QualitativeInput {
  notes: string;
  factory_capacity_pct?: number;
  management_assessment?: string;
  submitted_by?: string;
}

export interface RiskScore {
  company_id: string;
  rule_based_score: number;
  ml_stress_probability: number;
  final_risk_score: number;
  risk_category: string;
  rule_violations: string[];
  risk_strengths: string[];
  shap_values: Record<string, number>;
  decision: string;
  recommended_limit_crore: number;
  interest_premium_bps: number;
  decision_rationale: string;
}

export interface ShapEntry {
  feature: string;
  value: number;
  direction: string;
}

export interface CamData {
  cam_text: string;
  docx_path: string;
  pdf_path: string;
}

export interface ChatResponse {
  response: string;
  sources: string[];
}

export interface IntegrationStatus {
  configured: boolean;
  ok: boolean;
  error?: string;
  [key: string]: any;
}

export interface IntegrationHealthResponse {
  live_checks: boolean;
  overall_ok: boolean;
  integrations: {
    gemini: IntegrationStatus;
    firecrawl: IntegrationStatus;
    qwen_vl: IntegrationStatus;
    databricks: IntegrationStatus;
  };
}

// ----------------- v1 Types -----------------

export interface CompanyCreateInput {
  name: string;
  cin?: string;
  sector: string;
  loan_amount_requested: number;
  loan_tenor_months: number;
  loan_purpose?: string;
}

export interface DueDiligenceV1Input {
  factory_visit_date?: string;
  capacity_utilization_percent?: number;
  factory_condition?: string;
  inventory_levels?: string;
  management_cooperation?: string;
  free_text_notes: string;
  management_interview_rating?: number;
  borrower_finance_officer_name?: string;
  borrower_finance_officer_role?: string;
  borrower_finance_officer_email?: string;
  borrower_finance_officer_phone?: string;
  borrower_business_highlights?: string;
  borrower_major_customers?: string;
  borrower_contingent_liabilities?: string;
  borrower_planned_capex?: string;
  borrower_disclosed_risks?: string;
  key_management_persons: Array<{
    name: string;
    role: string;
    credibility_score?: number;
    notes?: string;
  }>;
}

// ----------------- Legacy API -----------------

export async function uploadDocuments(
  companyName: string,
  sector: string,
  files: File[]
): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append('company_name', companyName);
  formData.append('sector', sector);
  files.forEach((file) => formData.append('files', file));

  const { data } = await api.post<IngestResponse>('/ingest', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function runPipeline(
  companyId: string,
  companyName: string,
  documentPaths: string[]
): Promise<PipelineResponse> {
  const { data } = await api.post<PipelineResponse>('/run-pipeline', {
    company_id: companyId,
    company_name: companyName,
    document_paths: documentPaths,
  });
  return data;
}

export function getPipelineStreamUrl(companyId: string): string {
  return `${getActiveApiBase()}/pipeline-stream/${companyId}`;
}

export async function submitQualitative(
  companyId: string,
  input: QualitativeInput
): Promise<{ status: string }> {
  const { data } = await api.post(`/submit-qualitative/${companyId}`, {
    notes: input.notes,
    capacity_pct: input.factory_capacity_pct,
    mgmt: input.management_assessment,
  });
  return data;
}

export async function saveQualitative(
  companyId: string,
  input: QualitativeInput
): Promise<{ id: string; status: string }> {
  const { data } = await api.post(`/qualitative/${companyId}`, input);
  return data;
}

export async function getQualitative(
  companyId: string
): Promise<QualitativeInput | null> {
  const { data } = await api.get(`/qualitative/${companyId}`);
  return data;
}

export async function getScore(companyId: string): Promise<RiskScore> {
  const { data } = await api.get<RiskScore>(`/score/${companyId}`);
  return data;
}

export async function getShapValues(companyId: string): Promise<ShapEntry[]> {
  const { data } = await api.get<ShapEntry[]>(`/score/${companyId}/shap`);
  return data;
}

export async function getCam(companyId: string): Promise<CamData> {
  const { data } = await api.get<CamData>(`/cam/${companyId}`);
  return data;
}

export function getDocxDownloadUrl(companyId: string): string {
  return `${getActiveApiBase()}/cam/${companyId}/download/docx`;
}

export function getPdfDownloadUrl(companyId: string): string {
  return `${getActiveApiBase()}/cam/${companyId}/download/pdf`;
}

export async function chatWithCam(
  companyId: string,
  message: string
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', {
    company_id: companyId,
    message,
  });
  return data;
}

// ----------------- v1 API -----------------

export async function createCompanyV1(
  payload: CompanyCreateInput
): Promise<APIEnvelope<any>> {
  const { data } = await api.post<APIEnvelope<any>>('/api/v1/companies', payload);
  return data;
}

export async function uploadDocumentsV1(
  companyId: string,
  files: File[]
): Promise<APIEnvelope<any>> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const { data } = await api.post<APIEnvelope<any>>(
    `/api/v1/companies/${companyId}/documents`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: UPLOAD_TIMEOUT_MS,
    }
  );
  return data;
}

export async function triggerAnalysisV1(companyId: string): Promise<APIEnvelope<any>> {
  const { data } = await api.post<APIEnvelope<any>>(
    `/api/v1/companies/${companyId}/analyze`
  );
  return data;
}

export function getStatusStreamV1(companyId: string): string {
  return `${getActiveApiBase()}/api/v1/companies/${companyId}/status`;
}

export async function submitDueDiligenceV1(
  companyId: string,
  payload: DueDiligenceV1Input
): Promise<APIEnvelope<any>> {
  const { data } = await api.post<APIEnvelope<any>>(
    `/api/v1/companies/${companyId}/dd-input`,
    payload
  );
  return data;
}

export async function previewDueDiligenceV1(
  companyName: string,
  freeTextNotes: string
): Promise<APIEnvelope<any>> {
  const { data } = await api.post<APIEnvelope<any>>('/api/v1/due-diligence/preview', {
    company_name: companyName,
    free_text_notes: freeTextNotes,
  });
  return data;
}

export async function getResultsV1(companyId: string): Promise<APIEnvelope<any>> {
  const { data } = await api.get<APIEnvelope<any>>(`/api/v1/companies/${companyId}/results`);
  return data;
}

export async function getExplainV1(companyId: string): Promise<APIEnvelope<any>> {
  const { data } = await api.get<APIEnvelope<any>>(`/api/v1/companies/${companyId}/explain`);
  return data;
}

export async function getResearchV1(companyId: string): Promise<APIEnvelope<any>> {
  const { data } = await api.get<APIEnvelope<any>>(`/api/v1/companies/${companyId}/research`);
  return data;
}

export function getReportUrlV1(companyId: string): string {
  return `${getActiveApiBase()}/api/v1/companies/${companyId}/report`;
}

export function getReportPdfUrlV1(companyId: string): string {
  return `${getActiveApiBase()}/api/v1/companies/${companyId}/report/pdf`;
}

export async function chatWithCamV1(
  companyId: string,
  message: string
): Promise<ChatResponse> {
  const { data } = await api.post<APIEnvelope<ChatResponse>>(
    `/api/v1/companies/${companyId}/chat`,
    { message },
    { timeout: 90000 }
  );
  return data.data;
}

// ── Loan Application API ──

export interface LoanCreateInput {
  company_id: string;
  loan_type: string;
  loan_amount_cr: number;
  tenure_months: number;
  proposed_rate_pct?: number;
  repayment_mode?: string;
  purpose?: string;
  collateral_type?: string;
  collateral_value_cr?: number;
}

export async function createLoanApplication(
  payload: LoanCreateInput
): Promise<APIEnvelope<any>> {
  const { company_id, ...body } = payload;
  const { data } = await api.post<APIEnvelope<any>>(`/api/v1/companies/${company_id}/loan`, body);
  return data;
}

// ── Classification API ──

export interface ClassificationItem {
  id: string;
  document_id: string;
  auto_type: string;
  auto_confidence: number;
  auto_reasoning: string;
  human_approved: boolean | null;
  human_type_override: string | null;
  extracted_fields: Record<string, any> | null;
}

export async function getClassifications(
  companyId: string
): Promise<APIEnvelope<ClassificationItem[]>> {
  const { data } = await api.get<APIEnvelope<ClassificationItem[]>>(
    `/api/v1/classifications/${companyId}`
  );
  return data;
}

export async function updateClassification(
  classificationId: string,
  payload: { human_approved?: boolean; human_type_override?: string }
): Promise<APIEnvelope<any>> {
  const { data } = await api.patch<APIEnvelope<any>>(
    `/api/v1/classifications/${classificationId}`,
    payload
  );
  return data;
}

export async function extractSchema(
  classificationId: string,
  fields: string[]
): Promise<APIEnvelope<any>> {
  const { data } = await api.post<APIEnvelope<any>>(
    `/api/v1/classifications/${classificationId}/extract`,
    { fields }
  );
  return data;
}

// ── SWOT API ──

export interface SwotData {
  strengths: Array<{ point: string; evidence: string; source: string }>;
  weaknesses: Array<{ point: string; evidence: string; source: string }>;
  opportunities: Array<{ point: string; evidence: string; source: string }>;
  threats: Array<{ point: string; evidence: string; source: string }>;
  sector_outlook: string;
  macro_signals: Record<string, number | null>;
  investment_thesis: string;
  recommendation: string;
  generated_at: string | null;
}

export async function getSwotV1(companyId: string): Promise<APIEnvelope<SwotData>> {
  const { data } = await api.get<APIEnvelope<SwotData>>(
    `/api/v1/companies/${companyId}/swot`
  );
  return data;
}

export function getInvestmentReportUrl(companyId: string): string {
  return `${getActiveApiBase()}/api/v1/companies/${companyId}/investment-report`;
}

export async function healthCheck(): Promise<any> {
  const { data } = await api.get('/api/v1/health');
  return data;
}

function normalizeIntegrationHealthEnvelope(payload: any): APIEnvelope<IntegrationHealthResponse> {
  if (payload && typeof payload === 'object' && 'status' in payload && 'data' in payload) {
    return payload as APIEnvelope<IntegrationHealthResponse>;
  }
  if (payload && typeof payload === 'object' && 'integrations' in payload) {
    return {
      status: 'success',
      data: payload as IntegrationHealthResponse,
      meta: {
        request_id: 'client-fallback',
        timestamp: new Date().toISOString(),
        processing_time_ms: 0,
      },
    };
  }
  throw new Error('Invalid integration health response format');
}

export async function getIntegrationHealthV1(
  liveChecks = false
): Promise<APIEnvelope<IntegrationHealthResponse>> {
  const liveParam = liveChecks ? 'true' : 'false';
  const primaryPath = `/api/v1/health/integrations?live=${liveParam}`;
  try {
    const { data } = await api.get<APIEnvelope<IntegrationHealthResponse>>(primaryPath, {
      timeout: 120000,
    });
    return data;
  } catch (primaryErr: any) {
    const fallbackUrls: string[] = [];
    for (const base of buildApiBaseCandidates()) {
      fallbackUrls.push(`${base}/api/v1/health/integrations?live=${liveParam}`);
      fallbackUrls.push(`${base}/health/integrations?live=${liveParam}`);
    }

    for (const url of Array.from(new Set(fallbackUrls))) {
      try {
        const { data } = await axios.get(url, { timeout: 120000 });
        try {
          setActiveApiBase(new URL(url).origin);
        } catch {
          // Keep current API base if URL parsing fails.
        }
        return normalizeIntegrationHealthEnvelope(data);
      } catch {
        // Try next fallback URL.
      }
    }

    throw primaryErr;
  }
}
