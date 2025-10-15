"use client";

export default function DebugPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Debug Page</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Debug components have been removed for production.</p>
          <p className="text-sm text-gray-500 mt-2">This page is no longer needed.</p>
        </div>
      </div>
    </div>
  );
}
