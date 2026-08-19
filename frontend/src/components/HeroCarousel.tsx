import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, ArrowRight, Activity, Brain, TrendingUp, GitBranch, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";

/* ─── Real Unsplash photos — domain-matched for each slide ─── */
const SLIDES = [
  {
    /* Slide 1 — AIOps / Neural Network */
    badge: "AI-Powered Platform",
    title: "SYNAPSE",
    subtitle: "Intelligent Root Cause Analysis",
    desc: "AI-powered monitoring, causal reasoning, anomaly detection, and predictive failure analysis for cloud-native distributed systems.",
    btnLabel: "Explore Dashboard",
    btnTo: "/",
    secondBtn: "View Incidents",
    secondTo: "/incidents",
    accent: "#6366f1",
    // Neural network / AI chip — deep tech aesthetic
    photo: "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1600&q=90&fit=crop&crop=center",
    photoAlt: "AI neural network visualization",
    Icon: Activity,
  },
  {
    /* Slide 2 — Causal Inference / Root Cause Analysis */
    badge: "Causal Intelligence",
    title: "AI-Powered RCA",
    subtitle: "Identify the true source of incidents",
    desc: "Temporal Graph Networks and PC Causal Inference help detect root causes 10× faster than manual investigation.",
    btnLabel: "View RCA Reports",
    btnTo: "/incidents",
    secondBtn: "Run Simulation",
    secondTo: "/simulate",
    accent: "#8b5cf6",
    // Data analysis / graphs — purple research theme
    photo: "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1600&q=90&fit=crop&crop=center",
    photoAlt: "Causal graph analysis visualization",
    Icon: Brain,
  },
  {
    /* Slide 3 — Cloud Monitoring / Observability */
    badge: "Real-Time Observability",
    title: "Cloud Monitoring",
    subtitle: "Complete observability across services",
    desc: "Monitor system health, metrics, dependencies, and incidents in real time across your entire microservice topology.",
    btnLabel: "Open Service Graph",
    btnTo: "/graph",
    secondBtn: "Live Dashboard",
    secondTo: "/",
    accent: "#06b6d4",
    // Server room / data center — cloud infrastructure
    photo: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1600&q=90&fit=crop&crop=center",
    photoAlt: "Cloud infrastructure data center",
    Icon: Activity,
  },
  {
    /* Slide 4 — Predictive Analytics / Failure Prevention */
    badge: "Predictive Analytics",
    title: "Predictive Intelligence",
    subtitle: "Predict failures before they happen",
    desc: "AI-driven anomaly detection and predictive analytics give your team the power to act proactively, not reactively.",
    btnLabel: "Model Status",
    btnTo: "/model",
    secondBtn: "Inject Fault",
    secondTo: "/simulate",
    accent: "#10b981",
    // Analytics dashboard / real-time metrics — green tech
    photo: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1600&q=90&fit=crop&crop=center",
    photoAlt: "Predictive analytics dashboard",
    Icon: TrendingUp,
  },
  {
    /* Slide 5 — Service Topology / Microservices */
    badge: "Service Topology",
    title: "Dynamic Service Mapping",
    subtitle: "Visualize complex service relationships",
    desc: "Understand dependencies and instantly identify cascading failures across 10+ interconnected microservices.",
    btnLabel: "Explore Causal Graph",
    btnTo: "/graph",
    secondBtn: "View Incidents",
    secondTo: "/incidents",
    accent: "#f59e0b",
    // Network topology / interconnected systems — amber/gold
    photo: "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1600&q=90&fit=crop&crop=center",
    photoAlt: "Network topology microservices visualization",
    Icon: GitBranch,
  },
];

