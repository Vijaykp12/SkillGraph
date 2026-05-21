"use client";

import { useEffect, useState } from "react";
import { getProfile, updateProfile, uploadResume } from "@/lib/api";
import { UploadCloud, FileText, CheckCircle, BrainCircuit, UserCheck } from "lucide-react";

export default function ProfileOverview() {
  const [profile, setProfile] = useState<any>(null);
  const [bio, setBio] = useState("");
  const [currentOcc, setCurrentOcc] = useState("");
  const [targetOcc, setTargetOcc] = useState("");
  const [newSkill, setNewSkill] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const loadProfile = async () => {
    try {
      const data = await getProfile();
      setProfile(data);
      setBio(data.bio || "");
      setCurrentOcc(data.current_occupation || "");
      setTargetOcc(data.target_occupation || "");
      setSkills(data.parsed_skills || []);
    } catch (err) {
      console.error("Failed to load profile", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setStatusMsg("Parsing resume contents...");
    try {
      const updated = await uploadResume(file);
      setProfile(updated);
      setBio(updated.bio || "");
      setCurrentOcc(updated.current_occupation || "");
      setTargetOcc(updated.target_occupation || "");
      setSkills(updated.parsed_skills || []);
      setStatusMsg("Resume parsed successfully!");
    } catch (err: any) {
      setStatusMsg(err.message || "Failed to upload resume");
    } finally {
      setUploading(false);
      setTimeout(() => setStatusMsg(""), 4000);
    }
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const updated = await updateProfile({
        bio,
        current_occupation: currentOcc,
        target_occupation: targetOcc,
        parsed_skills: skills
      });
      setProfile(updated);
      setStatusMsg("Profile updated successfully!");
    } catch (err: any) {
      setStatusMsg("Failed to save profile details");
    } finally {
      setTimeout(() => setStatusMsg(""), 3000);
    }
  };

  const addSkill = () => {
    if (newSkill.trim() && !skills.includes(newSkill.trim())) {
      setSkills([...skills, newSkill.trim()]);
      setNewSkill("");
    }
  };

  const removeSkill = (skillToRemove: string) => {
    setSkills(skills.filter(s => s !== skillToRemove));
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
        <h1 className="text-3xl font-bold tracking-tight text-white">Workforce Intelligence Profile</h1>
        <p className="text-sm text-gray-400 mt-1">
          Manage your career embeddings, upload resumes, and explore skill structures.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Resume Upload / Bio */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-card rounded-2xl p-6 border border-white/5 relative">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary-400" />
              Resume Intelligence
            </h2>
            <p className="text-xs text-gray-400 mb-6">
              Upload your PDF resume to instantly extract occupations, target skills, and map your Skill DNA.
            </p>
            
            <label className="flex flex-col items-center justify-center border border-dashed border-white/10 hover:border-primary-500/50 rounded-xl p-8 cursor-pointer transition-all bg-white/5 hover:bg-white/10 group relative">
              <UploadCloud className="h-10 w-10 text-gray-400 group-hover:text-primary-500 transition-colors mb-3" />
              <span className="text-sm font-semibold text-white">Upload Resume</span>
              <span className="text-xs text-gray-400 mt-1">PDF format (Max 5MB)</span>
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileUpload}
                disabled={uploading}
              />
            </label>

            {statusMsg && (
              <div className={`mt-4 p-3 rounded-lg text-xs font-semibold flex items-center gap-2 ${
                statusMsg.includes("Failed") 
                  ? "bg-red-500/10 border border-red-500/20 text-red-400" 
                  : "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
              }`}>
                <CheckCircle className="h-4 w-4 flex-shrink-0" />
                {statusMsg}
              </div>
            )}
          </div>

          {/* Quick Metrics */}
          <div className="glass-card rounded-2xl p-6 border border-white/5">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-cyber-cyan" />
              Embedding Meta
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="text-xs text-gray-400">Total Skills Map</span>
                <span className="text-xs font-bold text-white">{skills.length} skills</span>
              </div>
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="text-xs text-gray-400">GNN Alignment</span>
                <span className="text-xs font-bold text-cyber-cyan">384 Dimensions</span>
              </div>
              <div className="flex items-center justify-between pb-2">
                <span className="text-xs text-gray-400">Knowledge Type</span>
                <span className="text-xs font-bold text-primary-400">Heterogeneous Graph</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Profile Form & Skills Badges */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card rounded-2xl p-8 border border-white/5">
            <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-indigo-400" />
              Career Details
            </h2>

            <form onSubmit={handleProfileSave} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Current Occupation</label>
                  <input
                    type="text"
                    placeholder="e.g. Data Scientist"
                    value={currentOcc}
                    onChange={(e) => setCurrentOcc(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Target Occupation</label>
                  <input
                    type="text"
                    placeholder="e.g. Machine Learning Engineer"
                    value={targetOcc}
                    onChange={(e) => setTargetOcc(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Professional Bio</label>
                <textarea
                  rows={3}
                  placeholder="Tell us about your technical expertise..."
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg glass-input text-sm"
                />
              </div>

              {/* Skills Editor */}
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-2">My Skill Sets</label>
                <div className="flex gap-2 mb-4">
                  <input
                    type="text"
                    placeholder="Add a skill..."
                    value={newSkill}
                    onChange={(e) => setNewSkill(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                    className="flex-1 px-4 py-2 rounded-lg glass-input text-sm"
                  />
                  <button
                    type="button"
                    onClick={addSkill}
                    className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-sm text-white font-medium shadow-neon transition-colors"
                  >
                    Add
                  </button>
                </div>

                <div className="flex flex-wrap gap-2 min-h-[60px] p-3 rounded-lg border border-white/5 bg-white/5">
                  {skills.length === 0 ? (
                    <span className="text-xs text-gray-400">No skills added yet.</span>
                  ) : (
                    skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary-500/10 text-primary-300 border border-primary-500/20"
                      >
                        {skill}
                        <button
                          type="button"
                          onClick={() => removeSkill(skill)}
                          className="h-3 w-3 hover:text-red-400 transition-colors"
                        >
                          &times;
                        </button>
                      </span>
                    ))
                  )}
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <button
                  type="submit"
                  className="px-6 py-2.5 bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-700 hover:to-indigo-700 text-white font-medium text-sm rounded-lg shadow-neon transition-colors"
                >
                  Save Profile Settings
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
