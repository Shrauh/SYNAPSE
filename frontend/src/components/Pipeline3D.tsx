import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface PipelineStage {
  id: string;
  label: string;
  sublabel: string;
  status: "pending" | "active" | "done" | "error";
  duration?: string;
  detail?: string;
}

interface Pipeline3DProps {
  stages: PipelineStage[];
}

/* ── Particle canvas behind pipeline ── */
function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf: number;
    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;
    canvas.width = W;
    canvas.height = H;

    const particles = Array.from({ length: 40 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.5 + 0.15,
    }));

    function draw() {
      ctx!.clearRect(0, 0, W, H);
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(124,58,237,${p.alpha})`;
        ctx!.fill();
      });
      // Draw subtle connecting lines between near particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 80) {
            ctx!.beginPath();
            ctx!.moveTo(particles[i].x, particles[i].y);
            ctx!.lineTo(particles[j].x, particles[j].y);
            ctx!.strokeStyle = `rgba(124,58,237,${0.12 * (1 - dist / 80)})`;
            ctx!.lineWidth = 0.5;
            ctx!.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute", inset: 0, width: "100%", height: "100%",
        pointerEvents: "none", borderRadius: "inherit",
      }}
    />
  );
}

/* ── Animated connector between stages ── */
function Connector({ status }: { status: "pending" | "active" | "done" | "error" }) {
  const color =
    status === "done"   ? "var(--status-healthy)" :
    status === "active" ? "var(--accent-violet)"  :
    status === "error"  ? "var(--status-critical)" :
    "var(--border)";

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 28, position: "relative" }}>
      <div style={{
        width: 2, height: "100%",
        background: color,
        transition: "background 0.6s ease",
        position: "relative",
        overflow: "hidden",
      }}>
        {status === "active" && (
          <motion.div
            style={{
              position: "absolute", top: 0, left: 0, right: 0,
              height: "30%",
              background: "linear-gradient(to bottom, transparent, var(--accent-violet), transparent)",
            }}
            animate={{ y: ["-100%", "400%"] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          />
        )}
      </div>
    </div>
  );
}

/* ── Icon for each stage ── */
function StageIcon({ id, status }: { id: string; status: PipelineStage["status"] }) {
  const glowColor =
    status === "done"   ? "rgba(16,185,129,0.4)"  :
    status === "active" ? "rgba(124,58,237,0.5)"   :
    status === "error"  ? "rgba(239,68,68,0.4)"    :
    "transparent";

  const bg =
    status === "done"   ? "linear-gradient(135deg,#064e3b,#10b981)" :
    status === "active" ? "linear-gradient(135deg,#4c1d95,#7c3aed)" :
    status === "error"  ? "linear-gradient(135deg,#7f1d1d,#ef4444)" :
    "var(--bg-elevated)";

  const icons: Record<string, string> = {
    ingestion:  "▤",
    gnn:        "◈",
    causal:     "⬡",
    llm:        "◇",
    severity:   "◬",
    recovery:   "◉",
  };

  return (
    <motion.div
      style={{
        width: 38, height: 38,
        borderRadius: 10,
        background: bg,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
        fontSize: "1rem",
        color: status === "pending" ? "var(--text-muted)" : "white",
        boxShadow: status !== "pending" ? `0 0 18px ${glowColor}` : "none",
        transition: "all 0.5s ease",
        fontFamily: "monospace",
        fontWeight: 700,
      }}
      animate={status === "active" ? { scale: [1, 1.08, 1] } : { scale: 1 }}
      transition={{ duration: 1.5, repeat: status === "active" ? Infinity : 0 }}
    >
      {status === "done"   ? "✓" :
       status === "error"  ? "✕" :
       status === "active" ? (icons[id] ?? "◈") :
       (icons[id] ?? "◈")}
    </motion.div>
  );
}

export function Pipeline3D({ stages }: Pipeline3DProps) {
  return (
    <div style={{
      position: "relative",
      background: "var(--bg-elevated)",
      border: "1px solid var(--border)",
      borderRadius: 16,
      padding: "1.5rem",
      overflow: "hidden",
    }}>
      <ParticleCanvas />

      <div style={{ position: "relative", zIndex: 1 }}>
        {stages.map((stage, idx) => (
          <div key={stage.id}>
            {/* Stage Card */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.08, duration: 0.4 }}
            >
              <div
                className={`pipeline-step-card pipeline-3d-card ${stage.status}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                  padding: "14px 16px",
                  borderRadius: 12,
                  border: `1px solid ${
                    stage.status === "done"   ? "rgba(16,185,129,0.3)"  :
                    stage.status === "active" ? "rgba(124,58,237,0.45)" :
                    stage.status === "error"  ? "rgba(239,68,68,0.3)"   :
                    "var(--border)"
                  }`,
                  background:
                    stage.status === "done"   ? "rgba(16,185,129,0.05)"  :
                    stage.status === "active" ? "rgba(124,58,237,0.08)"  :
                    stage.status === "error"  ? "rgba(239,68,68,0.06)"   :
                    "var(--bg-card)",
                  boxShadow:
                    stage.status === "active" ? "0 0 24px rgba(124,58,237,0.15), inset 0 1px 0 rgba(255,255,255,0.05)" :
                    stage.status === "done"   ? "0 0 16px rgba(16,185,129,0.08)" :
                    "none",
                  transition: "all 0.5s ease",
                  position: "relative",
                  overflow: "hidden",
                  // 3D tilt effect using CSS perspective
                  transform: stage.status === "active" ? "perspective(600px) rotateX(1deg) translateY(-1px)" : "none",
                }}
              >
                {/* Shimmer sweep on active */}
                {stage.status === "active" && (
                  <motion.div
                    style={{
                      position: "absolute", inset: 0,
                      background: "linear-gradient(105deg, transparent 40%, rgba(124,58,237,0.08) 50%, transparent 60%)",
                      pointerEvents: "none",
                    }}
                    animate={{ x: ["-100%", "200%"] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear", repeatDelay: 0.5 }}
                  />
                )}

                <StageIcon id={stage.id} status={stage.status} />

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: "0.82rem",
                    fontWeight: 700,
                    color: stage.status === "pending" ? "var(--text-muted)" : "var(--text-primary)",
                    marginBottom: 2,
                    letterSpacing: "-0.01em",
                  }}>
                    {stage.label}
                  </div>
                  <div style={{
                    fontSize: "0.72rem",
                    color: "var(--text-muted)",
                    fontFamily: "JetBrains Mono",
                  }}>
                    {stage.status === "active" ? (
                      <motion.span
                        animate={{ opacity: [1, 0.4, 1] }}
                        transition={{ duration: 1.2, repeat: Infinity }}
                      >
                        Processing...
                      </motion.span>
                    ) : stage.detail ?? stage.sublabel}
                  </div>
                </div>

                {/* Right side: duration or status indicator */}
                <div style={{ flexShrink: 0, textAlign: "right" }}>
                  {stage.status === "done" && stage.duration && (
                    <span style={{
                      fontSize: "0.68rem",
                      fontFamily: "JetBrains Mono",
                      color: "var(--status-healthy)",
                      background: "rgba(16,185,129,0.1)",
                      padding: "2px 8px",
                      borderRadius: 4,
                      border: "1px solid rgba(16,185,129,0.2)",
                    }}>
                      {stage.duration}
                    </span>
                  )}
                  {stage.status === "active" && (
                    <motion.div
                      style={{
                        width: 8, height: 8, borderRadius: "50%",
                        background: "var(--accent-violet)",
                        boxShadow: "0 0 8px var(--accent-violet)",
                      }}
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    />
                  )}
                  {stage.status === "error" && (
                    <span style={{
                      fontSize: "0.68rem",
                      color: "var(--status-critical)",
                      fontFamily: "JetBrains Mono",
                    }}>
                      Failed
                    </span>
                  )}
                  {stage.status === "pending" && (
                    <span style={{
                      fontSize: "0.68rem",
                      color: "var(--text-muted)",
                      fontFamily: "JetBrains Mono",
                    }}>
                      Pending
                    </span>
                  )}
                </div>
              </div>
            </motion.div>

            {/* Connector between stages */}
            {idx < stages.length - 1 && (
              <Connector status={
                stages[idx + 1].status === "done"   ? "done"    :
                stages[idx + 1].status === "active"  ? "active"  :
                stage.status === "done"              ? "pending" :
                "pending"
              } />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
