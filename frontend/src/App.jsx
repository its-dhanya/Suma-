import React, { useState, useEffect } from "react";
import SessionControls from "./components/SessionControls";
import TranscriptView from "./components/TranscriptView";
import SummaryCard from "./components/SummaryCard";
import { jsPDF } from "jspdf";
import myBackground from "/image.png"; // Background image

// Define SYSTEM_PROMPT for summarization requests
const SYSTEM_PROMPT = "Provide a concise and comprehensive summary of the lecture content.";

// Simple spinner component
function Spinner() {
  return (
    <div
      className="spinner"
      style={{
        border: "4px solid #f3f3f3",
        borderTop: "4px solid #3498db",
        borderRadius: "50%",
        width: "18px",
        height: "18px",
        animation: "spin 2s linear infinite"
      }}
    >
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );
}

// Component for inserting a YouTube video link
function VideoUploadControls({ setTranscript }) {
  const [youtubeURL, setYoutubeURL] = useState("");
  const [loadingUpload, setLoadingUpload] = useState(false);

  const handleUpload = async () => {
    if (!youtubeURL) return;
    setLoadingUpload(true);
    try {
      // Call the backend API to fetch a transcript based on the YouTube URL.
      const res = await fetch(
        `http://localhost:8000/youtube-transcript?videoURL=${encodeURIComponent(youtubeURL)}`
      );
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setTranscript(data.transcript);
    } catch (error) {
      console.error("Error uploading YouTube video:", error);
    } finally {
      setLoadingUpload(false);
    }
  };

  return (
    <div className="my-6 p-4 border rounded shadow-sm transition transform hover:scale-105 hover:shadow-xl">
      <h3 className="text-xl font-semibold mb-2">Insert a YouTube Video Link</h3>
      <input
        type="text"
        value={youtubeURL}
        onChange={(e) => setYoutubeURL(e.target.value)}
        placeholder="Enter YouTube video URL"
        className="border rounded p-2 w-full mb-4 focus:outline-none focus:ring-2 focus:ring-blue-600"
      />
      <button
        onClick={handleUpload}
        disabled={loadingUpload}
        className={`px-4 py-2 rounded font-semibold transition duration-300 ${
          loadingUpload
            ? "bg-blue-200 text-gray-500 cursor-not-allowed"
            : "bg-blue-600 text-white hover:bg-blue-700"
        }`}
      >
        {loadingUpload ? (
          <>
            <Spinner /> Uploading...
          </>
        ) : (
          "Submit YouTube Link"
        )}
      </button>
    </div>
  );
}

