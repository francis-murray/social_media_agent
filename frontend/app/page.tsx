"use client";

import { useState } from "react";

interface Post {
  platform: string;
  content: string;
}

interface GenerateResponse {
  video_id: string;
  posts: Post[];
  transcript_preview: string;
}

export default function Home() {
  const [videoUrl, setVideoUrl] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["LinkedIn", "Instagram"]);
  const [language, setLanguage] = useState("en");
  const [generatedPosts, setGeneratedPosts] = useState<Post[]>([]);
  const [transcriptPreview, setTranscriptPreview] = useState("");
  const [progress, setProgress] = useState("");
  const [fullTranscript, setFullTranscript] = useState("");
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);
  const [isTranscriptLoading, setIsTranscriptLoading] = useState(false);
  const [transcriptError, setTranscriptError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const availablePlatforms = ["LinkedIn", "Instagram", "Twitter", "Facebook", "TikTok"];

  const handlePlatformToggle = (platform: string) => {
    setSelectedPlatforms(prev => 
      prev.includes(platform) 
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  const handleGenerate = async () => {
    if (!videoUrl.trim()) {
      setError("Please enter a YouTube video URL or ID");
      return;
    }

    if (selectedPlatforms.length === 0) {
      setError("Please select at least one platform");
      return;
    }

    setIsGenerating(true);
    setError("");
    setGeneratedPosts([]);
    setTranscriptPreview("");
    setProgress("Starting...");

    try {
      const params = new URLSearchParams();
      params.append("video_id", videoUrl.trim());
      selectedPlatforms.forEach((p) => params.append("platforms", p));
      params.append("language", language);

      const url = `http://localhost:8000/generate/stream?${params.toString()}`;

      const es = new EventSource(url);

      es.addEventListener("status", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.stage === "starting") setProgress("Starting...");
          if (data.stage === "transcript_ready") setProgress("Transcript ready");
          if (data.stage === "generating") setProgress(`Generating for ${data.platform}...`);
          if (data.stage === "done") setProgress("Done");
        } catch {}
      });

      es.addEventListener("transcript", (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          setTranscriptPreview(data.preview || "");
        } catch {}
      });

      es.addEventListener("post", (event: MessageEvent) => {
        try {
          const post = JSON.parse(event.data) as Post;
          setGeneratedPosts((prev) => [...prev, post]);
        } catch {}
      });

      es.addEventListener("error", (event: MessageEvent) => {
        try {
          const data = JSON.parse((event as any).data || "{}");
          setError(data.message || "An error occurred while streaming");
        } catch {
          setError("An error occurred while streaming");
        }
        es.close();
        setIsGenerating(false);
      });

      es.addEventListener("done", () => {
        es.close();
        setIsGenerating(false);
      });
    } catch (err) {
      console.error("Error starting stream:", err);
      setError(err instanceof Error ? err.message : "Failed to start stream. Please try again.");
      setIsGenerating(false);
    }
  };

  const handleCopy = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-4">
            Social Media Agent
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Generate engaging social media content from YouTube video transcripts using AI!
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 mb-8">
          {/* Video Information Section */}
          <div className="space-y-6">
            <h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-6">
              Video Information
            </h2>

            {/* YouTube URL Input */}
            <div>
              <label
                htmlFor="videoUrl"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                YouTube Video ID or URL
              </label>
              <input
                type="text"
                id="videoUrl"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="e.g., https://youtube.com/watch?v=dQw4w9WgXcQ or dQw4w9WgXcQ"
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white transition-all"
              />
            </div>

            {/* Platform Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Select Platforms
              </label>
              <div className="flex flex-wrap gap-3">
                {availablePlatforms.map((platform) => (
                  <button
                    key={platform}
                    type="button"
                    onClick={() => handlePlatformToggle(platform)}
                    className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      selectedPlatforms.includes(platform)
                        ? "bg-blue-600 text-white shadow-md"
                        : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
                    }`}
                  >
                    {platform}
                  </button>
                ))}
              </div>
            </div>

            {/* Language Selection */}
            <div>
              <label
                htmlFor="language"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Transcript Language
              </label>
              <select
                id="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white transition-all"
              >
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="pt">Portuguese</option>
                <option value="it">Italian</option>
                <option value="ja">Japanese</option>
                <option value="ko">Korean</option>
                <option value="zh">Chinese</option>
              </select>
            </div>

            {/* Transcript Preview */}
            {transcriptPreview && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-3">
                <p className="text-blue-700 dark:text-blue-300 text-sm">
                  <span className="font-semibold">Transcript preview:</span> {transcriptPreview}
                </p>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    disabled={isTranscriptLoading || !videoUrl}
                    onClick={async () => {
                      if (isTranscriptExpanded) {
                        setIsTranscriptExpanded(false);
                        return;
                      }
                      setTranscriptError("");
                      if (!fullTranscript) {
                        try {
                          setIsTranscriptLoading(true);
                          const params = new URLSearchParams();
                          params.append("video_id", videoUrl.trim());
                          params.append("language", language);
                          const resp = await fetch(`http://localhost:8000/transcript?${params.toString()}`);
                          if (!resp.ok) {
                              const e = await resp.json().catch(() => ({} as any));
                              throw new Error(e.detail || `HTTP ${resp.status}`);
                          }
                          const data = await resp.json();
                          setFullTranscript(data.transcript || "");
                        } catch (e) {
                          setTranscriptError(e instanceof Error ? e.message : "Failed to load transcript");
                          return;
                        } finally {
                          setIsTranscriptLoading(false);
                        }
                      }
                      setIsTranscriptExpanded(true);
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      isTranscriptExpanded
                        ? "bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600"
                        : "bg-blue-600 text-white hover:bg-blue-700"
                    } ${isTranscriptLoading ? "opacity-60 cursor-not-allowed" : ""}`}
                  >
                    {isTranscriptExpanded ? "Hide full transcript" : isTranscriptLoading ? "Loading transcript..." : "Show full transcript"}
                  </button>
                  {transcriptError && (
                    <span className="text-red-600 dark:text-red-400 text-sm">{transcriptError}</span>
                  )}
                </div>
                {isTranscriptExpanded && fullTranscript && (
                  <div className="bg-white dark:bg-gray-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 max-h-80 overflow-auto">
                    <p className="text-gray-800 dark:text-gray-100 text-sm whitespace-pre-wrap leading-relaxed">{fullTranscript}</p>
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-red-600 dark:text-red-400 text-sm flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  {error}
                </p>
              </div>
            )}

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={!videoUrl || isGenerating}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isGenerating ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  {progress || "Generating..."}
                </span>
              ) : (
                "Generate Content"
              )}
            </button>
          </div>
        </div>

        {/* Generated Content Section */}
        {generatedPosts.length > 0 && (
          <div className="space-y-6 animate-fadeIn">
            <h3 className="text-2xl font-semibold text-gray-800 dark:text-white">
              Generated Content
            </h3>
            {generatedPosts.map((post, index) => (
              <div
                key={index}
                className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8"
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-xl font-semibold text-gray-800 dark:text-white flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-blue-600"></span>
                    {post.platform}
                  </h4>
                  <button
                    onClick={() => handleCopy(post.content, index)}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-all duration-200"
                  >
                    {copiedIndex === index ? (
                      <>
                        <svg
                          className="w-5 h-5 text-green-500"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                        Copied!
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                          />
                        </svg>
                        Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
                  <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                    {post.content}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
