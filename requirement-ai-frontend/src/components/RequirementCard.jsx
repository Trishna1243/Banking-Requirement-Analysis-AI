import React from "react";
import { normalizeQuestionList } from "../utils/analysisStorage";

function RequirementCard({ requirement }) {
  const normalizedPriority = String(requirement.priority || "").trim().toLowerCase();
  const missingInformation = normalizeQuestionList(
    requirement.analysis?.missing_information
  );
  const missingInformationDetails = Array.isArray(
    requirement.analysis?.missing_information_details
  )
    ? requirement.analysis.missing_information_details
    : [];
  const suggestedQuestions = normalizeQuestionList(
    requirement.analysis?.suggested_questions
  );
  const retrievedSources = Array.isArray(requirement.retrievedSources)
    ? requirement.retrievedSources
    : [];
  const priorityClass =
    normalizedPriority === "high"
      ? "high"
      : normalizedPriority === "medium"
        ? "medium"
        : "";

  return (
    <div className="req">
      <div>
        <b>
          {requirement.id}
        </b>

        <span className={priorityClass}>
          {requirement.priority}
        </span>
      </div>

      <p>
        <b>Extracted requirement:</b> {requirement.text}
      </p>

      <small>
        Model analysis — Type: {requirement.analysis?.requirement_type || "Not specified"}
        {" · "}Category: {requirement.category}
        {" · "}Priority: {requirement.priority}
        {" · "}SDLC phase: {requirement.sdlc}
        {requirement.page != null && (
          <>
            {" · "}
            Source page: {requirement.page}
          </>
        )}
        {requirement.sourceLocation && (
          <>
            {" · "}
            Source location: {requirement.sourceLocation}
          </>
        )}
      </small>

      {requirement.sourceEvidence && (
        <p>
          <b>Extracted source evidence:</b> {requirement.sourceEvidence}
        </p>
      )}

      {requirement.analysis?.ambiguity && (
        <p>
          <b>Ambiguity:</b> {asList(requirement.analysis.ambiguity).join("; ")}
        </p>
      )}

      {missingInformationDetails.length > 0 ? (
        <div>
          <b>Missing-information findings:</b>
          <ul>
            {missingInformationDetails.map((gap, index) => (
              <li key={`${gap.question}-${index}`}>
                <b>{gap.category}:</b> {gap.information}
                <p><b>Why it matters:</b> {gap.why_it_matters}</p>
                <p>
                  <b>Evidence checked:</b>{" "}
                  {Array.isArray(gap.evidence_checked)
                    ? gap.evidence_checked.join(" ")
                    : gap.evidence_checked}
                </p>
                <p><b>Clarification question:</b> {gap.question}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : missingInformation.length > 0 ? (
        <div>
          <b>Missing information:</b>
          <ul>{missingInformation.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </div>
      ) : null}

      {suggestedQuestions.length > 0 && (
        <div>
          <b>Suggested questions:</b>
          <ul>{suggestedQuestions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </div>
      )}

      {requirement.analysis?.sdlc_reasoning && (
        <p>
          <b>SDLC reasoning:</b> {requirement.analysis.sdlc_reasoning}
        </p>
      )}

      {requirement.analysis?.priority_reasoning && (
        <p>
          <b>Priority reasoning:</b> {requirement.analysis.priority_reasoning}
        </p>
      )}

      {retrievedSources.length > 0 && (
        <details>
          <summary>Retrieved document evidence ({retrievedSources.length})</summary>
          {retrievedSources.map((source) => (
            <p key={source.chunk_id}>
              <small>
                {source.source_document}
                {source.source_page != null
                  ? ` · Page ${source.source_page}`
                  : source.source_location
                    ? ` · ${source.source_location}`
                    : ""}
              </small>
              <br />
              {source.text}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}

function asList(value) {
  if (Array.isArray(value)) return value.filter(Boolean).map(String);
  return value ? [String(value)] : [];
}

export default RequirementCard;
