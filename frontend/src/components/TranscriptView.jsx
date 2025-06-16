import React from "react";

export default function TranscriptView({ transcript }) {
  if (!transcript) return null;

  return (
    <div
      className="mt-6 bg-white p-6 rounded-lg shadow-xl border border-gray-300 w-full"
      style={{ fontFamily: "'Lato', sans-serif" }}
    >
      <h2
        className="text-2xl font-bold mb-4 border-b pb-2"
        style={{ color: "#34495E" }}
      >
        Transcript
      </h2>
      <div className="max-h-96 overflow-y-auto w-full">
        <div
          className="text-base whitespace-pre-wrap w-full"
          style={{ color: "#2C3E50", whiteSpace: "pre-wrap", wordBreak: "break-word" }}
        >
          {transcript}
        </div>
      </div>
    </div>
  );
}