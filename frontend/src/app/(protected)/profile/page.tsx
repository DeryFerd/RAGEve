"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getMe, updateProfile, changePassword, logout } from "@/lib/api/auth";
import { AuthMeResponse } from "@/lib/api/auth";
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
      } catch (err) {
        // Not authenticated, redirect to login
        router.push("/login");
        return;
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [router]);

  const handleProfileUpdate = async (e: React.FormEvent) => {
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

  const handlePasswordChange = async (e: React.FormEvent) => {
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
    return <div className={styles.container}>Loading...</div>;
  }

  if (!user) {
    return null; // Redirecting
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Profile</h1>

        {error && <div className={styles.error}>{error}</div>}
        {success && <div className={styles.success}>{success}</div>}

        <section className={styles.section}>
          <h2>Account Information</h2>
          <div className={styles.infoGrid}>
            <div>
              <strong>Username:</strong> {user.username}
            </div>
            <div>
              <strong>Email:</strong> {user.email} {user.email_verified ? "(verified)" : "(unverified)"}
            </div>
            <div>
              <strong>Full Name:</strong> {user.full_name || "(not set)"}
            </div>
            <div>
              <strong>Member since:</strong> {user.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
            </div>
            <div>
              <strong>Last login:</strong> {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "N/A"}
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <h2>Edit Profile</h2>
          <form onSubmit={handleProfileUpdate} className={styles.form}>
            <div className={styles.field}>
              <label htmlFor="fullName">Full Name</label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={savingProfile}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={savingProfile}
              />
              <small>Changing email will require re-verification.</small>
            </div>
            <button type="submit" disabled={savingProfile} className={styles.button}>
              {savingProfile ? "Saving..." : "Save Changes"}
            </button>
          </form>
        </section>

        <section className={styles.section}>
          <h2>Change Password</h2>
          <form onSubmit={handlePasswordChange} className={styles.form}>
            <div className={styles.field}>
              <label htmlFor="currentPassword">Current Password</label>
              <input
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                disabled={changingPassword}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="newPassword">New Password</label>
              <input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                disabled={changingPassword}
                minLength={8}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="confirmPassword">Confirm New Password</label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={changingPassword}
              />
            </div>
            <button type="submit" disabled={changingPassword} className={styles.button}>
              {changingPassword ? "Changing..." : "Change Password"}
            </button>
          </form>
        </section>

        <section className={styles.section}>
          <button onClick={handleLogout} className={styles.logoutButton}>
            Log Out
          </button>
        </section>
      </div>
    </div>
  );
}
