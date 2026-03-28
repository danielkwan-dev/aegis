"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";

const GLITCH_CHARS = "ABCDEFabcdef0123456789!@#$%&*<>{}[]=/\\|~^";

interface TypingEffectProps {
  text: string;
  speed?: number;
  decipherDuration?: number;
  style?: React.CSSProperties;
  className?: string;
}

export default function TypingEffect({
  text,
  speed = 14,
  decipherDuration = 500,
  style,
  className,
}: TypingEffectProps) {
  const [phase, setPhase] = useState<"decipher" | "typing" | "done">("decipher");
  const [displayed, setDisplayed] = useState("");
  const [glitchText, setGlitchText] = useState("");
  const rafRef = useRef<number>(0);

  // Phase 1: Decipher — random flickering characters
  useEffect(() => {
    setPhase("decipher");
    setDisplayed("");
    setGlitchText("");

    const start = performance.now();
    const previewLen = Math.min(text.length, 60);

    function animateGlitch(now: number) {
      const elapsed = now - start;
      if (elapsed >= decipherDuration) {
        setPhase("typing");
        return;
      }
      // Generate random characters that gradually settle
      const progress = elapsed / decipherDuration;
      let result = "";
      for (let i = 0; i < previewLen; i++) {
        if (Math.random() < progress * 0.3) {
          result += text[i] ?? " ";
        } else {
          result += GLITCH_CHARS[Math.floor(Math.random() * GLITCH_CHARS.length)];
        }
      }
      setGlitchText(result);
      rafRef.current = requestAnimationFrame(animateGlitch);
    }

    rafRef.current = requestAnimationFrame(animateGlitch);
    return () => cancelAnimationFrame(rafRef.current);
  }, [text, decipherDuration]);

  // Phase 2: Type out real text
  useEffect(() => {
    if (phase !== "typing") return;
    setGlitchText("");
    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
        setPhase("done");
      }
    }, speed);
    return () => clearInterval(interval);
  }, [phase, text, speed]);

  return (
    <motion.span
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      style={style}
      className={className}
    >
      {phase === "decipher" && (
        <span style={{ color: "#06b6d4", opacity: 0.7, letterSpacing: "0.02em" }}>
          {glitchText}
        </span>
      )}
      {(phase === "typing" || phase === "done") && (
        <>
          {displayed}
          {phase === "typing" && (
            <span
              style={{
                display: "inline-block",
                width: "2px",
                height: "1em",
                backgroundColor: "#06b6d4",
                marginLeft: "2px",
                verticalAlign: "text-bottom",
                animation: "blink 0.8s step-end infinite",
              }}
            />
          )}
        </>
      )}
    </motion.span>
  );
}
