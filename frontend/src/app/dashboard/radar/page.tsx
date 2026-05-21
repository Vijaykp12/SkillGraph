"use client";

import { useEffect, useState } from "react";
import { getProfile, getGapAnalysis, getLearningRecommendations } from "@/lib/api";
import { Search, Compass, BookOpen, AlertCircle, ArrowRight, ShieldCheck } from "lucide-react";

export default function SkillGapRadarPage() {
  const [profile, setProfile] = useState<any>(null);
  const [targetOcc, setTargetOcc] = useState("");
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [gapData, setGapData] = useState<any>(null);
  const [courses, setCourses] = useState<any[]>([]);
  const [error, setError] = useState("");

  const loadData = async () => {
    try {
      const prof = await getProfile();
      setProfile(prof);
      if (prof.target_occupation) {
        setTargetOcc(prof.target_occupation);
        // Automatically run initial gap analysis
        await runAnalysis(prof.target_occupation, prof.parsed_skills);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async (target: string, currentSkills: string[]) => {
    setCalculating(true);
    setError("");
    try {
      const data = await getGapAnalysis(target, currentSkills);
      setGapData(data);
      
      // Load courses
      const courseData = await getLearningRecommendations(target, currentSkills);
      setCourses(courseData.recommendations || []);
    } catch (err: any) {
      setError(err.message || "Could not calculate gap metrics.");
      setGapData(null);
    } finally {
      setCalculating(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetOcc.trim() && profile) {
      runAnalysis(targetOcc.trim(), profile.parsed_skills);
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
        <h1 className="text-3xl font-bold tracking-tight text-white">AI Skill Gap Radar</h1>
        <p className="text-sm text-gray-400 mt-1">
          Compare your current skills against target occupation models and extract learning curriculums.
        </p>
      </div>

      {/* Target Search Form */}
      <div className="glass-card rounded-2xl p-6 border border-white/5">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-gray-400" />
            <input
              type="text"
              required
              placeholder="Query target occupation (e.g. Machine Learning Engineer)"
              value={targetOcc}
              onChange={(e) => setTargetOcc(e.target.value)}
              className="w-full pl-11 pr-4 py-3 rounded-xl glass-input text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={calculating}
            className="px-6 py-3 bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-700 hover:to-indigo-700 text-white font-medium text-sm rounded-xl shadow-neon transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {calculating ? "Analyzing..." : "Compare Gap"}
            <ArrowRight className="h-4.5 w-4.5" />
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-2">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {gapData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Match Score & Skills columns */}
          <div className="lg:col-span-2 space-y-6">
            {/* Summary Compatibility Score */}
            <div className="glass-card rounded-2xl p-6 border border-white/5 flex items-center justify-between bg-gradient-to-r from-primary-900/10 to-transparent">
              <div>
                <h3 className="text-sm font-semibold text-gray-400">Model Compatibility Match</h3>
                <p className="text-4xl font-extrabold text-white mt-1">{gapData.match_score}%</p>
                <p className="text-xs text-gray-400 mt-2">
                  Calculated using structural GNN adjacency weights and semantic vector projection.
                </p>
              </div>
              <div className="relative h-20 w-20 flex items-center justify-center">
                {/* Circular indicator */}
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  <path
                    className="text-white/5"
                    strokeWidth="3"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className="text-primary-500"
                    strokeDasharray={`${gapData.match_score}, 100`}
                    strokeWidth="3"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <span className="absolute text-xs font-bold text-white">{gapData.match_score}%</span>
              </div>
            </div>

            {/* Matching vs Missing Columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Matching */}
              <div className="glass-card rounded-2xl p-6 border border-white/5">
                <h3 className="text-sm font-bold text-emerald-400 mb-4 flex items-center gap-2">
                  <ShieldCheck className="h-4.5 w-4.5" />
                  Matching Skills ({gapData.matching_skills.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {gapData.matching_skills.length === 0 ? (
                    <span className="text-xs text-gray-400">No matching skills found.</span>
                  ) : (
                    gapData.matching_skills.map((s: any) => (
                      <span
                        key={s.id}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/15"
                      >
                        {s.name}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Missing */}
              <div className="glass-card rounded-2xl p-6 border border-white/5">
                <h3 className="text-sm font-bold text-primary-400 mb-4 flex items-center gap-2">
                  <AlertCircle className="h-4.5 w-4.5" />
                  Missing Skills ({gapData.missing_skills.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {gapData.missing_skills.length === 0 ? (
                    <span className="text-xs text-gray-400">Perfect match! No missing skills.</span>
                  ) : (
                    gapData.missing_skills.map((s: any) => (
                      <span
                        key={s.id}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-primary-500/10 text-primary-300 border border-primary-500/15"
                      >
                        {s.name}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Recommended Resources */}
          <div className="lg:col-span-1 glass-card rounded-2xl p-6 border border-white/5 flex flex-col">
            <h3 className="text-sm font-bold text-white mb-6 flex items-center gap-2 border-b border-white/5 pb-3">
              <BookOpen className="h-4.5 w-4.5 text-cyber-cyan" />
              Recommended Learning Roadmap
            </h3>

            <div className="flex-1 space-y-4">
              {courses.length === 0 ? (
                <p className="text-xs text-gray-400">No matching course recommendations found.</p>
              ) : (
                courses.map((course, idx) => (
                  <div key={idx} className="p-3 bg-white/5 rounded-xl border border-white/5 hover:border-white/10 transition-all">
                    <span className="inline-block px-2 py-0.5 rounded bg-primary-500/10 text-primary-300 text-[10px] font-bold mb-2">
                      Target: {course.skill_target}
                    </span>
                    <h4 className="text-xs font-bold text-white mb-1">{course.resource_name}</h4>
                    <div className="flex items-center justify-between text-[10px] text-gray-400 mt-2">
                      <span>Duration: {course.duration}</span>
                      <a href={course.url} target="_blank" rel="noreferrer" className="text-cyber-cyan hover:underline font-semibold flex items-center gap-0.5">
                        Enroll <ArrowRight className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
