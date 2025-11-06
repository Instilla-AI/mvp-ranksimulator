/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export default function AuditAIPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>(null);
  const [progress, setProgress] = useState("");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  const handleAnalyze = async () => {
    if (!url) {
      setError("Please enter a URL");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setProgress("Starting analysis...");

    try {
      // Start analysis
      const { job_id } = await api.startAnalysis(url);
      
      // Poll for results
      const pollStatus = async () => {
        try {
          const data = await api.checkStatus(job_id);
          
          // Update progress message
          if (data.progress) {
            setProgress(data.progress);
          }
          
          if (data.status === 'completed') {
            setResult(data.result);
            setProgress("Analysis completed!");
            setLoading(false);
          } else if (data.status === 'error') {
            setError(data.error || 'Analysis failed');
            setLoading(false);
          } else {
            // Poll again after 2 seconds
            setTimeout(pollStatus, 2000);
          }
        } catch {
          // Job not found or backend restarted
          setError('Analysis job lost. Backend may have restarted. Please try again.');
          setLoading(false);
        }
      };
      
      pollStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold text-gray-900 dark:text-white">
          AI Visibility Audit
        </h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Analyze how visible your content is in AI-powered search results
        </p>
      </div>

      {/* URL Input Card */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-900 dark:text-white">
            Enter URL to Analyze
          </label>
          <input
            type="url"
            placeholder="https://example.com/your-page"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-400"
          />
        </div>
        
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
        )}

        <button
          onClick={handleAnalyze}
          disabled={loading || !url}
          className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:cursor-not-allowed disabled:bg-gray-400 dark:bg-blue-500 dark:hover:bg-blue-600 dark:focus:ring-blue-800"
        >
          {loading ? (
            <>
              <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </>
          ) : (
            'Analyze URL'
          )}
        </button>

        {/* Progress Indicator */}
        {loading && progress && (
          <div className="mt-4 rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
            <div className="flex items-center">
              <svg className="mr-3 h-5 w-5 animate-spin text-blue-600 dark:text-blue-400" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                  {progress}
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  This may take 30-60 seconds...
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="mt-6 space-y-6">
          {/* Score Card */}
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
            <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-white">
              AI Visibility Score
            </h2>
            <div className="flex items-center justify-center">
              <div className="relative h-48 w-48">
                <svg className="h-full w-full -rotate-90 transform">
                  <circle
                    cx="96"
                    cy="96"
                    r="80"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    className="text-gray-200 dark:text-gray-700"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="80"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    strokeDasharray={`${2 * Math.PI * 80}`}
                    strokeDashoffset={`${2 * Math.PI * 80 * (1 - result.ai_visibility_score / 100)}`}
                    strokeLinecap="round"
                    className="text-blue-600 dark:text-blue-500"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-gray-900 dark:text-white">
                    {result.ai_visibility_score}%
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Visibility
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {result.coverage_details.covered_queries} of {result.coverage_details.total_queries} queries covered
              </p>
            </div>
          </div>

          {/* Generation Details */}
          {result.generation_details && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
              <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-white">
                Query Generation Details
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Routing Strategy
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {result.generation_details.routing_used || 'Standard routing'}
                  </p>
                </div>
                <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Reasoning Approach
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {result.generation_details.reasoning_used || 'Standard reasoning'}
                  </p>
                </div>
              </div>
              <div className="mt-4 rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  <strong>Coverage Threshold:</strong> Queries with similarity ≥ 65% are considered covered
                </p>
              </div>
            </div>
          )}

          {/* Query Details Table */}
          <div className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
            <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-800">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Query Analysis
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Query
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Routing
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Similarity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      Coverage
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {result.query_details?.map((query: any, index: number) => (
                    <>
                      <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                        <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => toggleRow(index)}
                              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                            >
                              <svg
                                className={`h-4 w-4 transition-transform ${expandedRows.has(index) ? 'rotate-90' : ''}`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </button>
                            <span>{query.query}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          {query.type}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-900/20 dark:text-purple-400">
                            {query.routing || 'N/A'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          {query.similarity !== undefined ? (
                            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              query.similarity >= 0.65
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                                : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
                            }`}>
                              {(query.similarity * 100).toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-gray-400">N/A</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                              query.covered
                                ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                                : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                            }`}
                          >
                            {query.covered ? '✓ Covered' : '✗ Not Covered'}
                          </span>
                        </td>
                      </tr>
                      {expandedRows.has(index) && (
                        <tr key={`${index}-details`} className="bg-gray-50 dark:bg-gray-800/30">
                          <td colSpan={5} className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                            <div className="space-y-3 text-sm">
                              <div>
                                <h4 className="font-semibold text-gray-900 dark:text-white mb-1">Reasoning:</h4>
                                <p className="text-gray-600 dark:text-gray-400">{query.reasoning || 'N/A'}</p>
                              </div>
                              {query.best_chunk && (
                                <div>
                                  <h4 className="font-semibold text-gray-900 dark:text-white mb-1">Best Matching Chunk:</h4>
                                  <p className="text-gray-600 dark:text-gray-400 italic">{query.best_chunk}</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
