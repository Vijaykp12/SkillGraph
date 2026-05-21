"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { 
  User, Radar, Share2, Compass, MessageSquare, Dna, LogOut, Menu, X, Cpu
} from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/");
    } else {
      setAuthorized(true);
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/");
  };

  const navItems = [
    { name: "Profile Overview", path: "/dashboard", icon: User },
    { name: "Skill DNA Mapping", path: "/dashboard/dna", icon: Dna },
    { name: "Skill Gap Radar", path: "/dashboard/radar", icon: Radar },
    { name: "Career Twin Simulator", path: "/dashboard/twin", icon: Compass },
    { name: "Interactive Graph", path: "/dashboard/graph", icon: Share2 },
    { name: "Career Assistant", path: "/dashboard/assistant", icon: MessageSquare },
  ];

  if (!authorized) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex md:w-64 md:flex-col glass-card border-r border-white/5">
        <div className="flex h-16 items-center px-6 border-b border-white/5 gap-2">
          <Cpu className="h-6 w-6 text-primary-500" />
          <span className="font-extrabold text-lg bg-clip-text text-transparent bg-gradient-to-r from-primary-400 to-cyber-cyan">
            SkillGraph Hub
          </span>
        </div>
        
        <nav className="flex-1 space-y-1 px-4 py-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path;
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`flex items-center px-4 py-3 rounded-xl text-sm font-semibold transition-all gap-3 ${
                  isActive 
                    ? "bg-primary-600/20 text-primary-400 border border-primary-500/20 shadow-neon" 
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/5">
          <button
            onClick={handleLogout}
            className="flex w-full items-center px-4 py-3 rounded-xl text-sm font-semibold text-red-400 hover:text-red-300 hover:bg-red-500/5 transition-all gap-3"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Mobile Drawer Navigation */}
      <div className="md:hidden">
        {mobileOpen && (
          <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)}></div>
        )}
        <div
          className={`fixed inset-y-0 left-0 z-50 w-64 glass-card border-r border-white/5 flex flex-col transform transition-transform duration-300 ${
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex h-16 items-center justify-between px-6 border-b border-white/5">
            <div className="flex items-center gap-2">
              <Cpu className="h-6 w-6 text-primary-500" />
              <span className="font-extrabold text-lg bg-clip-text text-transparent bg-gradient-to-r from-primary-400 to-cyber-cyan">
                SkillGraph
              </span>
            </div>
            <button onClick={() => setMobileOpen(false)}>
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
          
          <nav className="flex-1 space-y-1 px-4 py-6">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.path;
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center px-4 py-3 rounded-xl text-sm font-semibold transition-all gap-3 ${
                    isActive 
                      ? "bg-primary-600/20 text-primary-400 border border-primary-500/20" 
                      : "text-gray-400 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-white/5">
            <button
              onClick={handleLogout}
              className="flex w-full items-center px-4 py-3 rounded-xl text-sm font-semibold text-red-400 hover:text-red-300 gap-3"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header - Mobile Menu Button */}
        <header className="flex h-16 items-center px-6 md:px-8 border-b border-white/5 justify-between">
          <button
            onClick={() => setMobileOpen(true)}
            className="md:hidden p-2 rounded-lg hover:bg-white/5"
          >
            <Menu className="h-5 w-5 text-gray-400" />
          </button>
          <div className="flex items-center gap-4 ml-auto">
            <div className="text-right">
              <p className="text-xs text-gray-400">Node Sync Status</p>
              <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5 justify-end">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                GNN Fused
              </p>
            </div>
          </div>
        </header>

        {/* Content View */}
        <main className="flex-1 overflow-y-auto px-6 py-8 md:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
