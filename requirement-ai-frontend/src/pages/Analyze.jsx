import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import Layout from "../components/Layout";
import { useAnalysis } from "../context/AnalysisContext";
import { hasSdlcOutcome } from "../utils/analysisStorage";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

function Analyze() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();
  const { saveAnalysis } = useAnalysis();

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) {
      setFile(null);
      return;
    }

    if (!/\.(pdf|docx)$/i.test(selectedFile.name)) {
      setFile(null);
      setError("Please select a PDF or DOCX file.");
      return;
    }

    setFile(selectedFile);
    setError("");
  };

  const handleAnalyze = async () => {
    if (!file || loading) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/api/analyze-document`,
        {
          method: "POST",
          body: formData,
        }
      );

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          `Backend returned an invalid response (${response.status}).`
        );
      }

      if (
        !response.ok ||
        !data ||
        !data.success ||
        typeof data.filename !== "string" ||
        !Array.isArray(data.requirements) ||
        !hasSdlcOutcome(data)
      ) {
        throw new Error(
          (typeof data?.detail === "string" && data.detail) ||
            "Backend returned an incomplete analysis response."
        );
      }

      saveAnalysis(data);

      navigate("/results");
    } catch (err) {
      console.error("Document analysis error:", err);

      if (err instanceof TypeError && /failed to fetch/i.test(err.message)) {
        setError(
          `Could not connect to the backend at ${API_BASE_URL}. Check that FastAPI is running and that its /health endpoint responds.`
        );
      } else {
        setError(err.message || "Document analysis failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <header>
        <div>
          <label>NEW ANALYSIS</label>

          <h1>
            Analyze a Document
          </h1>

          <p>
            Upload a software requirement document
            to begin.
          </p>
        </div>
      </header>

      <div className="two">
        <section>
          <div className="drop">
            <div className="upload">
              ↑
            </div>

            <h2>
              Upload requirement document
            </h2>

            <p>
              PDF or DOCX
            </p>

            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              disabled={loading}
            />

            {file && (
              <p>
                <b>Selected:</b>{" "}
                {file.name}
              </p>
            )}
          </div>

          {error && (
            <p style={{ color: "#c01048" }}>
              {error}
            </p>
          )}

          <button
            disabled={!file || loading}
            onClick={handleAnalyze}
          >
            {loading
              ? "Analyzing..."
              : "Start Analysis →"}
          </button>
          {loading && (
            <p role="status">
              Requirements are analyzed sequentially before the project-level
              SDLC recommendation. This can take several minutes on a local
              GPU; keep this page open while analysis is running.
            </p>
          )}
        </section>

        <section>
          <label>
            WHAT HAPPENS NEXT
          </label>

          <h2>
            Analysis pipeline
          </h2>

          <ol>
            <li>
              Requirement Extraction
            </li>

            <li>
              Missing Information
            </li>

            <li>
              Requirement Analysis
            </li>

            <li>
              SDLC Identification
            </li>
          </ol>
        </section>
      </div>
    </Layout>
  );
}

export default Analyze;
