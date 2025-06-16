import React from "react";

function SummaryCard({ summary }) {
  if (!summary) return null;

  // When using a raw response, display it in a styled code block.
  if (summary.raw) {
    return (
      <div className="summary-card p-8 bg-white rounded-xl shadow-2xl border border-gray-300 font-sans">
        <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2 mb-6">
          Summary (Raw)
        </h2>
        <div className="bg-gray-800 text-gray-100 text-base p-6 rounded-md overflow-x-auto font-mono">
          <pre className="whitespace-pre-wrap">{summary.raw}</pre>
        </div>
      </div>
    );
  }

  // Helper to render different types of content.
  const renderContent = (content) => {
    if (Array.isArray(content)) {
      return content.map((item, index) => (
        <React.Fragment key={index}>
          {renderContent(item)}
          {index < content.length - 1 && <br />}
        </React.Fragment>
      ));
    } else if (content !== null && typeof content === "object") {
      // Check for question objects.
      if (
        Object.prototype.hasOwnProperty.call(content, "question") &&
        Object.prototype.hasOwnProperty.call(content, "answer")
      ) {
        return (
          <div className="qa-pair bg-gray-100 p-4 rounded-md my-3 border border-gray-400">
            <div>
              <span className="font-semibold text-blue-700">Q:</span>{" "}
              {renderContent(content.question)}
            </div>
            <div>
              <span className="font-semibold text-green-700">A:</span>{" "}
              {renderContent(content.answer)}
            </div>
          </div>
        );
      }
      return (
        <pre className="whitespace-pre-wrap text-sm text-gray-600 font-mono">
          {JSON.stringify(content, null, 2)}
        </pre>
      );
    }
    return content;
  };

  // Helper function to ensure properties are always arrays.
  const toArray = (prop) => {
    if (Array.isArray(prop)) return prop;
    if (prop !== undefined && prop !== null) return [prop];
    return [];
  };

  // Destructure summary ensuring that values are safely handled.
  const {
    overview,
    core_concepts,
    detailed_explanation,
    examples,
    takeaways,
    questions,
    resources,
  } = summary;

  return (
    <div className="summary-card p-8 bg-white rounded-xl shadow-2xl border border-gray-300 font-sans">
      {overview && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Overview
          </h2>
          <p className="mt-3 text-gray-800 text-lg leading-relaxed">{renderContent(overview)}</p>
        </div>
      )}
      {core_concepts && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Core Concepts
          </h2>
          <p className="mt-3 text-gray-800 text-lg leading-relaxed">{renderContent(core_concepts)}</p>
        </div>
      )}
      {detailed_explanation && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Detailed Explanation
          </h2>
          <p className="mt-3 text-gray-800 text-lg leading-relaxed">{renderContent(detailed_explanation)}</p>
        </div>
      )}
      {toArray(examples).length > 0 && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Examples
          </h2>
          <div className="mt-3 text-gray-800 text-lg leading-relaxed">
            {toArray(examples).map((ex, i) => (
              <p key={i}>{renderContent(ex)}</p>
            ))}
          </div>
        </div>
      )}
      {takeaways && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Key Takeaways
          </h2>
          <p className="mt-3 text-gray-800 text-lg leading-relaxed">{renderContent(takeaways)}</p>
        </div>
      )}
      {questions && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Follow-up Questions
          </h2>
          <div className="mt-3 text-gray-800 text-lg leading-relaxed">
            {toArray(questions).map((q, i) => (
              <p key={i} className="mb-2">
                {renderContent(q)}
              </p>
            ))}
          </div>
        </div>
      )}
      {toArray(resources).length > 0 && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">
            Resources
          </h2>
          <ul className="list-disc list-inside mt-3 text-gray-800 text-lg">
            {toArray(resources).map((r, i) => {
              const title = r.title ? renderContent(r.title) : "Untitled";
              const type = r.type ? renderContent(r.type) : "Unknown type";
              const url = r.url ? renderContent(r.url) : "No URL provided";
              return (
                <li key={i}>
                  <span className="text-blue-700 font-semibold">{title}</span>{" "}
                  <span className="text-gray-700">({type})</span> -{" "}
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-green-700 underline"
                  >
                    {url}
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

export default SummaryCard;