"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "../lib/api";
import { Sparkles, ArrowRight, ShieldCheck, Cpu } from "lucide-react";

export default function WelcomePage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        router.push("/dashboard");
      } else {
        await register(email, password, fullName);
        // Automate login after registration
        await login(email, password);
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Background glow filters */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-600/20 rounded-full blur-[100px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="w-full max-w-md z-10">
        {/* Glow Header */}
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="p-3 bg-primary-600/10 border border-primary-500/20 rounded-2xl mb-3 shadow-neon">
            <Cpu className="h-10 w-10 text-primary-500 animate-pulse" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary-500 via-purple-500 to-cyber-cyan">
            SkillGraph
          </h1>
          <p className="text-sm text-gray-400 mt-2">
            AI-Powered Heterogeneous Graph Intelligence
          </p>
        </div>

        {/* Form Card */}
        <div className="glass-card rounded-2xl p-8 shadow-2xl relative">
          <div className="flex border-b border-white/10 mb-6">
            <button
              className={`flex-1 pb-3 text-center text-sm font-semibold transition-all ${isLogin ? "text-primary-500 border-b-2 border-primary-500" : "text-gray-400 hover:text-white"
                }`}
              onClick={() => {
                setIsLogin(true);
                setError("");
              }}
            >
              Sign In
            </button>
            <button
              className={`flex-1 pb-3 text-center text-sm font-semibold transition-all ${!isLogin ? "text-primary-500 border-b-2 border-primary-500" : "text-gray-400 hover:text-white"
                }`}
              onClick={() => {
                setIsLogin(false);
                setError("");
              }}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Email Address</label>
              <input
                type="email"
                required
                placeholder="john@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Password</label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-lg bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-700 hover:to-indigo-700 text-white font-medium text-sm transition-all shadow-neon flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                "Authorizing..."
              ) : (
                <>
                  {isLogin ? "Access Dashboard" : "Create Account"}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </div>


      </div>
    </div>
  );
}
