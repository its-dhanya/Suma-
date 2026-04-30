import React from "react";

function SummaryCard({ summary }) {
  if (!summary) return null;

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

  const renderContent = (content) => {
    if (Array.isArray(content)) {
      return content.map((item, index) => (
        <div key={index}>{renderContent(item)}</div>
      ));
    }

    if (content !== null && typeof content === "object") {
      if ("question" in content && "answer" in content) {
        return (
          <div className="qa-pair bg-gray-100 p-4 rounded-md my-3 border border-gray-400">
            <div>
              <span className="font-semibold text-blue-700">Q:</span>{" "}
              {content.question}
            </div>
            <div>
              <span className="font-semibold text-green-700">A:</span>{" "}
              {content.answer}
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

    return <span>{content}</span>;
  };

  const toArray = (prop) => {
    if (Array.isArray(prop)) return prop;
    if (prop !== undefined && prop !== null) return [prop];
    return [];
  };

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
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Overview</h2>
          <div className="mt-3 text-gray-800 text-lg leading-relaxed">
            {renderContent(overview)}
          </div>
        </div>
      )}

      {core_concepts && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Core Concepts</h2>
          <ul className="list-disc list-inside mt-3 text-gray-800 text-lg">
            {toArray(core_concepts).map((c, i) => (
              <li key={i}>{renderContent(c)}</li>
            ))}
          </ul>
        </div>
      )}

      {detailed_explanation && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Detailed Explanation</h2>
          <div className="mt-3 text-gray-800 text-lg leading-relaxed">
            {renderContent(detailed_explanation)}
          </div>
        </div>
      )}

      {toArray(examples).length > 0 && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Examples</h2>
          <div className="mt-3 space-y-3">
            {toArray(examples).map((ex, i) => (
              <div key={i} className="p-4 bg-gray-100 rounded-lg border">
                {renderContent(ex)}
              </div>
            ))}
          </div>
        </div>
      )}

      {toArray(takeaways).length > 0 && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Key Takeaways</h2>
          <ul className="list-disc list-inside mt-3 text-gray-800 text-lg">
            {toArray(takeaways).map((t, i) => (
              <li key={i}>{renderContent(t)}</li>
            ))}
          </ul>
        </div>
      )}

      {toArray(questions).length > 0 && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Revision Q&amp;A</h2>
          <div className="mt-3">
            {toArray(questions).map((q, i) => (
              <div key={i}>{renderContent(q)}</div>
            ))}
          </div>
        </div>
      )}

      {toArray(resources).length > 0 && (
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-800 border-b pb-2">Resources</h2>
          <ul className="mt-3 space-y-2">
            {toArray(resources).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-base text-gray-800">
                {r.type && (
                  <span className="shrink-0 mt-0.5 text-xs font-bold uppercase bg-indigo-100 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-full">
                    {r.type}
                  </span>
                )}
                <div>
                  <span className="font-semibold text-blue-700">{r.title}</span>{" — "}
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-green-700 underline break-all"
                  >
                    {r.url}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

    </div>
  );
}

export default SummaryCard;