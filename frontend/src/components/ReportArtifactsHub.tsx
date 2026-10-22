import React, { useState, useEffect } from "react";
import {
  FileText,
  Download,
  Eye,
  CheckCircle2,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
  FileCode,
  Globe,
  Archive,
  Table,
  X,
  ShieldCheck,
} from "lucide-react";
import {
  fetchReportArtifacts,
  fetchReportPreview,
  getReportDownloadUrl,
} from "../api/endpoints";
import type {
  ReportArtifactItem,
  ReportPreviewData,
} from "../api/endpoints";
import { cyberAudio } from "./Cyber3DBackground";
import { Card3D } from "./Card3D";

interface Props {
  incidentId: string;
  incidentTitle: string;
  isAnalyzing: boolean;
}

export function ReportArtifactsHub({ incidentId, incidentTitle, isAnalyzing }: Props) {
  const [artifacts, setArtifacts] = useState<ReportArtifactItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<ReportPreviewData | null>(null);
  const [previewFmt, setPreviewFmt] = useState<"markdown" | "html" | "json">("markdown");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"artifacts" | "preview">("artifacts");

  const loadArtifacts = async () => {
    try {
      setLoading(true);
      const data = await fetchReportArtifacts(incidentId);
      setArtifacts(data);
    } catch {
      // Artifacts might still be generating
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArtifacts();
    if (isAnalyzing) {
      const interval = setInterval(loadArtifacts, 4000);
      return () => clearInterval(interval);
    }
  }, [incidentId, isAnalyzing]);

  const handleDownload = (fmt: string) => {
    cyberAudio.playClick();
    const url = getReportDownloadUrl(incidentId, fmt);
    window.open(url, "_blank");
  };

  const handleOpenPreview = async (fmt: "markdown" | "html" | "json" = "markdown") => {
    cyberAudio.playPulse();
    setPreviewFmt(fmt);
    setPreviewLoading(true);
    try {
      const data = await fetchReportPreview(incidentId, fmt);
      setPreviewData(data);
      setActiveTab("preview");
    } catch (e) {
      console.error("Preview load error", e);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCopyContent = () => {
    if (!previewData) return;
    navigator.clipboard.writeText(previewData.content);
    setCopied(true);
    cyberAudio.playClick();
    setTimeout(() => setCopied(false), 2000);
  };

  const FORMATS = [
    {
      id: "pdf",
      name: "Executive PDF",
      desc: "Full postmortem document formatted for leadership with graphs & root cause breakdown",
      icon: FileText,
      color: "#ef4444",
      bg: "rgba(239, 68, 68, 0.12)",
    },
    {
      id: "markdown",
      name: "Engineering Markdown",
      desc: "RFC-style postmortem report with root cause, timeline, actions, and forensic evidence",
      icon: FileCode,
      color: "#6366f1",
      bg: "rgba(99, 102, 241, 0.12)",
    },
    {
      id: "html",
      name: "Interactive HTML",
      desc: "Standalone styled web report with interactive data tables and audit trail",
      icon: Globe,
      color: "#06b6d4",
      bg: "rgba(6, 182, 212, 0.12)",
    },
    {
      id: "json",
      name: "Machine JSON",
      desc: "Standardized canonical payload containing full RCA telemetry and model predictions",
      icon: Sparkles,
      color: "#10b981",
      bg: "rgba(16, 185, 129, 0.12)",
    },
    {
      id: "csv",
      name: "Metrics CSV",
      desc: "Tabular summary of service degradation, anomaly scores, and verification results",
      icon: Table,
      color: "#f59e0b",
      bg: "rgba(245, 158, 11, 0.12)",
    },
    {
      id: "zip",
      name: "Evidence ZIP Bundle",
      desc: "Sanitized forensic archive with manifests, JSONs, verification telemetry, and timeline",
      icon: Archive,
      color: "#a855f7",
      bg: "rgba(168, 85, 247, 0.12)",
    },
  ];

  return (
    <Card3D
      style={{
        marginTop: "24px",
        padding: "24px",
        background: "rgba(26, 31, 46, 0.8)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          marginBottom: "20px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          paddingBottom: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(6, 182, 212, 0.3))",
              border: "1px solid rgba(99, 102, 241, 0.4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#6366f1",
            }}
          >
            <ShieldCheck size={22} color="#06b6d4" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
              Canonical Incident Reports & Forensics
              <span
                style={{
                  fontSize: "10px",
                  padding: "2px 8px",
                  borderRadius: "10px",
                  background: "rgba(16, 185, 129, 0.15)",
                  color: "var(--success)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  fontWeight: 600,
                  letterSpacing: "0.05em",
                }}
              >
                AUTOMATED PRODUCTION
              </span>
            </h2>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "2px" }}>
              Enterprise-grade verified audit reports generated from immutable database records.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => handleOpenPreview("markdown")}
            className="btn btn-ghost"
            style={{
              fontSize: "12px",
              gap: "6px",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              background: "rgba(255, 255, 255, 0.04)",
            }}
          >
            <Eye size={14} /> Preview Report
          </button>
          <button
            onClick={loadArtifacts}
            disabled={loading}
            className="btn btn-ghost"
            style={{
              fontSize: "12px",
              gap: "6px",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              color: "var(--primary)",
            }}
          >
            <RefreshCw size={13} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>
      </div>

      {/* Format Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: "14px",
        }}
      >
        {FORMATS.map((fmt) => {
          const Icon = fmt.icon;
          const matchingArtifact = artifacts.find((a) => a.format === fmt.id);

          return (
            <div
              key={fmt.id}
              style={{
                background: "rgba(15, 20, 25, 0.55)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "12px",
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "12px",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = fmt.color;
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = `0 6px 20px ${fmt.bg}`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)";
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div
                      style={{
                        width: "30px",
                        height: "30px",
                        borderRadius: "8px",
                        background: fmt.bg,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: fmt.color,
                      }}
                    >
                      <Icon size={16} />
                    </div>
                    <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                      {fmt.name}
                    </span>
                  </div>
                  {matchingArtifact && (
                    <span
                      title="Canonical artifact ready"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px",
                        color: "var(--success)",
                        fontWeight: 600,
                      }}
                    >
                      <CheckCircle2 size={13} /> READY
                    </span>
                  )}
                </div>
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.45 }}>
                  {fmt.desc}
                </p>
              </div>

              <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                <button
                  onClick={() => handleDownload(fmt.id)}
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                    padding: "7px 12px",
                    borderRadius: "8px",
                    background: fmt.bg,
                    border: `1px solid ${fmt.color}44`,
                    color: fmt.color,
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  <Download size={13} /> Download {fmt.id.toUpperCase()}
                </button>
                {fmt.id === "markdown" && (
                  <button
                    onClick={() => handleOpenPreview("markdown")}
                    title="View inline"
                    style={{
                      padding: "7px 10px",
                      borderRadius: "8px",
                      background: "rgba(255, 255, 255, 0.06)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: "var(--text-secondary)",
                      cursor: "pointer",
                    }}
                  >
                    <Eye size={13} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Interactive Report Preview Modal */}
      {previewData && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 99999,
            background: "rgba(0, 0, 0, 0.85)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          onClick={() => setPreviewData(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "920px",
              maxWidth: "100%",
              height: "85vh",
              maxHeight: "85vh",
              background: "var(--bg-card)",
              border: "1px solid rgba(99, 102, 241, 0.5)",
              borderRadius: "16px",
              display: "flex",
              flexDirection: "column",
              boxShadow: "0 25px 60px rgba(0, 0, 0, 0.9)",
              overflow: "hidden",
              position: "relative",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "rgba(15, 20, 25, 0.7)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <FileText size={18} color="var(--primary)" />
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.95rem" }}>{previewData.filename}</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    Report ID: {previewData.report_id} • SHA-256: {previewData.checksum_sha256?.substring(0, 16)}...
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <button
                  onClick={handleCopyContent}
                  className="btn btn-ghost"
                  style={{ fontSize: "12px", gap: "6px" }}
                >
                  {copied ? <Check size={13} color="var(--success)" /> : <Copy size={13} />}
                  {copied ? "Copied!" : "Copy Markdown"}
                </button>
                <button
                  onClick={() => handleDownload(previewFmt)}
                  className="btn btn-primary"
                  style={{ fontSize: "12px", gap: "6px" }}
                >
                  <Download size={13} /> Download File
                </button>
                <button
                  onClick={() => setPreviewData(null)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "4px 8px",
                  }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "24px",
                fontFamily: "var(--font-mono, monospace)",
                fontSize: "0.82rem",
                lineHeight: 1.6,
                color: "var(--text-primary)",
                background: "#0a0d14",
                whiteSpace: "pre-wrap",
              }}
            >
              {previewData.content}
            </div>
          </div>
        </div>
      )}
    </Card3D>
  );
}
