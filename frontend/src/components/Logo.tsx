import React from 'react';

export const AtomicNeuron = ({ className = "w-8 h-8", glow = true }) => {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {glow && (
        <div className="absolute inset-0 bg-[#007AFF]/20 blur-xl rounded-full scale-125 animate-pulse" />
      )}
      <svg
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10"
      >
        <circle cx="100" cy="100" r="80" stroke="#007AFF" strokeWidth="2" opacity="0.3"/>
        <circle cx="100" cy="100" r="40" stroke="#007AFF" strokeWidth="4"/>
        <path d="M80 100 Q100 60 120 100 T160 100" stroke="#007AFF" strokeWidth="3" strokeLinecap="round"/>
        <circle cx="100" cy="100" r="5" fill="#007AFF"/>
      </svg>
    </div>
  );
};

export const PureCortexLogo = ({ className = "h-8" }) => {
  return (
    <div className={`flex items-center gap-2 sm:gap-3 ${className}`}>
      <AtomicNeuron className="w-7 h-7 sm:w-8 sm:h-8 flex-shrink-0" glow={false} />
      <span className="text-xl sm:text-3xl font-black tracking-tight text-white font-sans uppercase">
        PURE<span className="text-[#007AFF]">CORTEX</span>
      </span>
    </div>
  );
};
