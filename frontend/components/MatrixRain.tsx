"use client";

import { useEffect, useRef } from "react";

const CHARS =
  "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF<>[]{}|/\\";

interface MatrixRainProps {
  side: "left" | "right";
  width?: number;
}

export default function MatrixRain({ side, width = 120 }: MatrixRainProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const fontSize = 13;
    let animId: number;

    const resize = () => {
      canvas.width = width;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const cols = Math.floor(width / fontSize);
    const drops: number[] = Array(cols).fill(0).map(() => Math.random() * -80);
    // Per-column opacity so columns feel independent
    const opacities: number[] = Array(cols).fill(0).map(() => 0.3 + Math.random() * 0.5);
    // Per-column speed multiplier
    const speeds: number[] = Array(cols).fill(0).map(() => 0.3 + Math.random() * 0.7);

    let frame = 0;

    const draw = () => {
      frame++;

      // Fade trail
      ctx.fillStyle = "rgba(8, 9, 10, 0.18)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.font = `${fontSize}px 'SF Mono', 'Fira Code', monospace`;

      for (let i = 0; i < drops.length; i++) {
        // Skip some frames per column based on speed to create variation
        if (frame % Math.ceil(1 / speeds[i]) !== 0 && speeds[i] < 0.7) continue;

        const y = drops[i] * fontSize;
        const x = i * fontSize;

        // Head character — bright
        const headChar = CHARS[Math.floor(Math.random() * CHARS.length)];
        ctx.fillStyle = `rgba(6, 182, 212, ${opacities[i]})`; // cyan head
        ctx.fillText(headChar, x, y);

        // Glow on head
        ctx.shadowColor = "#06b6d4";
        ctx.shadowBlur = 6;
        ctx.fillStyle = `rgba(180, 240, 255, ${opacities[i]})`;
        ctx.fillText(headChar, x, y);
        ctx.shadowBlur = 0;

        // Occasional green column instead of cyan for variety
        const colColor =
          i % 5 === 0
            ? `rgba(22, 163, 74, ${opacities[i] * 0.7})`  // green
            : i % 7 === 0
            ? `rgba(220, 38, 38, ${opacities[i] * 0.4})`  // dim red
            : `rgba(6, 182, 212, ${opacities[i] * 0.55})`; // cyan

        // Body character (slightly behind head)
        if (drops[i] > 1) {
          const bodyChar = CHARS[Math.floor(Math.random() * CHARS.length)];
          ctx.fillStyle = colColor;
          ctx.fillText(bodyChar, x, y - fontSize);
        }

        // Reset column when it goes off screen
        if (y > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
          opacities[i] = 0.25 + Math.random() * 0.5;
          speeds[i] = 0.3 + Math.random() * 0.7;
        }

        drops[i] += speeds[i];
      }

      animId = requestAnimationFrame(draw);
    };

    animId = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, [width]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: 0,
        [side]: 0,
        width,
        height: "100vh",
        pointerEvents: "none",
        zIndex: 0,
        opacity: 0.45,
        maskImage:
          side === "left"
            ? "linear-gradient(to right, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 70%, transparent 100%)"
            : "linear-gradient(to left, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 70%, transparent 100%)",
        WebkitMaskImage:
          side === "left"
            ? "linear-gradient(to right, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 70%, transparent 100%)"
            : "linear-gradient(to left, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 70%, transparent 100%)",
      }}
    />
  );
}
