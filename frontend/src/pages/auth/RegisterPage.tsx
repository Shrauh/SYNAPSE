import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, ShieldCheck, Check, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const rules = [
  { label: "8+ characters", test: (p: string) => p.length >= 8 },
  { label: "Uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
  { label: "Lowercase letter", test: (p: string) => /[a-z]/.test(p) },
  { label: "Number", test: (p: string) => /\d/.test(p) },
];

export default function RegisterPage() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ email: "", username: "", full_name: "", password: "", confirm_password: "" });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      await register(form);
      nav("/", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card auth-card-wide">
        <div className="auth-header">
          <div className="auth-logo"><ShieldCheck size={32} /></div>
          <h1 className="auth-title">Create account</h1>
          <p className="auth-subtitle">Join the SYNAPSE AIOps Platform</p>
        </div>

        <form onSubmit={submit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}

          <div className="form-row">
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={form.email} onChange={set("email")} placeholder="you@example.com" required className="form-input" />
            </div>
            <div className="form-group">
              <label>Username</label>
              <input type="text" value={form.username} onChange={set("username")} placeholder="john_doe" required className="form-input" pattern="[a-zA-Z0-9_]{3,32}" />
            </div>
          </div>

          <div className="form-group">
            <label>Full name <span className="optional">(optional)</span></label>
            <input type="text" value={form.full_name} onChange={set("full_name")} placeholder="John Doe" className="form-input" />
          </div>

          <div className="form-group">
            <label>Password</label>
            <div className="input-with-icon">
              <input type={showPw ? "text" : "password"} value={form.password} onChange={set("password")} placeholder="••••••••" required className="form-input" />
              <button type="button" className="pw-toggle" onClick={() => setShowPw(p => !p)}>
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {/* Password strength indicators */}
            {form.password && (
              <div className="pw-rules">
                {rules.map(r => (
                  <span key={r.label} className={`pw-rule ${r.test(form.password) ? "pw-rule-ok" : "pw-rule-fail"}`}>
                    {r.test(form.password) ? <Check size={12} /> : <X size={12} />} {r.label}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="form-group">
            <label>Confirm password</label>
            <input type="password" value={form.confirm_password} onChange={set("confirm_password")} placeholder="••••••••" required className="form-input" />
            {form.confirm_password && form.password !== form.confirm_password && (
              <span className="form-error-inline">Passwords do not match</span>
            )}
          </div>

          <button type="submit" disabled={loading} className="btn-primary btn-full">
            {loading ? <Loader2 size={16} className="spin" /> : null}
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login" className="auth-link">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
