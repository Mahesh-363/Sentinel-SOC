"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchApi } from "./api";

export interface OrgInfo {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface UserInfo {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin?: boolean;
  must_change_password?: boolean;
}

interface AuthContextType {
  user: UserInfo | null;
  token: string | null;
  organizations: OrgInfo[];
  activeOrg: OrgInfo | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name: string, orgName?: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
  setActiveOrg: (org: OrgInfo) => void;
  refreshUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<OrgInfo[]>([]);
  const [activeOrg, setActiveOrgState] = useState<OrgInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("sentinel_token");
    const savedUser = localStorage.getItem("sentinel_user");
    const savedOrgs = localStorage.getItem("sentinel_orgs");
    const savedActiveOrg = localStorage.getItem("sentinel_active_org_obj");

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        if (savedOrgs) {
          const parsedOrgs: OrgInfo[] = JSON.parse(savedOrgs);
          setOrganizations(parsedOrgs);
          if (savedActiveOrg) {
            setActiveOrgState(JSON.parse(savedActiveOrg));
          } else if (parsedOrgs.length > 0) {
            setActiveOrg(parsedOrgs[0]);
          }
        }
      } catch (e) {
        logout();
      }
    }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setActiveOrg = (org: OrgInfo) => {
    setActiveOrgState(org);
    localStorage.setItem("sentinel_active_org", org.id);
    localStorage.setItem("sentinel_active_org_obj", JSON.stringify(org));
  };

  const login = async (email: string, pass: string) => {
    const res = await fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password: pass }),
    });

    const authToken = res.access_token;
    const mustChangePassword = Boolean(res.must_change_password);
    const userData: UserInfo = {
      id: res.user_id,
      email: res.email,
      full_name: res.full_name,
      is_platform_admin: Boolean(res.is_platform_admin),
      must_change_password: mustChangePassword,
    };
    const orgs: OrgInfo[] = res.organizations || [];

    setToken(authToken);
    setUser(userData);
    setOrganizations(orgs);

    localStorage.setItem("sentinel_token", authToken);
    localStorage.setItem("sentinel_user", JSON.stringify(userData));
    localStorage.setItem("sentinel_orgs", JSON.stringify(orgs));

    if (orgs.length > 0) {
      setActiveOrg(orgs[0]);
    }

    if (mustChangePassword) {
      router.push("/change-password");
    } else {
      router.push("/dashboard");
    }
  };

  const register = async (email: string, pass: string, name: string, orgName?: string) => {
    const res = await fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password: pass,
        full_name: name,
        organization_name: orgName || "Primary Security Operations",
      }),
    });

    const authToken = res.access_token;
    const userData: UserInfo = {
      id: res.user_id,
      email: res.email,
      full_name: res.full_name,
      is_platform_admin: Boolean(res.is_platform_admin),
      must_change_password: false,
    };
    const orgs: OrgInfo[] = res.organizations || [];

    setToken(authToken);
    setUser(userData);
    setOrganizations(orgs);

    localStorage.setItem("sentinel_token", authToken);
    localStorage.setItem("sentinel_user", JSON.stringify(userData));
    localStorage.setItem("sentinel_orgs", JSON.stringify(orgs));

    if (orgs.length > 0) {
      setActiveOrg(orgs[0]);
    }

    router.push("/dashboard");
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    const res = await fetchApi("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    if (res.access_token) {
      setToken(res.access_token);
      localStorage.setItem("sentinel_token", res.access_token);
    }

    if (user) {
      const updatedUser: UserInfo = {
        ...user,
        must_change_password: false,
      };
      setUser(updatedUser);
      localStorage.setItem("sentinel_user", JSON.stringify(updatedUser));
    }

    router.push("/dashboard");
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setOrganizations([]);
    setActiveOrgState(null);
    localStorage.removeItem("sentinel_token");
    localStorage.removeItem("sentinel_user");
    localStorage.removeItem("sentinel_orgs");
    localStorage.removeItem("sentinel_active_org");
    localStorage.removeItem("sentinel_active_org_obj");
    router.push("/login");
  };

  const refreshUserData = async () => {
    if (!token) return;
    try {
      const memberships = await fetchApi("/auth/memberships");
      const mappedOrgs: OrgInfo[] = memberships.map((m: any) => ({
        id: m.organization_id,
        name: m.organization_name,
        slug: m.organization_name.toLowerCase().replace(/[^a-z0-9]/g, "-"),
        role: m.role,
      }));
      setOrganizations(mappedOrgs);
      localStorage.setItem("sentinel_orgs", JSON.stringify(mappedOrgs));
    } catch {}
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        organizations,
        activeOrg,
        loading,
        login,
        register,
        changePassword,
        logout,
        setActiveOrg,
        refreshUserData,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