export function HeroCarousel() {
  const [current, setCurrent] = useState(0);
  const [direction, setDirection] = useState(1);
  const [paused, setPaused] = useState(false);
  const navigate = useNavigate();

  const go = useCallback((idx: number, dir = 1) => {
    setDirection(dir);
    setCurrent((idx + SLIDES.length) % SLIDES.length);
  }, []);

  // Auto-advance every 5.5 seconds unless paused
  useEffect(() => {
    if (paused) return;
    const t = setInterval(() => go(current + 1, 1), 5500);
    return () => clearInterval(t);
  }, [current, go, paused]);

  const slide = SLIDES[current];

  const variants = {
    enter: (d: number) => ({ x: d > 0 ? "6%" : "-6%", opacity: 0, scale: 1.02 }),
    center: { x: 0, opacity: 1, scale: 1 },
    exit:  (d: number) => ({ x: d > 0 ? "-6%" : "6%", opacity: 0, scale: 0.98 }),
  };

  const contentVariants = {
    enter: (d: number) => ({ x: d > 0 ? 40 : -40, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit:  (d: number) => ({ x: d > 0 ? -40 : 40, opacity: 0 }),
  };

  return (
    <div
      className="hero-carousel"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* ── Full-bleed photo background with animated zoom ── */}
      <AnimatePresence custom={direction} initial={false} mode="sync">
        <motion.div
          key={`photo-${current}`}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1] }}
          style={{
            position: "absolute", inset: 0, zIndex: 0,
            backgroundImage: `url(${slide.photo})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
      </AnimatePresence>

      {/* ── Multi-layer overlay — left darkening + brand gradient ── */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 1,
        background: `
          linear-gradient(to right,
            rgba(4,4,15,0.92) 0%,
            rgba(4,4,15,0.80) 40%,
            rgba(4,4,15,0.45) 65%,
            rgba(4,4,15,0.15) 100%
          ),
          linear-gradient(to top,
            rgba(4,4,15,0.65) 0%,
            transparent 50%
          )
        `,
      }} />

      {/* ── Accent colour tint tied to slide ── */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 1,
        background: `radial-gradient(ellipse at 20% 50%, ${slide.accent}18 0%, transparent 60%)`,
        transition: "background 0.8s ease",
      }} />

      {/* ── Slide counter ── */}
      <div style={{
        position: "absolute", top: 18, right: 22, zIndex: 10,
        fontSize: "0.68rem", fontWeight: 700,
        color: "rgba(255,255,255,0.5)",
        fontFamily: "JetBrains Mono, monospace",
        letterSpacing: "0.12em",
      }}>
        {String(current + 1).padStart(2, "0")} / {String(SLIDES.length).padStart(2, "0")}
      </div>

      {/* ── Slide content ── */}
      <AnimatePresence custom={direction} initial={false} mode="wait">
        <motion.div
          key={`content-${current}`}
          custom={direction}
          variants={contentVariants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.45, ease: "easeOut" }}
          className="hero-slide-content"
          style={{ position: "relative", zIndex: 2 }}
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="hero-badge"
            style={{
              borderColor: `${slide.accent}50`,
              color: slide.accent,
              background: `${slide.accent}18`,
              backdropFilter: "blur(8px)",
            }}
          >
            <slide.Icon size={11} />
            {slide.badge}
          </motion.div>

          {/* Title */}
          <motion.h1
            className="hero-title"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            style={{ textShadow: `0 2px 24px rgba(0,0,0,0.6), 0 0 40px ${slide.accent}28` }}
          >
            {slide.title === "SYNAPSE" ? (
              <span className="gradient-text">{slide.title}</span>
            ) : slide.title}
          </motion.h1>

          {/* Subtitle */}
          <motion.div
            className="hero-subtitle"
            style={{ color: slide.accent }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            {slide.subtitle}
          </motion.div>

          {/* Description */}
          <motion.p
            className="hero-desc"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            {slide.desc}
          </motion.p>

          {/* Buttons */}
          <motion.div
            style={{ display: "flex", gap: 12, flexWrap: "wrap" }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32 }}
          >
            <button
              className="hero-btn"
              style={{
                background: `linear-gradient(135deg, ${slide.accent}ee, ${slide.accent}bb)`,
                boxShadow: `0 0 28px ${slide.accent}50, 0 4px 16px rgba(0,0,0,0.3)`,
              }}
              onClick={() => navigate(slide.btnTo)}
            >
              {slide.btnLabel} <ArrowRight size={14} />
            </button>
            <button
              className="hero-btn hero-btn-ghost"
              onClick={() => navigate(slide.secondTo)}
            >
              {slide.secondBtn}
            </button>
          </motion.div>
        </motion.div>
      </AnimatePresence>

      {/* ── Photo credit watermark (bottom-right) ── */}
      <div style={{
        position: "absolute", bottom: 44, right: 18, zIndex: 5,
        fontSize: "0.6rem", color: "rgba(255,255,255,0.25)",
        fontFamily: "JetBrains Mono, monospace",
        letterSpacing: "0.04em",
      }}>
        Photo · Unsplash
      </div>

      {/* ── Prev / Next nav buttons ── */}
      <button
        className="hero-nav-btn prev"
        onClick={() => { go(current - 1, -1); setPaused(false); }}
        aria-label="Previous slide"
      >
        <ChevronLeft size={18} />
      </button>
      <button
        className="hero-nav-btn next"
        onClick={() => { go(current + 1, 1); setPaused(false); }}
        aria-label="Next slide"
      >
        <ChevronRight size={18} />
      </button>

      {/* ── Dot indicators ── */}
      <div className="hero-dots">
        {SLIDES.map((s, i) => (
          <button
            key={i}
            className={`hero-dot${i === current ? " active" : ""}`}
            style={i === current ? { background: slide.accent, width: 22 } : undefined}
            onClick={() => { go(i, i > current ? 1 : -1); setPaused(false); }}
            aria-label={`Go to slide ${i + 1}: ${s.badge}`}
          />
        ))}
      </div>

      {/* ── Progress bar ── */}
      {!paused && (
        <motion.div
          key={`progress-${current}`}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 5.5, ease: "linear" }}
          style={{
            position: "absolute", bottom: 0, left: 0, right: 0,
            height: 2, background: slide.accent, opacity: 0.6,
            transformOrigin: "left center", zIndex: 10,
          }}
        />
      )}
    </div>
  );
}
