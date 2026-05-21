"use client";

import { useEffect, useState } from "react";
import { getProfile } from "@/lib/api";
import { 
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip
} from "recharts";
import { Dna, ShieldAlert, BookOpen, Award } from "lucide-react";

export default function SkillDNAPage() {
  const [dna, setDna] = useState<any>(null);
  const [skillsCount, setSkillsCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await getProfile();
        setDna(data.skills_dna || {});
        setSkillsCount((data.parsed_skills || []).length);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
      </div>
    );
  }

  // Format data for Recharts Radar
  const radarData = dna ? Object.keys(dna).map(key => ({
    subject: key,
    score: dna[key],
    fullMark: 5.0
  })) : [];

  const topCategory = radarData.length > 0 
    ? [...radarData].sort((a, b) => b.score - a.score)[0]
    : null;

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Skill DNA Mapping</h1>
        <p className="text-sm text-gray-400 mt-1">
          Vectorized structural mapping of your workforce intelligence signature.
        </p>
      </div>

      {radarData.length === 0 || skillsCount === 0 ? (
        <div className="glass-card rounded-2xl p-8 border border-white/5 flex flex-col items-center justify-center text-center">
          <ShieldAlert className="h-10 w-10 text-amber-400 mb-3" />
          <h3 className="text-lg font-bold text-white">DNA Mapping Empty</h3>
          <p className="text-sm text-gray-400 mt-1 max-w-md">
            Go back to the Profile Overview, upload your resume or add your skills to generate your Skill DNA chart.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Radar Chart Visualizer */}
          <div className="lg:col-span-2 glass-card rounded-2xl p-6 border border-white/5 flex flex-col justify-center min-h-[400px]">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Dna className="h-5 w-5 text-primary-400 animate-pulse" />
              Structural Signature
            </h3>
            
            <div className="w-full h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="rgba(255, 255, 255, 0.08)" />
                  <PolarAngleAxis 
                    dataKey="subject" 
                    tick={{ fill: "#9ca3af", fontSize: 11, fontWeight: 600 }}
                  />
                  <PolarRadiusAxis 
                    angle={30} 
                    domain={[0, 5.0]} 
                    tick={{ fill: "#4b5563" }}
                  />
                  <Radar
                    name="Skill Strength"
                    dataKey="score"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.3}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "rgba(13, 13, 38, 0.95)",
                      border: "1px solid rgba(99, 102, 241, 0.3)",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "12px"
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Core Analytics Cards */}
          <div className="lg:col-span-1 space-y-6">
            {/* Top Domain Indicator */}
            {topCategory && (
              <div className="glass-card rounded-2xl p-6 border border-white/5 bg-gradient-to-br from-primary-900/20 to-indigo-900/10">
                <h3 className="text-sm font-semibold text-gray-400 mb-1">Dominant Career Domain</h3>
                <p className="text-2xl font-extrabold text-white flex items-center gap-2">
                  <Award className="h-6 w-6 text-cyber-cyan" />
                  {topCategory.subject}
                </p>
                <div className="mt-4 bg-white/5 border border-white/5 rounded-lg p-3">
                  <span className="text-xs text-gray-400">GNN Strength Rating</span>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-white/10 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-primary-500 to-cyber-cyan h-2 rounded-full"
                        style={{ width: `${(topCategory.score / 5) * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-xs font-bold text-cyber-cyan">{topCategory.score} / 5.0</span>
                  </div>
                </div>
              </div>
            )}

            {/* General Overview breakdown */}
            <div className="glass-card rounded-2xl p-6 border border-white/5 space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <BookOpen className="h-4.5 w-4.5 text-indigo-400" />
                Domain Strengths
              </h3>
              
              <div className="space-y-3">
                {radarData.map(item => (
                  <div key={item.subject}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-400">{item.subject}</span>
                      <span className="font-bold text-white">{item.score} / 5.0</span>
                    </div>
                    <div className="w-full bg-white/5 rounded-full h-1.5">
                      <div 
                        className="bg-primary-500 h-1.5 rounded-full"
                        style={{ width: `${(item.score / 5) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
