const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8004";

export async function demoLogin(
  email: string,
  password: string
): Promise<{ access_token: string; email: string }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/demo-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const message =
      data?.error?.message || data?.detail?.error?.message || "Login failed";
    throw new Error(message);
  }
  return res.json();
}

export { API_BASE };
