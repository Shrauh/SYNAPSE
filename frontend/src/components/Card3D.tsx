import React, { useRef, useState } from "react";
import { cyberAudio } from "./Cyber3DBackground";

interface Card3DProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  tiltIntensity?: number;
  glowColor?: string;
  interactiveAudio?: boolean;
}

export function Card3D({
  children,
  tiltIntensity = 8,
  glowColor = "rgba(99, 102, 241, 0.25)",
  interactiveAudio = false,
  className = "",
  style = {},
  ...rest
}: Card3DProps) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [transform, setTransform] = useState("perspective(1000px) rotateX(0deg) rotateY(0deg)");
  const [glarePos, setGlarePos] = useState({ x: 50, y: 50, opacity: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -tiltIntensity;
    const rotateY = ((x - centerX) / centerX) * tiltIntensity;

    setTransform(`perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px)`);
    setGlarePos({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.15,
    });
  };

  const handleMouseEnter = () => {
    if (interactiveAudio) cyberAudio.playClick();
  };

  const handleMouseLeave = () => {
    setTransform("perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)");
    setGlarePos(prev => ({ ...prev, opacity: 0 }));
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`card3d-wrapper ${className}`}
      style={{
        position: "relative",
        transform,
        transition: "transform 0.15s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.2s ease",
        transformStyle: "preserve-3d",
        background: "rgba(26, 31, 46, 0.75)",
        backdropFilter: "blur(14px)",
        border: "1px solid rgba(100, 116, 139, 0.22)",
        borderRadius: "var(--radius-lg, 16px)",
        boxShadow: `0 8px 30px rgba(0, 0, 0, 0.35), 0 0 15px ${glowColor}`,
        overflow: "hidden",
        ...style,
      }}
      {...rest}
    >
      {/* Specular glare reflection overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background: `radial-gradient(circle at ${glarePos.x}% ${glarePos.y}%, rgba(255,255,255,0.18) 0%, transparent 60%)`,
          opacity: glarePos.opacity,
          transition: "opacity 0.2s ease",
          zIndex: 1,
        }}
      />
      <div style={{ position: "relative", zIndex: 2 }}>{children}</div>
    </div>
  );
}
