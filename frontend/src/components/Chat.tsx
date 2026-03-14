'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, Terminal, Shield, Cpu, Activity, Info, BarChart3, Wallet } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { AtomicNeuron } from './Logo';

export default function Chat() {
  const [messages, setMessages] = useState<{ sender: 'user' | 'agent'; text: string; timestamp: Date }[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const socketUrl = process.env.NEXT_PUBLIC_WS_URL || 'wss://purecortex.ai/ws/chat';
    ws.current = new WebSocket(socketUrl);
    
    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);
    
    ws.current.onmessage = (event) => {
      setIsTyping(false);
      setMessages((prev) => [...prev, { 
        sender: 'agent', 
        text: event.data, 
        timestamp: new Date() 
      }]);
    };

    return () => {
      ws.current?.close();
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !ws.current || !isConnected) return;

    ws.current.send(input);
    setMessages((prev) => [...prev, { 
      sender: 'user', 
      text: input, 
      timestamp: new Date() 
    }]);
    setInput('');
    setIsTyping(true);
  };

  return (
    <div className="flex flex-col h-[650px] w-full max-w-4xl mx-auto border border-white/5 rounded-2xl bg-[#050505] overflow-hidden shadow-2xl border-t-[#007AFF]/30">
      {/* Header */}
      <div className="bg-[#1A1A1A] p-5 border-b border-white/5 flex justify-between items-center backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="relative">
            <AtomicNeuron className="w-10 h-10" />
            <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-[#1A1A1A] ${isConnected ? 'bg-[#10B981]' : 'bg-[#EF4444]'}`} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight leading-none uppercase">Cortex-Omega-1</h2>
            <p className="text-[10px] text-[#007AFF] font-mono mt-1 uppercase tracking-[0.2em]">Neural Node Active</p>
          </div>
        </div>
        
        <div className="hidden md:flex gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-[10px] text-gray-400 font-mono uppercase tracking-tighter">
                <Shield className="w-3 h-3 text-[#10B981]" />
                Audit: Verified
            </div>
        </div>
      </div>
      
      {/* Messages Area */}
      <div ref={scrollRef} className="flex-1 p-6 overflow-y-auto space-y-6 scrollbar-thin scrollbar-thumb-white/10 bg-[url('https://www.transparenttextures.com/patterns/dark-matter.png')]">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full opacity-40 text-center px-10">
            <Terminal className="w-12 h-12 mb-4 text-[#007AFF]" />
            <h3 className="text-xl font-bold text-white mb-2 uppercase tracking-tighter italic">Neural Link Established</h3>
            <p className="text-sm text-gray-400 font-medium">Dual-Brain orchestration is online. PureCortex intelligence waiting for transmission.</p>
          </div>
        )}
        
        <AnimatePresence>
          {messages.map((msg, idx) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={idx} 
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] relative ${
                msg.sender === 'user' 
                  ? 'bg-[#007AFF] text-white rounded-2xl rounded-tr-none p-4 shadow-lg shadow-[#007AFF]/20' 
                  : 'bg-[#1A1A1A] text-gray-100 rounded-2xl rounded-tl-none p-4 border border-white/5 shadow-xl'
              }`}>
                <div className={`text-[9px] font-mono mb-1.5 uppercase tracking-widest opacity-60 flex items-center gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.sender === 'user' ? (
                    <>
                      <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      <span className="w-1 h-1 rounded-full bg-white/40" />
                      <span>Authenticated Controller</span>
                    </>
                  ) : (
                    <>
                      <Cpu className="w-3 h-3 text-[#007AFF]" />
                      <span>PureCortex Brain</span>
                      <span className="w-1 h-1 rounded-full bg-[#007AFF]/40" />
                      <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </>
                  )}
                </div>
                <div className="text-[14px] leading-relaxed font-sans font-medium">{msg.text}</div>
              </div>
            </motion.div>
          ))}
          
          {isTyping && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-[#1A1A1A] p-4 rounded-2xl rounded-tl-none border border-white/5 flex gap-1.5">
                <span className="w-2 h-2 bg-[#007AFF] rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-[#007AFF] rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-[#007AFF] rounded-full animate-bounce" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="p-6 bg-[#1A1A1A]/50 backdrop-blur-xl border-t border-white/5 flex gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Transmit command to Cortex..."
            className="w-full bg-[#050505] text-white border border-white/5 rounded-xl px-5 py-3.5 outline-none focus:ring-2 focus:ring-[#007AFF]/50 focus:border-[#007AFF]/50 transition-all placeholder:text-gray-700 font-medium"
          />
        </div>
        <button 
          type="submit" 
          disabled={!isConnected || !input.trim()}
          className="bg-[#007AFF] hover:bg-[#0062CC] disabled:opacity-30 disabled:cursor-not-allowed text-white px-6 rounded-xl font-black uppercase tracking-tighter transition-all shadow-lg shadow-[#007AFF]/20 active:scale-95 flex items-center justify-center"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Footer Info */}
      <div className="px-6 py-3 bg-[#050505] border-t border-white/5 flex flex-wrap justify-between items-center text-[9px] text-gray-600 font-mono uppercase tracking-widest">
        <div className="flex items-center gap-4">
           <span className="flex items-center gap-1 text-[#007AFF]"><Shield className="w-3 h-3" /> Hardened Link</span>
           <span className="flex items-center gap-1 text-[#10B981]"><Activity className="w-3 h-3" /> Algorand Testnet</span>
        </div>
        <div>
           INTEL_SESSION_ID: 2I7QEP...VGU
        </div>
      </div>
    </div>
  );
}
