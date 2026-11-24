import React from "react";

function RequirementCard({ requirement }) {
  const normalizedPriority = String(requirement.priority || "").trim().toLowerCase();
  const missingInformation = asList(requirement.analysis?.missing_information);
  const suggestedQuestions = asList(requirement.analysis?.suggested_questions);
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

      {missingInformation.length > 0 && (
        <div>
          <b>Missing information:</b>
          <ul>{missingInformation.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </div>
      )}

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
