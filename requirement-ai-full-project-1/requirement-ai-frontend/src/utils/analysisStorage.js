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
  return requirements.flatMap((item) => {
    const value = item?.analysis?.missing_information;
    if (Array.isArray(value)) return value.filter(Boolean);
    return value ? [value] : [];
  });
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
