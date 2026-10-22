import React, { useEffect, useRef, useState, createContext, useContext } from "react";

// ── Cyber Sound Effects via Web Audio API (Zero dependencies) ──────────────────
class CyberAudioEngine {
  private ctx: AudioContext | null = null;
  public enabled: boolean = true;

  constructor() {
    const saved = localStorage.getItem("synapse_audio_enabled");
    this.enabled = saved !== null ? saved === "true" : true;
  }

  private initCtx() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  public setEnabled(val: boolean) {
    this.enabled = val;
    localStorage.setItem("synapse_audio_enabled", String(val));
  }

  public playClick() {
    if (!this.enabled) return;
    try {
      this.initCtx();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(800, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.05);
      gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.05);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.05);
    } catch {}
  }

  public playPulse() {
    if (!this.enabled) return;
    try {
      this.initCtx();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(320, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(640, this.ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.05, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.12);
    } catch {}
  }

  public playAlert() {
    if (!this.enabled) return;
    try {
      this.initCtx();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(520, this.ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(380, this.ctx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.06, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.2);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.2);
    } catch {}
  }
}

export const cyberAudio = new CyberAudioEngine();

interface CyberContextType {
  theme: "neural" | "topology" | "minimal";
  setTheme: (t: "neural" | "topology" | "minimal") => void;
  particlesEnabled: boolean;
  setParticlesEnabled: (p: boolean) => void;
  soundEnabled: boolean;
  setSoundEnabled: (s: boolean) => void;
  playClick: () => void;
  playPulse: () => void;
  playAlert: () => void;
}

const CyberContext = createContext<CyberContextType>({
  theme: "neural",
  setTheme: () => {},
  particlesEnabled: true,
  setParticlesEnabled: () => {},
  soundEnabled: true,
  setSoundEnabled: () => {},
  playClick: () => {},
  playPulse: () => {},
  playAlert: () => {},
});

export const useCyberTheme = () => useContext(CyberContext);

export function Cyber3DProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<"neural" | "topology" | "minimal">(() => {
    return (localStorage.getItem("synapse_3d_theme") as any) || "neural";
  });
  const [particlesEnabled, setParticlesEnabled] = useState<boolean>(() => {
    const s = localStorage.getItem("synapse_particles");
    return s !== null ? s === "true" : true;
  });
  const [soundEnabled, setSoundEnabledState] = useState<boolean>(cyberAudio.enabled);

  const handleSetTheme = (t: "neural" | "topology" | "minimal") => {
    setTheme(t);
    localStorage.setItem("synapse_3d_theme", t);
    cyberAudio.playPulse();
  };

  const handleSetParticles = (p: boolean) => {
    setParticlesEnabled(p);
    localStorage.setItem("synapse_particles", String(p));
    cyberAudio.playClick();
  };

  const handleSetSound = (s: boolean) => {
    cyberAudio.setEnabled(s);
    setSoundEnabledState(s);
    if (s) cyberAudio.playClick();
  };

  return (
    <CyberContext.Provider
      value={{
        theme,
        setTheme: handleSetTheme,
        particlesEnabled,
        setParticlesEnabled: handleSetParticles,
        soundEnabled,
        setSoundEnabled: handleSetSound,
        playClick: () => cyberAudio.playClick(),
        playPulse: () => cyberAudio.playPulse(),
        playAlert: () => cyberAudio.playAlert(),
      }}
    >
      {children}
    </CyberContext.Provider>
  );
}

export function Cyber3DBackground() {
  const { theme, particlesEnabled } = useCyberTheme();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Mouse Parallax 3D Effect
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const { innerWidth, innerHeight } = window;
      const x = (e.clientX / innerWidth - 0.5) * 2; // -1 to +1
      const y = (e.clientY / innerHeight - 0.5) * 2;
      setMousePos({ x, y });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // Canvas Particles & Neural Synapse Simulation
  useEffect(() => {
    if (!particlesEnabled) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", handleResize);

    const PARTICLE_COUNT = 65;
    const particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.7,
      vy: (Math.random() - 0.5) * 0.7,
      radius: Math.random() * 2 + 1.2,
      baseAlpha: Math.random() * 0.5 + 0.3,
      color: Math.random() > 0.5 ? "rgba(6, 182, 212, " : "rgba(168, 85, 247, ",
    }));

    let mouseX = -1000;
    let mouseY = -1000;
    const handleCanvasMouse = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    window.addEventListener("mousemove", handleCanvasMouse, { passive: true });

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Update & Draw Particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Draw particle node
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}${p.baseAlpha})`;
        ctx.shadowColor = p.color.includes("182") ? "#06b6d4" : "#a855f7";
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Connect near particles
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            const alpha = (1 - dist / 120) * 0.22;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }

        // Synaptic filament to mouse cursor
        const dmx = p.x - mouseX;
        const dmy = p.y - mouseY;
        const mouseDist = Math.sqrt(dmx * dmx + dmy * dmy);
        if (mouseDist < 160) {
          const mouseAlpha = (1 - mouseDist / 160) * 0.6;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(mouseX, mouseY);
          ctx.strokeStyle = `rgba(6, 182, 212, ${mouseAlpha})`;
          ctx.lineWidth = 1.2;
          ctx.shadowColor = "#06b6d4";
          ctx.shadowBlur = 6;
          ctx.stroke();
          ctx.shadowBlur = 0;
        }
      }

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleCanvasMouse);
    };
  }, [particlesEnabled]);

  const bgImage =
    theme === "neural"
      ? "/images/synapse_3d_cyber_bg.jpg"
      : theme === "topology"
      ? "/images/synapse_3d_topology.jpg"
      : null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        overflow: "hidden",
        background: "var(--bg-primary)",
      }}
    >
      {/* 3D Parallax Image Layer */}
      {bgImage && (
        <div
          style={{
            position: "absolute",
            inset: "-40px",
            backgroundImage: `url(${bgImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center center",
            opacity: 0.22,
            filter: "brightness(0.9) contrast(1.15) saturate(1.2)",
            transform: `perspective(1000px) rotateY(${mousePos.x * 2.5}deg) rotateX(${-mousePos.y * 2.5}deg) translate3d(${mousePos.x * 12}px, ${mousePos.y * 12}px, 0)`,
            transition: "transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.5s ease",
            mixBlendMode: "screen",
          }}
        />
      )}

      {/* Cyber Grid & Ambient Vignette */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 50% 30%, rgba(99, 102, 241, 0.08) 0%, rgba(15, 20, 25, 0.85) 75%, var(--bg-primary) 100%)",
        }}
      />

      {/* Interactive Particle Synapse Canvas */}
      {particlesEnabled && (
        <canvas
          ref={canvasRef}
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.85,
          }}
        />
      )}

      {/* Subtle Holographic Grid Scanline */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          opacity: 0.4,
        }}
      />
    </div>
  );
}

