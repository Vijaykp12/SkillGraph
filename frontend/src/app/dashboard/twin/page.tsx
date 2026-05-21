"use client";

import { useEffect, useState } from "react";
import { getProfile, simulateTwin } from "@/lib/api";
import { Compass, Sparkles, AlertCircle, ArrowDown, Activity, ChevronRight } from "lucide-react";

export default function CareerTwinPage() {
  const [profile, setProfile] = useState<any>(null);
  const [startOcc, setStartOcc] = useState("");
  const [targetOcc, setTargetOcc] = useState("");
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [simData, setSimData] = useState<any>(null);
  const [error, setError] = useState("");

  const loadData = async () => {
    try {
      const prof = await getProfile();
      setProfile(prof);
      setStartOcc(prof.current_occupation || "");
      setTargetOcc(prof.target_occupation || "");
      
      // Auto run simulation if both set
      if (prof.current_occupation && prof.target_occupation) {
        await runSimulation(prof.current_occupation, prof.target_occupation);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async (start: string, target: string) => {
    setSimulating(true);
    setError("");
    try {
      const data = await simulateTwin(start, target);
      setSimData(data);
    } catch (err: any) {
      setError(err.message || "Failed to calculate transition simulator pathways.");
      setSimData(null);
    } finally {
      setSimulating(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (startOcc.trim() && targetOcc.trim()) {
      runSimulation(startOcc.trim(), targetOcc.trim());
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">AI Career Twin Simulator</h1>
        <p className="text-sm text-gray-400 mt-1">
          Predict multi-step career transitions and model transition velocity indicators using GNN link predictions.
        </p>
      </div>

      {/* Simulator Forms */}
      <div className="glass-card rounded-2xl p-6 border border-white/5">
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Starting Occupation</label>
            <input
              type="text"
              required
              placeholder="e.g. Frontend Engineer"
              value={startOcc}
              onChange={(e) => setStartOcc(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl glass-input text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Target Occupation</label>
            <input
              type="text"
              required
              placeholder="e.g. DevOps Engineer"
              value={targetOcc}
              onChange={(e) => setTargetOcc(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl glass-input text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={simulating}
            className="w-full py-3 bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-700 hover:to-indigo-700 text-white font-medium text-sm rounded-xl shadow-neon transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Compass className="h-4.5 w-4.5 animate-spin-slow" />
            {simulating ? "Simulating..." : "Simulate Twin Path"}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-2">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {simData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Transition sequence timeline */}
          <div className="lg:col-span-2 space-y-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary-400" />
              Transition Steps
            </h3>

            <div className="relative border-l border-white/10 pl-6 ml-4 space-y-8">
              {simData.path_sequence.map((step: any, idx: number) => (
                <div key={idx} className="relative">
                  {/* Timeline bullet dot */}
                  <span className="absolute -left-[31px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-500 ring-4 ring-background">
                    <span className="h-1.5 w-1.5 rounded-full bg-white"></span>
                  </span>

                  <div className="glass-card rounded-2xl p-6 border border-white/5 space-y-4 hover:border-white/10 transition-all">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        {step.from_occupation}
                        <ChevronRight className="h-4 w-4 text-gray-400" />
                        <span className="text-primary-400">{step.to_occupation}</span>
                      </h4>
                      <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 text-[10px] font-bold">
                        {step.gap_percentage}% Skill Gap
                      </span>
                    </div>

                    <div className="space-y-2">
                      <span className="text-[10px] font-semibold text-gray-400 block">Skills to Acquire:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {step.skills_to_learn.map((skill: string, sIdx: number) => (
                          <span
                            key={sIdx}
                            className="px-2 py-0.5 rounded bg-white/5 border border-white/5 text-gray-300 text-xs"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column - Momentum index */}
          <div className="lg:col-span-1 space-y-6">
            {/* Momentum Indicator card */}
            <div className="glass-card rounded-2xl p-6 border border-white/5 flex flex-col items-center justify-center text-center bg-gradient-to-br from-indigo-900/10 to-transparent">
              <Activity className="h-10 w-10 text-cyber-cyan mb-3 animate-pulse" />
              <h3 className="text-sm font-semibold text-gray-400">Career Momentum Score</h3>
              <p className="text-5xl font-extrabold text-white mt-2">{simData.momentum_score}%</p>
              
              <div className="w-full bg-white/5 rounded-full h-1.5 mt-6">
                <div 
                  className="bg-gradient-to-r from-primary-500 to-cyber-cyan h-1.5 rounded-full"
                  style={{ width: `${simData.momentum_score}%` }}
                ></div>
              </div>
              <p className="text-[10px] text-gray-400 mt-3 leading-relaxed">
                Calculated using cosine transition distance vectors and topological node connectivity. Higher values indicate lower barrier-to-entry transitions.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
