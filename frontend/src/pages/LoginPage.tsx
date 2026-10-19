import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/entries");
    } catch {
      setError("Invalid credentials. Check email and password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="brand-mark" style={{ color: "var(--accent)", marginBottom: 8 }}>
          QuillStack
        </div>
        <h1>Sign in</h1>
        <p className="lede">Editorial workspace for newsrooms and multi-brand publishers.</p>
        <div className="form-field">
          <label>Email</label>
          <input type="text" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        </div>
        <div className="form-field">
          <label>Password</label>
          <input type="text" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p style={{ color: "var(--danger)", marginBottom: 12 }}>{error}</p>}
        <button className="btn accent" type="submit" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Signing in…" : "Enter workspace"}
        </button>
      </form>
    </div>
  );
}
