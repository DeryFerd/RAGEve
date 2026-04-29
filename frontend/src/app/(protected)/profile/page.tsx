"use client";

import * as React from "react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getMe, updateProfile, changePassword, logout } from "@/lib/api/auth";
import { AuthMeResponse } from "@/lib/api/auth";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { User, Mail, Calendar, Clock, Lock, LogOut } from "lucide-react";
import styles from "./page.module.css";

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthMeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Profile edit state
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await getMe();
        setUser(data);
        setFullName(data.full_name || "");
        setEmail(data.email);
      } catch {
        // Not authenticated, redirect to login
        router.push("/login");
        return;
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [router]);

  const handleProfileUpdate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSavingProfile(true);
    try {
      const updated = await updateProfile({
        full_name: fullName,
        email: email,
      });
      setUser(updated);
      setSuccess("Profile updated successfully");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to update profile");
      }
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters long");
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSuccess("Password changed successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to change password");
      }
    } finally {
      setChangingPassword(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      router.push("/login");
    } catch (err) {
      console.error("Logout failed", err);
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner size={32} />
      </div>
    );
  }

  if (!user) {
    return null; // Redirecting
  }

  return (
    <div className={styles.container}>
      <Card>
        <CardBody>
          {/* Header with avatar */}
          <div className={styles.header}>
            <div className={styles.avatar} aria-hidden="true">
              <User size={32} />
            </div>
            <div className={styles.titleArea}>
              <h1 className={styles.title}>Profile</h1>
              <p className={styles.subtitle}>@{user.username}</p>
            </div>
          </div>

          {/* Feedback alerts */}
          {error && <div className={`${styles.alert} ${styles.alertError}`}>{error}</div>}
          {success && <div className={`${styles.alert} ${styles.alertSuccess}`}>{success}</div>}

          {/* Account Information */}
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Account Information</h2>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Username</span>
                <span className={styles.infoValue}>
                  <User size={14} color="var(--text-muted)" />
                  {user.username}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Email</span>
                <div className={styles.emailRow}>
                  <span className={styles.infoValue}>
                    <Mail size={14} color="var(--text-muted)" />
                    {user.email}
                  </span>
                  <Badge variant={user.email_verified ? "success" : "warning"}>
                    {user.email_verified ? "Verified" : "Unverified"}
                  </Badge>
                </div>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Full Name</span>
                <span className={styles.infoValue}>
                  <User size={14} color="var(--text-muted)" />
                  {user.full_name || "(not set)"}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Member since</span>
                <span className={styles.infoValue}>
                  <Calendar size={14} color="var(--text-muted)" />
                  {user.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Last login</span>
                <span className={styles.infoValue}>
                  <Clock size={14} color="var(--text-muted)" />
                  {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "N/A"}
                </span>
              </div>
            </div>
          </div>

          {/* Edit Profile */}
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Edit Profile</h2>
            <form onSubmit={handleProfileUpdate} className={styles.form}>
              <Input
                label="Full Name"
                id="fullName"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={savingProfile}
                placeholder="Enter your full name"
              />
              <Input
                label="Email"
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={savingProfile}
                hint="Changing email will require re-verification."
                placeholder="you@example.com"
              />
              <Button type="submit" disabled={savingProfile} loading={savingProfile}>
                Save Changes
              </Button>
            </form>
          </div>

          {/* Change Password */}
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>
              <Lock size={14} />
              Change Password
            </h2>
            <form onSubmit={handlePasswordChange} className={styles.form}>
              <Input
                label="Current Password"
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={changingPassword}
                required
              />
              <Input
                label="New Password"
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={changingPassword}
                required
                minLength={8}
                hint="At least 8 characters"
              />
              <Input
                label="Confirm New Password"
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={changingPassword}
                required
              />
              <Button type="submit" disabled={changingPassword} loading={changingPassword}>
                Change Password
              </Button>
            </form>
          </div>

          {/* Logout */}
          <div className={styles.logoutSection}>
            <Button variant="danger" fullWidth onClick={handleLogout}>
              <LogOut size={16} />
              Log Out
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
