"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api/auth";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import styles from "./page.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
      router.push("/");
      router.refresh();
    } catch (err: unknown) {
      if (err instanceof Error) {
        // Check for email verification error
        if (err.message.includes("verify your email")) {
          setError("Please verify your email before logging in. Check your inbox or request a new verification link.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Login failed. Please check your credentials.");
      }
      setLoading(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCardWrapper}>
        <Card>
          <CardHeader title="Login" />
          <CardBody>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {error && (
                <div style={{
                  padding: 'var(--space-3)',
                  backgroundColor: 'var(--bg-elevated)',
                  color: 'var(--text-primary)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--text-sm)',
                  border: '1px solid var(--border)'
                }}>
                  {error}
                </div>
              )}
              <Input
                id="email"
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                placeholder="you@example.com"
                autoComplete="email"
              />
              <div style={{ position: 'relative' }}>
                <Input
                  id="password"
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={styles.passwordToggle}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'calc(-1 * var(--space-2))' }}>
                <Link href="/forgot-password" className={styles.forgotPassword}>
                  Forgot password?
                </Link>
              </div>
              <Button type="submit" fullWidth loading={loading} disabled={loading}>
                Log In
              </Button>
            </form>
          </CardBody>
          <div style={{ padding: 'var(--space-3)', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'center' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)', margin: 0 }}>
              Don&apos;t have an account?{" "}
              <Link href="/register" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 }}>
                Register
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
