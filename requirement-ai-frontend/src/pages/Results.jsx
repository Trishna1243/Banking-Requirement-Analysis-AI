import React from "react";
import { useNavigate } from "react-router-dom";

import Layout from "../components/Layout";
import RequirementCard from "../components/RequirementCard";
import { useAnalysis } from "../context/AnalysisContext";
import {
  getAmbiguityItems,
  getMissingItems,
  getRequirements,
} from "../utils/analysisStorage";

function Results() {
  const navigate = useNavigate();
  const { analysis: data } = useAnalysis();

  if (!data) {
    return (
      <Layout>
        <header>
          <div>
            <label>ANALYSIS RESULTS</label>

            <h1>
              No Analysis Available
            </h1>

            <p>
              Upload a document from the Analyze page
              to generate results.
            </p>
          </div>
        </header>

        <section>
          <button
            onClick={() => {
              navigate("/analyze");
            }}
          >
            ← Start New Analysis
          </button>
        </section>
      </Layout>
    );
  }

  const requirements = getRequirements(data);

  const highPriorityCount = requirements.filter(
    (item) =>
      String(
        item.analysis?.priority || ""
      ).toLowerCase() === "high"
  ).length;

  const missingItems = getMissingItems(requirements);
  const ambiguityItems = getAmbiguityItems(requirements);
  const missingCount = missingItems.length;
  const ambiguityCount = ambiguityItems.length;
  const sdlcRecommendation = data.sdlc_recommendation;
  const sdlcFailed = data.sdlc_status === "failed";
  const supportingFactorLabels = [
    ["requirement_characteristics", "Requirement characteristics"],
    ["risk_and_compliance", "Risk and compliance"],
    ["project_complexity", "Project complexity"],
    ["development_and_validation", "Development and validation"],
  ];

  return (
    <Layout>
      <header>
        <div>
          <label>
            ANALYSIS RESULTS
          </label>

          <h1>
            Requirement Analysis
          </h1>

          <p>
            {data.filename}
          </p>
        </div>

        <span
          className={sdlcRecommendation ? "done" : undefined}
          style={
            sdlcRecommendation
              ? undefined
              : { background: "#fffaeb", color: "#b54708", padding: "8px 12px", borderRadius: "20px", fontSize: "11px", fontWeight: 800 }
          }
        >
          {sdlcRecommendation
            ? "Analysis Complete"
            : sdlcFailed
              ? "Requirements Complete · SDLC Failed"
              : "Reanalysis Required"}
        </span>
      </header>

      <div className="stats compact">
        <div>
          Extracted

          <strong>
            {requirements.length}
          </strong>
        </div>

        <div>
          High Priority

          <strong>
            {highPriorityCount}
          </strong>
        </div>

        <div>
          Missing

          <strong>
            {missingCount}
          </strong>
        </div>

        <div>
          Ambiguities

          <strong>
            {ambiguityCount}
          </strong>
        </div>
      </div>

      <section>
        <h2>
          Extracted Requirements
        </h2>

        {requirements.length === 0 ? (
          <p>
            No requirements were returned by the backend.
          </p>
        ) : (
          requirements.map((requirement) => (
            <RequirementCard
              key={requirement.requirement_id}
              requirement={{
                id: requirement.requirement_id,
                priority:
                  requirement.analysis?.priority ||
                  "Not specified",
                category:
                  requirement.analysis?.category ||
                  "Not specified",
                sdlc:
                  requirement.analysis?.sdlc_stage ||
                  requirement.analysis?.sdlc ||
                  requirement.analysis?.type ||
                  "Not specified",
                text:
                  requirement.requirement_statement ||
                  "",
                page:
                  requirement.source_page,
                sourceLocation:
                  requirement.source_location,
                sourceEvidence:
                  requirement.source_evidence,
                retrievedSources:
                  requirement.retrieved_sources,
                analysis:
                  requirement.analysis || {},
              }}
            />
          ))
        )}
      </section>

      <div className="two">
        <section>
          <h2>
            Missing Information
          </h2>

          {data.missing_information_status === "unverified" && (
            <>
              <p role="status">
                Document-wide validation did not complete. Any questions below
                are unverified model candidates, not confirmed omissions.
              </p>
              {data.missing_information_error && (
                <p role="alert">
                  Validation error: {data.missing_information_error}
                </p>
              )}
            </>
          )}

          {missingCount === 0 ? (
            <p>
              {data.missing_information_status === "unverified"
                ? "No candidate questions were returned."
                : "No missing-information items were returned by the model."}
            </p>
          ) : (
            <ul>
              {missingItems.map((item, index) => (
                <li key={`${item}-${index}`}>
                  {item}
                </li>
              ))}
            </ul>
          )}
        </section>

      </div>

      <section>
        <h2>Overall SDLC Identification</h2>

        {!sdlcRecommendation ? (
          <>
            {sdlcFailed ? (
              <p role="alert">
                Overall SDLC identification failed after the requirement
                analyses completed:{" "}
                {data.sdlc_error || "No error details were returned."}
              </p>
            ) : (
              <p>
                This saved analysis does not contain the required overall SDLC
                recommendation. It may have been created before the current
                response format was added. Re-run the document analysis to
                generate and save the project-level recommendation.
              </p>
            )}
            <button onClick={() => navigate("/analyze")}>
              {sdlcFailed ? "Retry analysis" : "Re-analyze document"}
            </button>
          </>
        ) : (
          <>
            <p>
              <b>Recommended SDLC Model:</b>{" "}
              {sdlcRecommendation.recommended_model ||
                "No confident recommendation"}
            </p>

            <p>
              <b>Reasoning:</b>{" "}
              {sdlcRecommendation.reasoning ||
                "No reasoning was returned by the model."}
            </p>

            <h3>Supporting Factors</h3>
            <ul>
              {supportingFactorLabels.map(([key, label]) => (
                <li key={key}>
                  <b>{label}:</b>{" "}
                  {sdlcRecommendation.supporting_factors?.[key] ||
                    "Not established by the uploaded document."}
                </li>
              ))}
            </ul>

            {Array.isArray(sdlcRecommendation.evidence_limitations) &&
              sdlcRecommendation.evidence_limitations.length > 0 && (
                <>
                  <h3>Evidence Limitations</h3>
                  <ul>
                    {sdlcRecommendation.evidence_limitations.map(
                      (limitation, index) => (
                        <li key={`${limitation}-${index}`}>{limitation}</li>
                      )
                    )}
                  </ul>
                </>
              )}
          </>
        )}
      </section>
    </Layout>
  );
}

export default Results;
