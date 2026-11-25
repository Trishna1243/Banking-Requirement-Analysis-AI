import React from "react";
import { useNavigate } from "react-router-dom";

import Layout from "../components/Layout";
import { useAnalysis } from "../context/AnalysisContext";
import {
  getAnalysisMetrics,
  getAmbiguityItems,
  getRequirements,
} from "../utils/analysisStorage";

function Dashboard() {

  const navigate = useNavigate();
  const { analysis } = useAnalysis();
  const requirements = getRequirements(analysis);
  const metrics = getAnalysisMetrics(analysis);
  const ambiguityItems = getAmbiguityItems(requirements);
  const hasAnalysis = Boolean(analysis);

  return (
    <Layout>

      <header>

        <div>

          <label>
            AI REQUIREMENT ENGINEERING
          </label>

          <h1>
            Requirement Analysis Dashboard
          </h1>

          <p>
            Extract, analyze and organize software
            requirements from financial-sector documents.
          </p>

        </div>

        <button
          onClick={() => navigate("/analyze")}
        >
          + New Analysis
        </button>

      </header>


      <div className="stats">

        <div>
          Requirements

          <strong>
            {hasAnalysis ? metrics.requirementCount : 0}
          </strong>

          <small>
            {hasAnalysis ? "Latest analysis" : "No analysis yet"}
          </small>

        </div>


        <div>
          Missing Information

          <strong>
            {hasAnalysis ? metrics.missingInformationCount : 0}
          </strong>

          <small>
            {hasAnalysis ? "Needs clarification" : "No analysis yet"}
          </small>

        </div>


        <div>
          High Priority

          <strong>
            {hasAnalysis ? metrics.highPriorityCount : 0}
          </strong>

          <small>
            {hasAnalysis ? "Requires attention" : "No analysis yet"}
          </small>

        </div>


        <div>
          SDLC Phases

          <strong>
            {hasAnalysis ? metrics.sdlcPhaseCount : 0}
          </strong>

          <small>
            {hasAnalysis ? "Identified" : "No analysis yet"}
          </small>

        </div>

      </div>


      <section className="hero">

        <div>

          <label>
            START HERE
          </label>

          <h2>
            Turn unstructured documents
            into structured requirements.
          </h2>

          <p>
            Upload a requirement document and review
            extracted requirements, missing information
            and SDLC identification.
          </p>

          <button
            onClick={() => navigate("/analyze")}
          >
            Analyze a Document →
          </button>

        </div>


        <div className="pipeline">

          <span>
            01 · Document
          </span>

          <span>
            02 · Requirements
          </span>

          <span>
            03 · Analysis
          </span>

          <span>
            04 · SDLC
          </span>

        </div>

      </section>


      <section>

        <h2>
          Recent Analysis
        </h2>

        {hasAnalysis ? (
          <>
            <p>{analysis.filename || "Uploaded document"}</p>
            <small>
              {metrics.requirementCount} requirements · {metrics.missingInformationCount} missing information items ·
              {" "}Completed
            </small>
            {ambiguityItems.length > 0 && (
              <small>
                {" "}<br />{ambiguityItems.length} ambiguities identified
              </small>
            )}
          </>
        ) : (
          <>
            <p>No analysis available</p>
            <small>Upload a PDF to generate real results.</small>
          </>
        )}

      </section>

    </Layout>
  );
}

export default Dashboard;