// ── 3D Ambience Floating Selector / Control Pill ───────────────────────────────
export function CyberControls() {
  const { theme, setTheme, particlesEnabled, setParticlesEnabled, soundEnabled, setSoundEnabled } =
    useCyberTheme();
  const [open, setOpen] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(!open)}
        title="3D Cyber Ambience & Controls"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "4px 10px",
          borderRadius: "20px",
          background: "rgba(99, 102, 241, 0.12)",
          border: "1px solid rgba(99, 102, 241, 0.3)",
          color: "var(--primary)",
          fontSize: "12px",
          fontWeight: 600,
          cursor: "pointer",
          transition: "all 0.2s",
        }}
      >
        <span style={{ fontSize: "13px" }}>✨ 3D Cyber</span>
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: "240px",
            background: "rgba(26, 31, 46, 0.95)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(99, 102, 241, 0.35)",
            borderRadius: "var(--radius-md)",
            padding: "14px",
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
            zIndex: 100,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
            3D Atmosphere & Audio
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <button
              onClick={() => setTheme("neural")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 10px",
                borderRadius: "6px",
                background: theme === "neural" ? "rgba(99, 102, 241, 0.2)" : "transparent",
                border: theme === "neural" ? "1px solid var(--primary)" : "1px solid transparent",
                color: theme === "neural" ? "#fff" : "var(--text-secondary)",
                fontSize: "12px",
                cursor: "pointer",
              }}
            >
              <span>🧠 Neural Synapse 3D</span>
              {theme === "neural" && <span>✓</span>}
            </button>

            <button
              onClick={() => setTheme("topology")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 10px",
                borderRadius: "6px",
                background: theme === "topology" ? "rgba(6, 182, 212, 0.2)" : "transparent",
                border: theme === "topology" ? "1px solid var(--accent-cyan)" : "1px solid transparent",
                color: theme === "topology" ? "#fff" : "var(--text-secondary)",
                fontSize: "12px",
                cursor: "pointer",
              }}
            >
              <span>🌐 Topology Matrix 3D</span>
              {theme === "topology" && <span>✓</span>}
            </button>

            <button
              onClick={() => setTheme("minimal")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 10px",
                borderRadius: "6px",
                background: theme === "minimal" ? "rgba(255, 255, 255, 0.1)" : "transparent",
                border: theme === "minimal" ? "1px solid var(--border)" : "1px solid transparent",
                color: theme === "minimal" ? "#fff" : "var(--text-secondary)",
                fontSize: "12px",
                cursor: "pointer",
              }}
            >
              <span>🌌 Pure Dark Cyber</span>
              {theme === "minimal" && <span>✓</span>}
            </button>
          </div>

          <div style={{ height: "1px", background: "var(--border)", margin: "4px 0" }} />

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Particle Synapses</span>
            <button
              onClick={() => setParticlesEnabled(!particlesEnabled)}
              style={{
                padding: "3px 8px",
                borderRadius: "12px",
                fontSize: "11px",
                fontWeight: 600,
                background: particlesEnabled ? "rgba(16, 185, 129, 0.2)" : "rgba(100, 116, 139, 0.2)",
                color: particlesEnabled ? "var(--success)" : "var(--text-muted)",
                border: "none",
                cursor: "pointer",
              }}
            >
              {particlesEnabled ? "ON" : "OFF"}
            </button>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Cyber Sound FX</span>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              style={{
                padding: "3px 8px",
                borderRadius: "12px",
                fontSize: "11px",
                fontWeight: 600,
                background: soundEnabled ? "rgba(99, 102, 241, 0.2)" : "rgba(100, 116, 139, 0.2)",
                color: soundEnabled ? "var(--primary)" : "var(--text-muted)",
                border: "none",
                cursor: "pointer",
              }}
            >
              {soundEnabled ? "ON" : "MUTED"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
