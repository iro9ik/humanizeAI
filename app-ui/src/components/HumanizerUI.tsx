import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUp, Loader2, Sparkles, Briefcase, GraduationCap, PenTool, Eye, EyeOff, Copy, Check, X } from 'lucide-react';
import { cn } from '../lib/utils';
import { computeWordDiff, type DiffToken } from '../lib/diff';
import lightLogo from '../assets/light.png';

const HERO_TEXTS = [
  "Ready to convert?",
  "Ready to fix the tone?",
  "Time to make it better.",
  "Make it professional instantly.",
  "Bring your text to life."
];

const LOADING_TEXTS = [
  "Refining...",
  "Polishing...",
  "Almost ready..."
];

const MODES = [
  { id: 'clear', label: 'Clear', icon: Sparkles },
  { id: 'professional', label: 'Professional', icon: Briefcase },
  { id: 'academic', label: 'Academic', icon: GraduationCap },
  { id: 'creative', label: 'Creative', icon: PenTool }
];

const COMMON_ENGLISH_WORDS = new Set([
  "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
  "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
  "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
  "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
  "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
  "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
  "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
  "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
  "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
  "even", "new", "want", "because", "any", "these", "give", "day", "most", "us"
]);

function validateInputFrontend(text: string): { isValid: boolean; message: string } {
  if (!text || !text.trim()) {
    return { isValid: false, message: "Please provide text to transform." };
  }

  const words = text.trim().split(/\s+/).filter(w => w.length > 0);
  if (words.length < 20) {
    return { isValid: false, message: "Text too short, minimum 20 words required." };
  }

  // Latin character check for non-English languages (Russian, Chinese, Arabic, etc.)
  const latinChars = (text.match(/[a-zA-Z]/g) || []).length;
  const totalChars = text.replace(/\s/g, "").length;
  if (totalChars > 0) {
    const latinRatio = latinChars / totalChars;
    if (latinRatio < 0.7) {
      return { isValid: false, message: "Only English text is supported." };
    }
  }

  // Clean words to check English words ratio
  const cleanedWords = words.map(w => w.replace(/[^\w']/g, "").toLowerCase()).filter(w => w);
  const commonCount = cleanedWords.filter(w => COMMON_ENGLISH_WORDS.has(w)).length;
  const commonRatio = commonCount / Math.max(1, cleanedWords.length);

  if (commonRatio < 0.18) {
    const uniqueWords = new Set(cleanedWords).size;
    if (uniqueWords < 5) {
      return { isValid: false, message: "Text must contain valid words." };
    }

    const vowels = (text.match(/[aeiouyAEIOUY]/g) || []).length;
    const consonants = (text.match(/[bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ]/g) || []).length;
    const hasSmashPattern = /[asdfghjkl;']{8,}|[qweruiop]{8,}|[zxcvbnm]{8,}/i.test(text);

    if (vowels === 0 || (consonants / Math.max(1, vowels)) > 5.0 || hasSmashPattern) {
      return { isValid: false, message: "Text must contain valid words." };
    } else {
      return { isValid: false, message: "Only English text is supported." };
    }
  }

  return { isValid: true, message: "" };
}

export default function HumanizerUI() {
  const [inputText, setInputText] = useState('');
  const [submittedText, setSubmittedText] = useState('');
  const [mode, setMode] = useState('humanizer'); 
  
  const [heroIndex, setHeroIndex] = useState(0);
  const [loadingIndex, setLoadingIndex] = useState(0);
  
  const [status, setStatus] = useState<'idle' | 'validating' | 'loading' | 'success'>('idle');
  
  const [backendOutput, setBackendOutput] = useState<{output: string, msg: string, evalState: string} | null>(null);
  const [diffResult, setDiffResult] = useState<DiffToken[] | null>(null);
  const [apiMessage, setApiMessage] = useState<{type: 'error' | 'success', text: string} | null>(null);
  
  const [showDiff, setShowDiff] = useState(true);
  const [copied, setCopied] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Hero text rotation
  useEffect(() => {
    if (status !== 'idle' && status !== 'validating') return;
    const interval = setInterval(() => {
      setHeroIndex((prev) => (prev + 1) % HERO_TEXTS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [status]);

  // Loading text rotation
  useEffect(() => {
    if (status !== 'loading') return;
    const interval = setInterval(() => {
      setLoadingIndex((prev) => (prev + 1) % LOADING_TEXTS.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [status]);

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    // If they start typing again, bring them back to idle mode instantly
    if (status === 'success') {
      setStatus('idle');
      setApiMessage(null);
    }
    if (apiMessage?.type === 'error') {
      setApiMessage(null); 
    }
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 300)}px`;
    }
  };

  const handleCopy = () => {
    if (backendOutput?.output) {
      navigator.clipboard.writeText(backendOutput.output);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSubmit = async () => {
    if (!inputText.trim()) return;
    
    const textToSubmit = inputText;
    
    setStatus('validating');
    setBackendOutput(null);
    setDiffResult(null);
    setApiMessage(null);

    // Run robust frontend validations matching backend checks
    const validation = validateInputFrontend(textToSubmit);
    if (!validation.isValid) {
      setStatus('idle');
      setApiMessage({ type: 'error', text: validation.message });
      return;
    }
    
    // Validation passed! Transition immediately to Split View showing loading Skeletons
    setSubmittedText(textToSubmit);
    setStatus('loading');
    
    try {
      const response = await fetch('http://localhost:8000/humanize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToSubmit,
          mode: mode.toUpperCase(),
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        const out = data.output || data.result || '';
        const msg = data.message || '';
        const evalState = data.ai_evaluation || data.status;
        
        if (evalState === 'INVALID_INPUT' || msg.startsWith('INVALID_INPUT') || (!out.trim() && msg)) {
          // Backend double-check rule failure -> return to input screen with preserved text
          setStatus('idle');
          setApiMessage({ type: 'error', text: msg.replace('INVALID_INPUT:', '').trim() });
        } else {
          // Success! Update output and transition directly to success state
          setBackendOutput({ output: out, msg, evalState });
          setDiffResult(computeWordDiff(textToSubmit, out));
          setInputText(''); // Clear input
          if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'; // Reset text box height
          }
          setStatus('success');
          if (msg) setApiMessage({ type: 'success', text: msg });
        }
      } else {
        console.error("API Error Response:", data);
        setStatus('idle');
        setApiMessage({ type: 'error', text: 'Server error occurred. Please try again later.' });
      }
    } catch (err) {
      console.error("Fetch Exception:", err);
      setStatus('idle');
      setApiMessage({ type: 'error', text: 'Unable to connect to the backend server. Please make sure the service is running and try again.' });
    }
  };

  const lineCount = Math.min(12, Math.max(3, Math.ceil(submittedText.length / 60)));
  const skeletonLines = Array.from({ length: lineCount });

  return (
    <>
      <div className="absolute top-6 left-6 md:top-10 md:left-10 z-50">
        <img 
          src={lightLogo} 
          alt="Logo" 
          className="h-10 md:h-14 cursor-pointer select-none" 
          draggable="false"
          onContextMenu={(e) => e.preventDefault()}
          onClick={() => {
            setStatus('idle');
            setApiMessage(null);
            setBackendOutput(null);
            setInputText('');
          }} 
        />
      </div>

      {/* Background Component */}
      <div className="fixed inset-0 -z-10 bg-[#000000]">
        <motion.div
          animate={{ opacity: (status === 'idle' || status === 'validating') ? 1 : 0.3 }}
          transition={{ duration: 1 }}
          className="absolute inset-0 bg-[radial-gradient(circle_560px_at_50%_200px,#525252,transparent)]" 
        />
      </div>

      <div className="min-h-screen flex flex-col items-center pt-28 px-4 sm:px-6 pb-24">
        
        {/* HERO TEXT */}
        <AnimatePresence mode="wait">
          {(status === 'idle' || status === 'validating') && (
            <motion.div
              key="hero"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20, height: 0, marginBottom: 0 }}
              className="text-center w-full max-w-3xl mb-12 overflow-hidden"
            >
              <div className="h-16 flex items-center justify-center">
                <AnimatePresence mode="wait">
                  <motion.h1
                    key={heroIndex}
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: -20, opacity: 0 }}
                    transition={{ duration: 0.5, ease: "easeInOut" }}
                    className="text-4xl md:text-5xl font-semibold tracking-tight text-white"
                  >
                    {HERO_TEXTS[heroIndex]}
                  </motion.h1>
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* MAIN INPUT AREA (Always visible) */}
        <motion.div 
          layout
          className="w-full max-w-3xl flex flex-col items-center z-10"
        >
          <div className="w-full bg-[#111111]/80 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl transition-all duration-300 focus-within:border-white/30 focus-within:ring-1 focus-within:ring-white/20">
            <div className="relative w-full">
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={handleInput}
                disabled={status === 'validating' || status === 'loading'}
                placeholder="Paste your text here..."
                className="w-full bg-transparent text-white placeholder:text-white/30 p-6 pb-2 resize-none outline-none min-h-[140px] max-h-[300px] overflow-y-auto text-lg leading-relaxed text-mask disabled:opacity-50 transition-all duration-300"
              />
            </div>
            
            <div className="flex items-center justify-between p-4 pt-2">
              <div className="flex items-center gap-2"></div>

              <div className="flex items-center gap-3 ml-auto">
                {mode !== 'humanizer' && (
                  <div 
                    onClick={() => {
                      if (status !== 'validating' && status !== 'loading') {
                        setMode('humanizer');
                        if (status === 'success') setStatus('idle');
                      }
                    }}
                    className={cn(
                      "group flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-transparent hover:bg-white/10 transition-colors border border-transparent hover:border-white/10 text-white/70 hover:text-white cursor-pointer",
                      (status === 'validating' || status === 'loading') && "opacity-50 cursor-not-allowed hover:bg-transparent hover:border-transparent hover:text-white/70"
                    )}
                  >
                    <X size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                    <span className="text-sm font-medium">{MODES.find(m => m.id === mode)?.label}</span>
                  </div>
                )}
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim() || status === 'validating' || status === 'loading'}
                  className="bg-white text-black p-2.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-semibold transition-all w-11 h-11"
                >
                  {status === 'validating' ? (
                    <Loader2 size={20} className="animate-spin" />
                  ) : (
                    <ArrowUp size={20} strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* ERROR MESSAGE (Below Input) */}
          <AnimatePresence>
            {apiMessage?.type === 'error' && status === 'idle' && (
              <motion.div
                initial={{ opacity: 0, height: 0, y: -10 }}
                animate={{ opacity: 1, height: 'auto', y: 0 }}
                exit={{ opacity: 0, height: 0, y: -10 }}
                className="w-full mt-6"
              >
                <div className="bg-red-600 text-white px-6 py-4 rounded-xl flex items-center justify-center text-center shadow-lg">
                  <span className="text-base font-semibold tracking-wide">{apiMessage.text}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* MODE TAGS (Outside input box) */}
          <AnimatePresence>
            {(status === 'idle' || status === 'validating') && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                className="flex flex-wrap items-center justify-center gap-3 mt-8"
              >
                {MODES.map((m) => {
                  const Icon = m.icon;
                  const isActive = mode === m.id;
                  return (
                    <button
                      key={m.id}
                      disabled={status !== 'idle'}
                      onClick={() => setMode(isActive ? 'humanizer' : m.id)}
                      className={cn(
                        "flex items-center gap-2 px-4 py-2 rounded-full border transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed",
                        isActive 
                          ? "bg-white text-black border-white shadow-[0_0_20px_rgba(255,255,255,0.15)]" 
                          : "bg-[#111111]/60 text-white/60 border-white/10 hover:bg-white/10 hover:text-white hover:border-white/20"
                      )}
                    >
                      <Icon size={16} strokeWidth={isActive ? 2.5 : 2} />
                      <span className="text-sm font-medium">{m.label}</span>
                    </button>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* RESULTS SPLIT VIEW */}
        <AnimatePresence>
          {(status === 'loading' || status === 'success') && (
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="w-full max-w-7xl flex flex-col gap-6 items-center mt-12"
            >
              
              {/* SUCCESS MESSAGE */}
              <AnimatePresence>
                {apiMessage?.type === 'success' && status === 'success' && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-3xl text-white border-2 border-white bg-transparent px-6 py-4 rounded-xl flex items-center justify-center text-center mb-2"
                  >
                    <span className="text-base font-semibold tracking-wide">{apiMessage.text}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="w-full flex flex-col md:flex-row gap-6 items-stretch relative">
                
                {/* MIDDLE BLURRY LOADER */}
                <AnimatePresence>
                  {status === 'loading' && (
                    <motion.div 
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 1.05 }}
                      transition={{ duration: 0.3 }}
                      className="absolute inset-[-16px] z-50 flex items-center justify-center rounded-[2rem] backdrop-blur-[3px] pointer-events-none"
                    >
                      <div className="bg-[#0A0A0A]/90 border border-white/20 rounded-2xl p-8 flex flex-col items-center justify-center shadow-2xl">
                        <Loader2 size={36} className="animate-spin text-white mb-5" />
                        <div className="h-8 overflow-hidden flex items-center justify-center">
                          <AnimatePresence mode="wait">
                            <motion.div
                              key={loadingIndex}
                              initial={{ y: 20, opacity: 0 }}
                              animate={{ y: 0, opacity: 1 }}
                              exit={{ y: -20, opacity: 0 }}
                              transition={{ duration: 0.3 }}
                              className="text-xl text-white font-medium tracking-wide"
                            >
                              {LOADING_TEXTS[loadingIndex]}
                            </motion.div>
                          </AnimatePresence>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* LEFT CARD (Input / Original) */}
                <div className="w-full md:w-1/2 flex flex-col">
                  <div className="h-8 flex items-center justify-between mb-4 px-2">
                    <div className="flex items-center gap-3">
                      <h3 className="text-white/50 font-medium text-sm tracking-wider uppercase">Original Input</h3>
                      {/* Mode Tag for Input Side */}
                      <AnimatePresence>
                        {status === 'success' && backendOutput?.evalState && backendOutput.evalState !== 'INVALID_INPUT' && (
                          <motion.span 
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className={cn(
                              "text-[10px] font-bold px-2.5 py-1 rounded uppercase tracking-wider flex items-center gap-1.5 shadow-sm",
                              backendOutput.evalState.toUpperCase().replace(' ', '_').replace('-', '_') === 'AI_GENERATED' ? "bg-red-600 text-white" : "bg-emerald-600 text-white"
                            )}
                          >
                            {backendOutput.evalState.replace('_', ' ')}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                  <div className="bg-[#111111]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl min-h-[300px] flex flex-col relative overflow-hidden h-full">
                    <div className={cn("text-white/80 text-lg leading-relaxed whitespace-pre-wrap flex-1 overflow-y-auto text-mask", status === 'loading' && "opacity-40 blur-[1px]")}>
                      {status === 'success' && showDiff && diffResult ? (
                        diffResult.map((token, i) => {
                          if (token.op === 'delete') {
                            if (!token.value.trim()) return <span key={i}>{token.value}</span>;
                            return <span key={i} className="text-red-300 bg-red-500/20 rounded px-1 pb-0.5 mx-0.5 line-through decoration-red-400/50">{token.value}</span>;
                          }
                          if (token.op === 'equal') {
                            return <span key={i}>{token.value}</span>;
                          }
                          return null;
                        })
                      ) : (
                        submittedText
                      )}
                    </div>
                  </div>
                </div>

                {/* RIGHT CARD (Output) */}
                <div className="w-full md:w-1/2 flex flex-col">
                  <div className="h-8 flex items-center justify-between mb-4 px-2">
                    <div className="flex items-center gap-3">
                      <h3 className="text-white font-medium text-sm tracking-wider uppercase">
                        Refined Output
                      </h3>
                      {/* Mode Tag for Output Side */}
                      <AnimatePresence>
                        {status === 'success' && backendOutput?.evalState?.toUpperCase().replace(' ', '_').replace('-', '_') !== 'HUMAN_LIKE' && (
                          <motion.span 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="text-[10px] font-bold px-2.5 py-1 rounded bg-white text-black uppercase tracking-wider flex items-center gap-1.5"
                          >
                            {mode === 'humanizer' ? 'Humanized' : mode}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </div>
                    
                    {status === 'success' && (
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={() => setShowDiff(!showDiff)}
                          className="text-white/50 hover:text-white transition-colors p-2 rounded-lg hover:bg-white/10 flex items-center gap-2 text-xs font-medium uppercase tracking-wider"
                        >
                          {showDiff ? <><EyeOff size={16} /> Hide Diff</> : <><Eye size={16} /> Show Diff</>}
                        </button>
                        <div className="w-px h-4 bg-white/20 mx-1"></div>
                        <button 
                          onClick={handleCopy}
                          className="text-white/50 hover:text-white transition-colors p-2 rounded-lg hover:bg-white/10"
                          title="Copy to clipboard"
                        >
                          {copied ? <Check size={18} className="text-green-400" /> : <Copy size={18} />}
                        </button>
                      </div>
                    )}
                  </div>
                  
                  <div className="bg-[#111111]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl min-h-[300px] flex flex-col relative overflow-hidden h-full">
                    
                    {status === 'loading' ? (
                      <div className="text-white/20 space-y-4 pt-2">
                        {skeletonLines.map((_, i) => (
                          <div 
                            key={i} 
                            className={cn(
                              "h-[18px] bg-white/20 rounded-md animate-pulse",
                              i === skeletonLines.length - 1 ? "w-2/3" : "w-full"
                            )}
                            style={{ animationDelay: `${i * 100}ms` }}
                          ></div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-white text-lg leading-relaxed whitespace-pre-wrap flex-1 overflow-y-auto text-mask">
                        {showDiff && diffResult ? (
                          diffResult.map((token, i) => {
                            if (token.op === 'insert') {
                              if (!token.value.trim()) return <span key={i}>{token.value}</span>;
                              return <span key={i} className="text-green-300 bg-green-500/20 rounded px-1 pb-0.5 mx-0.5">{token.value}</span>;
                            }
                            if (token.op === 'equal') {
                              return <span key={i}>{token.value}</span>;
                            }
                            return null;
                          })
                        ) : (
                          backendOutput?.output
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </>
  );
}
