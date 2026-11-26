const DEMO_TOKEN_KEY = "invoiceai_demo_token";
const DEMO_EMAIL_KEY = "invoiceai_demo_email";

export function isDemoLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(localStorage.getItem(DEMO_TOKEN_KEY));
}

export function getDemoEmail(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(DEMO_EMAIL_KEY);
}

export function setDemoSession(token: string, email: string): void {
  localStorage.setItem(DEMO_TOKEN_KEY, token);
  localStorage.setItem(DEMO_EMAIL_KEY, email);
}

export function clearDemoSession(): void {
  localStorage.removeItem(DEMO_TOKEN_KEY);
  localStorage.removeItem(DEMO_EMAIL_KEY);
}

export const DEMO_CREDENTIALS = {
  email: "demo@invoiceai.local",
  password: "demo",
} as const;

/** Seeded demo users (password: demo for all). */
export const DEMO_USERS = [
  { email: "demo@invoiceai.local", role: "admin", label: "Admin / Finance Manager" },
  { email: "reviewer@invoiceai.local", role: "reviewer", label: "Reviewer" },
  { email: "approver@invoiceai.local", role: "approver", label: "Approver" },
  { email: "staff@invoiceai.local", role: "staff", label: "Staff" },
] as const;
