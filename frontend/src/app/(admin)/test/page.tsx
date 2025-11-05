"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export default function TestPage() {
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const testBackend = async () => {
    setLoading(true);
    setResult("Testing...\n");
    
    try {
      // Test 1: Backend alive
      setResult(prev => prev + "1. Testing backend...\n");
      const response = await fetch('https://mvp-ranksimulator-production.up.railway.app/');
      const data = await response.json();
      setResult(prev => prev + `✅ Backend alive: ${data.message}\n\n`);
      
      // Test 2: Check token
      const token = localStorage.getItem('token');
      setResult(prev => prev + `2. Token in localStorage: ${token ? 'YES' : 'NO'}\n`);
      if (token) {
        setResult(prev => prev + `   Token: ${token.substring(0, 20)}...\n\n`);
      }
      
      // Test 3: Check user
      const user = localStorage.getItem('user');
      setResult(prev => prev + `3. User in localStorage: ${user ? 'YES' : 'NO'}\n`);
      if (user) {
        setResult(prev => prev + `   User: ${JSON.parse(user).email}\n\n`);
      }
      
      // Test 4: Test login
      setResult(prev => prev + "4. Testing login...\n");
      try {
        const loginData = await api.login('ciccioragusa@gmail.com', '12345Aa!');
        setResult(prev => prev + `✅ Login successful: ${loginData.user.email}\n`);
        setResult(prev => prev + `   Token: ${loginData.access_token.substring(0, 20)}...\n\n`);
      } catch (err) {
        setResult(prev => prev + `❌ Login failed: ${err instanceof Error ? err.message : 'Unknown error'}\n\n`);
      }
      
      // Test 5: Test getUsers
      setResult(prev => prev + "5. Testing getUsers...\n");
      try {
        const usersData = await api.getUsers();
        setResult(prev => prev + `✅ Users loaded: ${usersData.users.length} users\n`);
        usersData.users.forEach((u: { email: string; role: string }) => {
          setResult(prev => prev + `   - ${u.email} (${u.role})\n`);
        });
      } catch (err) {
        setResult(prev => prev + `❌ getUsers failed: ${err instanceof Error ? err.message : 'Unknown error'}\n`);
      }
      
    } catch (err) {
      setResult(prev => prev + `\n❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}\n`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-3xl font-semibold text-gray-900 dark:text-white mb-6">
        API Test Page
      </h1>
      
      <button
        onClick={testBackend}
        disabled={loading}
        className="mb-4 rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Testing...' : 'Run Tests'}
      </button>
      
      {result && (
        <pre className="rounded-lg bg-gray-100 p-4 text-sm dark:bg-gray-800 whitespace-pre-wrap font-mono">
          {result}
        </pre>
      )}
    </div>
  );
}
