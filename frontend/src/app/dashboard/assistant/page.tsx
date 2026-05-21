"use client";

import { useEffect, useRef, useState } from "react";
import { getChatWebSocket } from "@/lib/api";
import { MessageSquare, Send, Sparkles, HelpCircle, Terminal } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I am your SkillGraph AI Career Coach. I can analyze your Skill DNA, simulate career twin pathways, calculate skill gaps, and recommend learning resources. What would you like to explore today?"
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [streamingResponse, setStreamingResponse] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingResponse]);

  // Connect to websocket
  useEffect(() => {
    let socket: WebSocket;
    try {
      socket = getChatWebSocket();
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.status === "authenticated") {
          setConnected(true);
        } else if (data.type === "chunk") {
          // Streaming chunk
          setStreamingResponse(data.content);
          if (data.done) {
            // Append complete message
            setMessages((prev) => [...prev, { role: "assistant", content: data.content }]);
            setStreamingResponse("");
          }
        } else if (data.error) {
          console.error("WS error frame:", data.error);
        }
      };

      socket.onclose = () => {
        setConnected(false);
      };

      setWs(socket);
    } catch (err) {
      console.error(err);
    }

    return () => {
      socket?.close();
    };
  }, []);

  const handleSend = (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim() || !ws || !connected) return;

    // 1. Add user message
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    if (!textToSend) setInputText("");

    // 2. Send frame via WebSocket
    ws.send(JSON.stringify({ message: text }));
  };

  const samplePrompts = [
    "What is my skill gap?",
    "Simulate a career path to Machine Learning Engineer",
    "Show me salary trends",
    "What course should I take?"
  ];

  return (
    <div className="space-y-8 max-w-4xl h-[calc(100vh-12rem)] flex flex-col">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          <MessageSquare className="h-7 w-7 text-primary-400" />
          AI Multi-Agent Career Assistant
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Chat with your personal career agent. Powered by streaming WebSockets and GNN vector reasoning.
        </p>
      </div>

      <div className="flex-1 glass-card rounded-2xl border border-white/5 overflow-hidden flex flex-col relative min-h-[400px]">
        {/* Connection status banner */}
        <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between bg-black/40 text-[10px]">
          <span className="flex items-center gap-1.5 text-gray-400">
            <Terminal className="h-3.5 w-3.5" />
            Session Socket Interface
          </span>
          <span className={`font-bold flex items-center gap-1 ${connected ? "text-emerald-400" : "text-amber-400"}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`}></span>
            {connected ? "WebSocket Connected" : "Connecting Handshake..."}
          </span>
        </div>

        {/* Messages container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-primary-600 text-white"
                    : "glass-card border border-white/10 text-gray-200"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {/* Streaming display bubble */}
          {streamingResponse && (
            <div className="flex justify-start">
              <div className="max-w-[75%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed glass-card border border-white/10 text-gray-200">
                {streamingResponse}
                <span className="inline-block h-3 w-1.5 ml-1 bg-primary-400 animate-pulse"></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Chips */}
        <div className="px-6 py-3 border-t border-white/5 bg-white/[0.01] flex flex-wrap gap-2 items-center">
          <HelpCircle className="h-3.5 w-3.5 text-gray-400" />
          {samplePrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              disabled={!connected}
              className="text-[10px] px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-white/5 rounded-full text-gray-400 hover:text-white transition-all disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input box */}
        <div className="p-4 border-t border-white/5 bg-black/20">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              required
              disabled={!connected}
              placeholder={connected ? "Ask me anything about your career path..." : "Connecting to chatbot service..."}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="flex-1 px-4 py-3 rounded-xl glass-input text-xs disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!connected || !inputText.trim()}
              className="p-3 bg-primary-600 hover:bg-primary-700 text-white rounded-xl shadow-neon transition-all flex items-center justify-center disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
