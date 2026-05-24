"use client";

import { useEffect, useRef, useState } from "react";
import { getGraphData, searchSkills, getNodeDetails } from "@/lib/api";
import { Share2, RefreshCw, ZoomIn, ZoomOut, Maximize2, Compass } from "lucide-react";

export default function InteractiveGraphPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const layoutRef = useRef<any>(null);
  const latestLoadIdRef = useRef<number>(0);
  const [cyInstance, setCyInstance] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);

  // Core load function
  const initGraph = async (centerId?: string) => {
    const loadId = ++latestLoadIdRef.current;
    setLoading(true);
    try {
      const data = await getGraphData(centerId);
      if (loadId !== latestLoadIdRef.current) {
        return;
      }
      if (!data || !data.nodes || !data.edges) {
        console.error("Invalid graph data received:", data);
        setLoading(false);
        return;
      }
      
      // Dynamic import to prevent SSR crashes on Vercel/Next
      const cytoscape = (await import("cytoscape")).default;
      
      // Prepare elements
      const elements: any[] = [];
      data.nodes.forEach((node: any) => {
        elements.push({
          data: {
            id: node.id,
            name: node.name,
            type: node.type,
            color: node.type === "Skill" ? "#6366f1" : "#a855f7",
            shape: node.type === "Skill" ? "ellipse" : "round-rectangle"
          }
        });
      });
      
      data.edges.forEach((edge: any) => {
        elements.push({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.type
          }
        });
      });

      if (containerRef.current) {
        if (layoutRef.current) {
          try {
            layoutRef.current.stop();
          } catch (e) {
            console.error("Error stopping cytoscape layout:", e);
          }
        }
        if (cyRef.current) {
          try {
            cyRef.current.destroy();
          } catch (e) {
            console.error("Error destroying cytoscape instance:", e);
          }
        }

        const cy = cytoscape({
          container: containerRef.current,
          elements: elements,
          style: [
            {
              selector: "node",
              style: {
                "background-color": "data(color)",
                "label": "data(name)",
                "color": "#fff",
                "font-size": "10px",
                "text-valign": "center",
                "text-halign": "center",
                "width": "45px",
                "height": "45px",
                "shape": "data(shape)" as any,
                "border-width": "2px",
                "border-color": "#1e1b4b",
                "text-wrap": "wrap",
                "text-max-width": "45px"
              }
            },
            {
              selector: "edge",
              style: {
                "width": 1.5,
                "line-color": "#4b5563",
                "target-arrow-color": "#4b5563",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "label": "data(label)",
                "font-size": "7px",
                "color": "#9ca3af",
                "text-rotation": "autorotate",
                "text-margin-y": -7
              }
            },
            {
              selector: "node:selected",
              style: {
                "border-color": "#00f0ff",
                "border-width": "4px",
                "shadow-color": "#00f0ff",
                "shadow-blur": 10,
                "shadow-opacity": 0.8
              } as any
            }
          ]
        });

        // Patch endBatch to prevent crashes when instance is destroyed during layout frames
        const originalEndBatch = (cy as any).endBatch;
        (cy as any).endBatch = function() {
          if ((cy as any).destroyed() || !(cy as any).renderer()) {
            return cy;
          }
          return originalEndBatch.apply(cy, arguments);
        };

        // Initialize and run layout separately, caching its reference
        const layout = cy.layout({
          name: "cose",
          idealEdgeLength: 80,
          nodeOverlap: 20,
          refresh: 20,
          fit: true,
          padding: 30,
          randomize: true,
          componentSpacing: 100,
          nodeRepulsion: 400000,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0
        } as any);

        layout.run();
        layoutRef.current = layout;

        // Event hooks
        cy.on("tap", "node", async (evt) => {
          const node = evt.target;
          setSelectedNode({
            id: node.id(),
            name: node.data("name"),
            type: node.data("type"),
            loading: true
          });
          try {
            const data = await getNodeDetails(node.id());
            setSelectedNode(data);
          } catch (err) {
            console.error(err);
            setSelectedNode({
              id: node.id(),
              name: node.data("name"),
              type: node.data("type"),
              related_jobs: [],
              courses: []
            });
          }
        });

        // Double click to refocus
        cy.on("dbltap", "node", (evt) => {
          const node = evt.target;
          initGraph(node.id());
        });

        setCyInstance(cy);
        cyRef.current = cy;
      }
    } catch (err) {
      console.error(err);
    } finally {
      if (loadId === latestLoadIdRef.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    initGraph();
    return () => {
      if (layoutRef.current) {
        try {
          layoutRef.current.stop();
        } catch (e) {
          console.error("Error stopping cytoscape layout on unmount:", e);
        }
      }
      if (cyRef.current) {
        try {
          cyRef.current.destroy();
        } catch (e) {
          console.error("Error destroying cytoscape instance on unmount:", e);
        }
      }
    };
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      try {
        const results = await searchSkills(searchQuery.trim());
        setSearchResults(results.results || []);
      } catch (err) {
        console.error(err);
      }
    } else {
      setSearchResults([]);
    }
  };

  const handleSelectSearchResult = (nodeId: string) => {
    initGraph(nodeId);
    setSearchQuery("");
    setSearchResults([]);
  };

  // Zoom handlers
  const zoomIn = () => cyInstance?.zoom(cyInstance.zoom() + 0.1);
  const zoomOut = () => cyInstance?.zoom(cyInstance.zoom() - 0.1);
  const fitGraph = () => cyInstance?.fit();

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Share2 className="h-7 w-7 text-primary-400" />
            SkillGraph Knowledge Explorer
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Navigate the workforce ontology. Double-click a node to refocus neighbor topologies.
          </p>
        </div>

        {/* Dynamic Search */}
        <form onSubmit={handleSearch} className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Search nodes semantically..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-4 pr-10 py-2 rounded-lg glass-input text-xs"
          />
          <button type="submit" className="absolute right-3 top-2.5 text-gray-400 hover:text-white">
            <RefreshCw className="h-4 w-4" />
          </button>
          
          {/* Search Dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute left-0 right-0 mt-2 bg-cyber-darkBlue border border-white/10 rounded-lg shadow-2xl z-50 max-h-60 overflow-y-auto">
              {searchResults.map((res) => (
                <button
                  key={res.id}
                  onClick={() => handleSelectSearchResult(res.id)}
                  className="w-full px-4 py-2.5 text-left text-xs hover:bg-white/5 border-b border-white/5 text-gray-300 flex justify-between items-center"
                >
                  <span>{res.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-300">
                    {res.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </form>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Graph Container */}
        <div className="lg:col-span-3 glass-card rounded-2xl border border-white/5 relative min-h-[500px] overflow-hidden flex flex-col justify-center">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-xs z-10">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
            </div>
          )}
          
          {/* View Toolbar */}
          <div className="absolute bottom-4 left-4 z-10 flex gap-2">
            <button onClick={zoomIn} className="p-2 bg-white/5 border border-white/5 rounded-lg text-gray-300 hover:text-white hover:bg-white/10">
              <ZoomIn className="h-4.5 w-4.5" />
            </button>
            <button onClick={zoomOut} className="p-2 bg-white/5 border border-white/5 rounded-lg text-gray-300 hover:text-white hover:bg-white/10">
              <ZoomOut className="h-4.5 w-4.5" />
            </button>
            <button onClick={fitGraph} className="p-2 bg-white/5 border border-white/5 rounded-lg text-gray-300 hover:text-white hover:bg-white/10">
              <Maximize2 className="h-4.5 w-4.5" />
            </button>
            <button onClick={() => initGraph()} className="p-2 bg-white/5 border border-white/5 rounded-lg text-gray-300 hover:text-white hover:bg-white/10">
              <Compass className="h-4.5 w-4.5" />
            </button>
          </div>

          <div ref={containerRef} className="w-full h-[500px]"></div>
        </div>

        {/* Right Info Panel */}
        <div className="lg:col-span-1 glass-card rounded-2xl p-6 border border-white/5 flex flex-col min-h-[400px]">
          <h3 className="text-sm font-bold text-white mb-6 border-b border-white/5 pb-3">
            Node Details Panel
          </h3>

          {selectedNode ? (
            <div className="space-y-6 flex-1">
              <div>
                <span className="text-[10px] uppercase tracking-wider font-extrabold text-primary-400 block">
                  {selectedNode.type} Node
                </span>
                <h4 className="text-lg font-bold text-white mt-1 leading-snug">
                  {selectedNode.name}
                </h4>
              </div>

              {selectedNode.loading ? (
                <div className="flex h-32 items-center justify-center">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-500 border-t-transparent"></div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="border-b border-white/5 pb-2 text-left">
                    <span className="text-[10px] text-gray-400 block">System ID</span>
                    <code className="text-xs font-mono text-cyber-cyan">{selectedNode.id}</code>
                  </div>
                  <div className="text-left">
                    <span className="text-[10px] text-gray-400 block mb-2">
                      {selectedNode.type === "Skill" ? "Related Occupations/Jobs" : "Required Skills"}
                    </span>
                    {selectedNode.related_jobs && selectedNode.related_jobs.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {selectedNode.related_jobs.map((item: any) => (
                          <span
                            key={item.id}
                            className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white/5 border border-white/5 text-gray-300"
                          >
                            {item.name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[11px] text-gray-400 italic">No direct relationships found.</p>
                    )}
                  </div>
                  <div className="text-left">
                    <span className="text-[10px] text-gray-400 block mb-2">
                      {selectedNode.type === "Skill" ? "Recommended Courses / Referrals" : "Target Career Transitions"}
                    </span>
                    {selectedNode.courses && selectedNode.courses.length > 0 ? (
                      <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                        {selectedNode.courses.map((course: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-2 bg-white/5 rounded border border-white/5 text-left"
                          >
                            <h5 className="text-[11px] font-bold text-white mb-0.5">{course.resource_name}</h5>
                            <div className="flex items-center justify-between text-[9px] text-gray-400 mt-1">
                              <span>{course.duration}</span>
                              {course.url && course.url !== "#" ? (
                                <a
                                  href={course.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-cyber-cyan hover:underline font-semibold"
                                >
                                  Explore Course &rarr;
                                </a>
                              ) : (
                                <span className="text-gray-500">Curriculum path</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[11px] text-gray-400 italic">No recommendations available.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <Share2 className="h-8 w-8 text-gray-500 mb-3" />
              <p className="text-xs text-gray-400">
                Click a node inside the explorer graph to view detailed vector relationships and metadata.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
