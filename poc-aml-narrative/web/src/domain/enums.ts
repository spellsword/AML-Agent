export enum Recommendation {
  CLOSE = 'Close',
  ESCALATE = 'Escalate',
  RFI = 'RFI',
}

export enum CaseStatus {
  AI_ANALYSIS = 'ai_analysis',
  CHECKER_REVIEW = 'checker_review',
  ESCALATED = 'escalated',
  CLOSED = 'closed',
  RFI_PENDING = 'rfi_pending',
}

export enum EvidenceSourceType {
  TRANSACTION = 'transaction',
  KYC = 'kyc',
  CTOS_UBO = 'ctos_ubo',
  SCREENING = 'screening',
  NNS_SEARCH = 'nns_search',
  PRIOR_ALERT = 'prior_alert',
  POLICY = 'policy',
}

export enum LLMErrorCode {
  LLM_TIMEOUT = 'LLM-TIMEOUT',
  LLM_SERVICE_UNAVAILABLE = 'LLM-SERVICE-UNAVAILABLE',
  LLM_CAPACITY_LIMIT = 'LLM-CAPACITY-LIMIT',
  LLM_CONTRACT_INVALID = 'LLM-CONTRACT-INVALID',
  LLM_AUTH_FAILURE = 'LLM-AUTH-FAILURE',
  LLM_OUTPUT_INVALID = 'LLM-OUTPUT-INVALID',
}

export const RETRYABLE_ERRORS: LLMErrorCode[] = [
  LLMErrorCode.LLM_TIMEOUT,
  LLMErrorCode.LLM_SERVICE_UNAVAILABLE,
  LLMErrorCode.LLM_CAPACITY_LIMIT,
];

export const NON_RETRYABLE_ERRORS: LLMErrorCode[] = [
  LLMErrorCode.LLM_CONTRACT_INVALID,
  LLMErrorCode.LLM_AUTH_FAILURE,
  LLMErrorCode.LLM_OUTPUT_INVALID,
];

export enum FallbackReason {
  LLM_TIMEOUT = 'LLM_TIMEOUT',
  LLM_OUTPUT_INVALID = 'LLM_OUTPUT_INVALID',
  LLM_AUTH_FAILURE = 'LLM_AUTH_FAILURE',
  LLM_SERVICE_UNAVAILABLE = 'LLM_SERVICE_UNAVAILABLE',
  PII_MASK_FAILED = 'PII_MASK_FAILED',
  CUMULATIVE_BUDGET_EXHAUSTED = 'CUMULATIVE_BUDGET_EXHAUSTED',
}

export enum JurorRoleFocus {
  QUANTITATIVE_METRICS = 'quantitative_metrics',
  RED_FLAG_EVIDENCE = 'red_flag_evidence',
  CUSTOMER_CONTEXT = 'customer_context',
}

export enum HumanAction {
  AGREE_CLOSE = 'agree_close',
  AGREE_ESCALATE = 'agree_escalate',
  OVERRIDE_TO_ESCALATE = 'override_to_escalate',
  OVERRIDE_TO_CLOSE = 'override_to_close',
  TRIGGER_RFI = 'trigger_rfi',
}

export enum RouteTarget {
  QC_REVIEW = 'qc_review',
  MANAGER_APPROVAL = 'manager_approval',
  GAML_L3_REVIEW = 'gaml_l3_review',
  RFI_PENDING = 'rfi_pending',
}

export enum RetrievalMode {
  ZERO_SHOT = 'zero_shot',
  SIMILAR_CASE = 'similar_case',
  VECTOR_UNAVAILABLE = 'vector_unavailable',
}

export enum ValidationCheckId {
  SCHEMA_VALID = 'schema_valid',
  EVIDENCE_REFS_RESOLVABLE = 'evidence_refs_resolvable',
  NO_UNMASKED_PII = 'no_unmasked_pii',
  NO_ABBREVIATION_IN_NARRATIVE = 'no_abbreviation_in_narrative',
  NO_PREMATURE_ESCALATE_STATE = 'no_premature_escalate_state',
  PROMPT_INJECTION_CLEAN = 'prompt_injection_clean',
  RECOMMENDATION_NOT_AUTONOMUS = 'recommendation_not_autonomous',
  FULL_TERMS_EXPANDED = 'full_terms_expanded',
}

export enum NarrativeSectionKey {
  CUSTOMER_PROFILE = 'customer_profile',
  TRANSACTION_ANALYSIS = 'transaction_analysis',
  RISK_INDICATORS = 'risk_indicators',
  SCREENING_OUTCOMES = 'screening_outcomes',
  CONNECTED_PARTIES = 'connected_parties',
  CONCLUSION = 'conclusion',
}