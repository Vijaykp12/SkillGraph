let BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
let WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/assistant/ws/chat";

if (typeof window !== "undefined") {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  
  if (hostname.endsWith(".github.dev") || hostname.endsWith(".app.github.dev") || hostname.includes("preview.app.github.dev")) {
    const backendHostname = hostname.replace("-3000", "-8000");
    const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
    BASE_URL = `${protocol}//${backendHostname}/api/v1`;
    WS_URL = `${wsProtocol}//${backendHostname}/api/v1/assistant/ws/chat`;
  }
}

function getHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function login(email: string, password: string) {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);
  
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params,
  });
  
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  
  const data = await res.json();
  if (typeof window !== "undefined") {
    localStorage.setItem("token", data.access_token);
  }
  return data;
}

export async function register(email: string, password: string, fullName?: string) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }
  
  return res.json();
}

export async function getProfile() {
  const res = await fetch(`${BASE_URL}/auth/profile`, {
    method: "GET",
    headers: getHeaders(),
  });
  
  if (!res.ok) {
    throw new Error("Failed to load profile");
  }
  return res.json();
}

export async function updateProfile(data: { bio?: string; current_occupation?: string; target_occupation?: string; parsed_skills?: string[] }) {
  const res = await fetch(`${BASE_URL}/auth/profile`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    throw new Error("Failed to update profile");
  }
  return res.json();
}

export async function uploadResume(file: File) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const formData = new FormData();
  formData.append("file", file);
  
  const res = await fetch(`${BASE_URL}/auth/resume/upload`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to parse resume");
  }
  return res.json();
}

export async function searchSkills(q: string, itemType?: string) {
  const queryParam = itemType ? `?q=${q}&item_type=${itemType}` : `?q=${q}`;
  const res = await fetch(`${BASE_URL}/skills/search${queryParam}`, {
    method: "GET",
    headers: getHeaders(),
  });
  return res.json();
}

export async function getGraphData(centerId?: string) {
  const queryParam = centerId ? `?center_id=${centerId}` : "";
  const res = await fetch(`${BASE_URL}/skills/explorer${queryParam}`, {
    method: "GET",
    headers: getHeaders(),
  });
  return res.json();
}

export async function getGapAnalysis(targetOccupation: string, currentSkills?: string[]) {
  const res = await fetch(`${BASE_URL}/recs/gap-analysis`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ target_occupation: targetOccupation, current_skills: currentSkills }),
  });
  if (!res.ok) throw new Error("Gap analysis calculation failed");
  return res.json();
}

export async function simulateTwin(startOccupation: string, targetOccupation: string) {
  const res = await fetch(`${BASE_URL}/recs/twin-simulator`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ start_occupation: startOccupation, target_occupation: targetOccupation }),
  });
  if (!res.ok) throw new Error("Twin simulation failed");
  return res.json();
}

export async function getLearningRecommendations(targetOccupation?: string, currentSkills?: string[]) {
  const res = await fetch(`${BASE_URL}/recs/learning-resources`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ target_occupation: targetOccupation, current_skills: currentSkills }),
  });
  return res.json();
}

export async function getNodeDetails(nodeId: string) {
  const res = await fetch(`${BASE_URL}/skills/node/${nodeId}`, {
    method: "GET",
    headers: getHeaders(),
  });
  return res.json();
}

export function getChatWebSocket(): WebSocket {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : "";
  const ws = new WebSocket(WS_URL);
  
  ws.onopen = () => {
    // Send auth token as first frame
    ws.send(JSON.stringify({ token }));
  };
  
  return ws;
}