// Main App Component
function App() {
  const [sessionFolder, setSessionFolder] = useState("");
  const [transcript, setTranscript] = useState("");
  const [summary, setSummary] = useState(null);
  const [jobId, setJobId] = useState(null);
  // Tabs: "home", "video", "transcript", "summary"
  const [activeTab, setActiveTab] = useState("home");
  const [loading, setLoading] = useState({
    session: false,
    transcribe: false,
    summarize: false
  });
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    console.log("Updated summary:", summary);
  }, [summary]);

  const startSession = async () => {
    console.log("Starting session...");
    setLoading((prev) => ({ ...prev, session: true }));
    setIsRecording(true);
    try {
      const res = await fetch("http://localhost:8000/start-session", {
        method: "POST"
      });
      const data = await res.json();
      console.log("Session started:", data);
      setSessionFolder(data.session_folder);
    } catch (error) {
      console.error("Error starting session:", error);
    } finally {
      setLoading((prev) => ({ ...prev, session: false }));
    }
  };

  const stopSession = async () => {
    console.log("Stopping session...");
    try {
      await fetch("http://localhost:8000/stop-session", { method: "POST" });
      setIsRecording(false);
      console.log("Stop signal sent.");
    } catch (error) {
      console.error("Error stopping session:", error);
    }
  };

  const doTranscribe = async () => {
    console.log("Starting transcription...");
    setLoading((prev) => ({ ...prev, transcribe: true }));
    try {
      const res = await fetch("http://localhost:8000/transcribe", {
        method: "POST"
      });
      const data = await res.json();
      console.log("Transcription successful:", data);
      setTranscript(data.transcript);
    } catch (error) {
      console.error("Error transcribing:", error);
    } finally {
      setLoading((prev) => ({ ...prev, transcribe: false }));
    }
  };

  // Summarization process in Summary tab
  const startSummarization = async () => {
    console.log("Starting summarization job...");
    setLoading((prev) => ({ ...prev, summarize: true }));
    try {
      const res = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_prompt: SYSTEM_PROMPT })
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      console.log("Summarization job enqueued:", data);
      setJobId(data.jobId);
    } catch (error) {
      console.error("Error enqueuing summarization job:", error);
      setLoading((prev) => ({ ...prev, summarize: false }));
    }
  };

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/summary/${jobId}`);
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        console.log("Polling summary job:", data);
        if (data.status === "done" || data.status === "error") {
          if (data.status === "done") {
            setSummary(data.result);
          } else {
            console.error("Summarization job failed:", data.result);
          }
          setJobId(null);
          setLoading((prev) => ({ ...prev, summarize: false }));
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Error polling summary job:", error);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [jobId]);

  // Export PDF with professional and colorful styling.
  // If summary.raw exists, it prints the raw summary (no changes to the json summary).
  // Otherwise, it flattens the JSON into an ordered list of sections.
  const exportPDF = async () => {
    if (!summary) return;

    // If a raw summary is provided, use it directly.
    if (summary.raw) {
      const doc = new jsPDF({ unit: "pt", format: "letter" });
      const pageWidth  = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const margin     = 40;
      let y = margin;

      // Title
      doc.setFont("helvetica", "bold");
      doc.setFontSize(30);
      doc.setTextColor(30, 30, 60);
      doc.text("Lecture Summary", pageWidth/2, y, { align: "center" });
      y += 30;

      // Subtitle with a thin line below
      doc.setFontSize(14);
      doc.setTextColor(100);
      doc.text("Generated by Suma", pageWidth/2, y, { align: "center" });
      y += 20;
      doc.setDrawColor(200);
      doc.setLineWidth(0.5);
      doc.line(margin, y, pageWidth - margin, y);
      y += 20;

      // Raw summary content
      doc.setFont("times", "normal");
      doc.setFontSize(12);
      doc.setTextColor(30, 30, 30);
      const lines = doc.splitTextToSize(summary.raw, pageWidth - margin * 2);
      lines.forEach((line) => {
        if (y > pageHeight - margin) {
          doc.addPage();
          y = margin;
        }
        doc.text(line, margin, y);
        y += 16;
      });

      // Footer page numbering
      const pageCount = doc.internal.getNumberOfPages();
      doc.setFont("helvetica", "italic");
      doc.setFontSize(10);
      doc.setTextColor(150);
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.text(
          `Page ${i} of ${pageCount}`,
          pageWidth - margin,
          pageHeight - 20,
          { align: "right" }
        );
      }
      doc.save("Lecture_Summary_Suma.pdf");
      return;
    }

    // Otherwise, flatten the JSON into an ordered list of sections.
    const sections = [
      { key: "overview", title: "Overview", content: summary.overview },
      { key: "core_concepts", title: "Core Concepts", content: summary.core_concepts.join("\n") },
      { key: "detailed_explanation", title: "Detailed Explanation", content: summary.detailed_explanation },
      { key: "examples", title: "Examples", content: summary.examples },
      { key: "takeaways", title: "Key Takeaways", content: summary.takeaways.map(t => `• ${t}`).join("\n") },
      {
        key: "questions",
        title: "Revision Questions",
        content: summary.questions
          .map((q, i) => `${i + 1}. Q: ${q.question}\n   A: ${q.answer}`)
          .join("\n\n")
      },
      {
        key: "resources",
        title: "Resources",
        content: summary.resources
          .map((r, i) => `${i + 1}. ${r.title} (${r.type})\n   ${r.url}`)
          .join("\n\n")
      }
    ];

    const doc = new jsPDF({ unit: "pt", format: "letter" });
    const pageWidth  = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin     = 40;
    let y = margin;

    // Title
    doc.setFont("helvetica", "bold");
    doc.setFontSize(30);
    doc.setTextColor(30, 30, 60);
    doc.text("Lecture Summary", pageWidth/2, y, { align: "center" });
    y += 30;

    // Subtitle with a thin line below
    doc.setFontSize(14);
    doc.setTextColor(100);
    doc.text("Generated by Suma", pageWidth/2, y, { align: "center" });
    y += 20;
    doc.setDrawColor(200);
    doc.setLineWidth(0.5);
    doc.line(margin, y, pageWidth - margin, y);
    y += 20;

    // Section loop
    sections.forEach((sec, idx) => {
      // New page if needed
      if (y > pageHeight - margin - 100) {
        doc.addPage();
        y = margin;
      }

      // Section header background band (light blue)
      const bandHeight = 24;
      doc.setFillColor(225, 240, 255);
      doc.rect(margin, y - bandHeight + 4, pageWidth - margin * 2, bandHeight, "F");

      // Section header text
      doc.setFont("helvetica", "bold");
      doc.setFontSize(18);
      doc.setTextColor(30, 80, 160);
      doc.text(sec.title, margin + 4, y);
      y += 28;

      // Section content
      doc.setFont("times", "normal");
      doc.setFontSize(12);
      doc.setTextColor(30, 30, 30);
      const lines = doc.splitTextToSize(sec.content, pageWidth - margin * 2);
      lines.forEach((line) => {
        if (y > pageHeight - margin) {
          doc.addPage();
          y = margin;
        }
        doc.text(line, margin, y);
        y += 16;
      });
      y += 16; // extra spacing after section
    });

    // Footer page numbering
    const pageCount = doc.internal.getNumberOfPages();
    doc.setFont("helvetica", "italic");
    doc.setFontSize(10);
    doc.setTextColor(150);
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.text(
        `Page ${i} of ${pageCount}`,
        pageWidth - margin,
        pageHeight - 20,
        { align: "right" }
      );
    }

    // 3) Save PDF
    doc.save("Lecture_Summary_Suma.pdf");
  };

  return (
    <div className="min-h-screen text-gray-900 flex flex-col items-center justify-start p-10 relative overflow-hidden">
      {/* Background image */}
      <div
        className="absolute top-0 left-0 w-full h-full"
        style={{
          backgroundImage: `url(${myBackground})`,
          backgroundRepeat: "repeat",
          backgroundSize: "300px 300px",
          zIndex: -1,
          opacity: 0.4,
          animation: "movebg 40s linear infinite"
        }}
      />
      {/* Navigation */}
      <nav className="w-full max-w-5xl mb-6">
        <ul className="flex justify-around bg-white/90 backdrop-blur-md rounded-full p-3 shadow-md">
          <li>
            <button
              onClick={() => setActiveTab("home")}
              className={`px-4 py-2 font-semibold rounded-full transition duration-300 ${
                activeTab === "home" ? "bg-blue-600 text-white" : "text-gray-800 hover:bg-blue-100"
              }`}
            >
              Home
            </button>
          </li>
          <li>
            <button
              onClick={() => setActiveTab("video")}
              className={`px-4 py-2 font-semibold rounded-full transition duration-300 ${
                activeTab === "video" ? "bg-indigo-600 text-white" : "text-gray-800 hover:bg-indigo-100"
              }`}
            >
              Video
            </button>
          </li>
          <li>
            <button
              onClick={() => setActiveTab("transcript")}
              className={`px-4 py-2 font-semibold rounded-full transition duration-300 ${
                activeTab === "transcript" ? "bg-green-600 text-white" : "text-gray-800 hover:bg-green-100"
              }`}
            >
              Transcript
            </button>
          </li>
          <li>
            <button
              onClick={() => setActiveTab("summary")}
              className={`px-4 py-2 font-semibold rounded-full transition duration-300 ${
                activeTab === "summary" ? "bg-purple-600 text-white" : "text-gray-800 hover:bg-purple-100"
              }`}
            >
              Summary
            </button>
          </li>
        </ul>
      </nav>
      <div className="w-full max-w-5xl bg-white/90 backdrop-blur-lg rounded-3xl shadow-2xl border border-gray-300 p-10 space-y-8">
        {/* Header section */}
        <div className="bg-gradient-to-r from-blue-800 to-indigo-800 rounded-3xl p-16 text-center shadow-2xl transition-transform">
          <h1 className="text-9xl font-extrabold text-white drop-shadow-xl animate-pulse">
            Suma
          </h1>
          <p className="mt-6 text-4xl text-gray-200 italic tracking-wide">
            Your Smart Note-Taking Assistant
          </p>
        </div>
        {activeTab === "home" && (
          <div className="text-center space-y-6">
            <h2 className="text-5xl font-bold">Welcome to Suma</h2>
            <p className="text-xl text-gray-700 max-w-3xl mx-auto">
              Suma is designed to transform the way you capture and review important information from lectures and meetings. Leveraging advanced AI, Suma makes note-taking effortless.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-8">
              <div className="group p-6 border rounded-xl shadow-lg transition transform hover:scale-105 hover:shadow-2xl hover:bg-gradient-to-r hover:from-blue-800 hover:to-indigo-800">
                <h3 className="text-2xl font-bold mb-2 group-hover:text-white">
                  Record & Upload
                </h3>
                <p className="text-gray-600 group-hover:text-white">
                  Record your lectures or upload a YouTube video to instantly convert audio to text.
                </p>
              </div>
              <div className="group p-6 border rounded-xl shadow-lg transition transform hover:scale-105 hover:shadow-2xl hover:bg-gradient-to-r hover:from-blue-800 hover:to-indigo-800">
                <h3 className="text-2xl font-bold mb-2 group-hover:text-white">
                  Transcription
                </h3>
                <p className="text-gray-600 group-hover:text-white">
                  View detailed transcripts of your recordings with high accuracy.
                </p>
              </div>
              <div className="group p-6 border rounded-xl shadow-lg transition transform hover:scale-105 hover:shadow-2xl hover:bg-gradient-to-r hover:from-blue-800 hover:to-indigo-800">
                <h3 className="text-2xl font-bold mb-2 group-hover:text-white">
                  Summarization
                </h3>
                <p className="text-gray-600 group-hover:text-white">
                  Generate concise summaries with actionable insights and resource recommendations.
                </p>
              </div>
            </div>
            <p className="text-lg text-gray-600 mt-8">
              Navigate through the tabs above to start recording, view transcripts, and generate summaries.
            </p>
          </div>
        )}
        {activeTab === "video" && (
          <div className="space-y-6">
            <SessionControls
              onStart={startSession}
              onStop={stopSession}
              loading={loading.session}
              isRecording={isRecording}
              sessionFolder={sessionFolder}
            />
            <VideoUploadControls setTranscript={setTranscript} />
          </div>
        )}
        {activeTab === "transcript" && (
          <div className="space-y-6">
            <div className="flex justify-center">
              <button
                onClick={doTranscribe}
                disabled={loading.transcribe}
                className={`mt-6 px-6 py-3 rounded-lg font-semibold shadow-lg transition duration-300 ease-in-out ${
                  loading.transcribe
                    ? "bg-blue-200 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {loading.transcribe ? (
                  <>
                    <Spinner /> Transcribing…
                  </>
                ) : (
                  "Transcribe Audio"
                )}
              </button>
            </div>
            <TranscriptView transcript={transcript} />
          </div>
        )}
        {activeTab === "summary" && (
          <div className="space-y-6">
            <div className="flex justify-center gap-6">
              <button
                onClick={startSummarization}
                disabled={loading.summarize}
                className={`mt-4 px-6 py-3 rounded-lg font-semibold shadow-lg transition duration-300 ease-in-out ${
                  loading.summarize
                    ? "bg-green-200 text-gray-500 cursor-not-allowed"
                    : "bg-green-600 text-white hover:bg-green-700"
                }`}
              >
                {loading.summarize ? (
                  <>
                    <Spinner /> Summarizing…
                  </>
                ) : (
                  "Generate Summary"
                )}
              </button>
              {summary && (
                <button
                  onClick={exportPDF}
                  className="mt-4 px-6 py-3 rounded-lg font-semibold shadow-lg bg-purple-700 text-white hover:bg-purple-800 transition duration-300"
                >
                  Export as PDF
                </button>
              )}
            </div>
            {summary && <SummaryCard summary={summary} />}
          </div>
        )}
      </div>
      <style>
        {`
          @keyframes movebg {
            0% { background-position: 0% 100%; }
            100% { background-position: 0% 0%; }
          }
        `}
      </style>
    </div>
  );
}

export default App;