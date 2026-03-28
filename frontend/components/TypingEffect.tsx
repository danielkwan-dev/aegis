"use client";

import { useEffect, useState } from "react";

interface TypingEffectProps {
  text: string;
  speed?: number;
  style?: React.CSSProperties;
}

export default function TypingEffect({ text, speed = 18, style }: TypingEffectProps) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return (
    <span style={style}>
      {displayed}
      {!done && (
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
    </span>
  );
}
