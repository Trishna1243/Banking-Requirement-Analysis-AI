import React from "react";
import { useNavigate } from "react-router-dom";

import Layout from "../components/Layout";
import RequirementCard from "../components/RequirementCard";
import { useAnalysis } from "../context/AnalysisContext";
import {
  getAmbiguityItems,
  getMissingItems,
  getRequirements,
  getSdlcStages,
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
  const sdlcStages = getSdlcStages(requirements);
  const missingCount = missingItems.length;
  const ambiguityCount = ambiguityItems.length;

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

        <span className="done">
          Analysis Complete
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

          {missingCount === 0 ? (
            <p>
              No missing-information items were returned
              by the model.
            </p>
          ) : (
            <ul>
              {requirements
                .flatMap((item) =>
                  Array.isArray(item.analysis?.missing_information)
                    ? item.analysis.missing_information
                    : item.analysis?.missing_information
                      ? [item.analysis.missing_information]
                      : []
                )
                .map((item, index) => (
                  <li key={`${item}-${index}`}>
                    {item}
                  </li>
                ))}
            </ul>
          )}
        </section>

        <section>
          <h2>
            SDLC Identification
          </h2>

          <ol>
            {[
              ...sdlcStages,
            ].map((stage) => (
              <li key={stage}>
                {stage}
              </li>
            ))}

            {sdlcStages.length === 0 && (
              <li>
                SDLC stage information was not returned
                by Model 1 V2.
              </li>
            )}
          </ol>
        </section>
      </div>
    </Layout>
  );
}

export default Results;
