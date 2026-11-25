export const ANALYSIS_STORAGE_KEY = "reqai:lastAnalysis";

function isAnalysisResponse(value) {
  return Boolean(
    value &&
      typeof value === "object" &&
      value.success === true &&
      typeof value.filename === "string" &&
      Array.isArray(value.requirements)
  );
}

export function isSdlcRecommendation(value) {
  const factors = value?.supporting_factors;
  return Boolean(
    value &&
      typeof value === "object" &&
      (value.recommended_model === null ||
        (typeof value.recommended_model === "string" &&
          value.recommended_model.trim())) &&
      typeof value.reasoning === "string" &&
      value.reasoning.trim() &&
      factors &&
      typeof factors === "object" &&
      !Array.isArray(factors) &&
      Array.isArray(value.evidence_limitations) &&
      value.evidence_limitations.every((item) => typeof item === "string")
  );
}

export function hasSdlcOutcome(value) {
  return Boolean(
    isSdlcRecommendation(value?.sdlc_recommendation) ||
      (value?.sdlc_status === "failed" &&
        typeof value.sdlc_error === "string" &&
        value.sdlc_error.trim())
  );
}

const EMPTY_QUESTION_VALUES = new Set([
  "n/a",
  "n.a.",
  "na",
  "nil",
  "no",
  "no missing info",
  "no missing information",
  "none",
  "none provided",
  "not applicable",
  "not specified",
  "null",
  "yes",
]);
const QUESTION_START =
  /^(what|which|who|whom|whose|when|where|why|how|is|are|am|was|were|do|does|did|can|could|will|would|should|has|have|had|may|might|must)\b/i;

export function normalizeQuestionList(value) {
  const candidates = Array.isArray(value) ? value : [value];
  const seen = new Set();
  return candidates.flatMap((candidate) => {
    if (typeof candidate !== "string") return [];
    const question = candidate.replace(/\s+/g, " ").trim();
    const sentinel = question.toLowerCase();
    if (
      EMPTY_QUESTION_VALUES.has(sentinel) ||
      question.split(/\s+/).length < 3 ||
      !question.endsWith("?") ||
      !QUESTION_START.test(question)
    ) {
      return [];
    }

    const key = question.toLowerCase().replace(/[^\w]+/g, " ").trim();
    if (!key || seen.has(key)) return [];
    seen.add(key);
    return [question];
  });
}

export function getStoredAnalysis() {
  try {
    const stored = sessionStorage.getItem(ANALYSIS_STORAGE_KEY);
    if (!stored) return null;

    const parsed = JSON.parse(stored);
    return isAnalysisResponse(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function storeAnalysis(data) {
  if (!isAnalysisResponse(data)) {
    throw new TypeError("Cannot persist an incomplete document analysis response.");
  }
  if (!hasSdlcOutcome(data)) {
    throw new TypeError(
      "Cannot persist an analysis without a completed or explicitly failed SDLC outcome."
    );
  }
  sessionStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify(data));
  return data;
}

export function clearStoredAnalysis() {
  sessionStorage.removeItem(ANALYSIS_STORAGE_KEY);
}

export function getRequirements(data) {
  return Array.isArray(data?.requirements) ? data.requirements : [];
}

export function getMissingItems(requirements) {
  const seen = new Set();
  return requirements.flatMap((item) =>
    normalizeQuestionList(item?.analysis?.missing_information).filter((question) => {
      const key = question.toLowerCase().replace(/[^\w]+/g, " ").trim();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
  );
}

export function getAmbiguityItems(requirements) {
  return requirements.flatMap((item) => {
    const analysis = item?.analysis || {};
    const value = analysis.ambiguity ?? analysis.ambiguities;
    if (Array.isArray(value)) return value.filter(Boolean);
    return value ? [value] : [];
  });
}

export function getSdlcStages(requirements) {
  return [
    ...new Set(
      requirements
        .map((item) => {
          const analysis = item?.analysis || {};
          return analysis.sdlc_stage || analysis.sdlc || analysis.type;
        })
        .filter((stage) => typeof stage === "string" && stage.trim())
    ),
  ];
}

export function getAnalysisMetrics(analysis) {
  const requirements = getRequirements(analysis);
  return {
    requirementCount: requirements.length,
    missingInformationCount: getMissingItems(requirements).length,
    highPriorityCount: requirements.filter(
      (item) =>
        String(item?.analysis?.priority || "").trim().toLowerCase() === "high"
    ).length,
    sdlcPhaseCount: getSdlcStages(requirements).length,
  };
}
