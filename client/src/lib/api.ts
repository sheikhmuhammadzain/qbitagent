export type ConnectRequest = {
  server_name: string;
  model?: string;
};

export type ConnectResponse = {
  status: string;
  server: string;
  model: string;
  tools: { name: string; description?: string }[];
  tool_count: number;
};

export type StatusResponse = {
  connected: boolean;
  server?: string | null;
  model?: string | null;
  tools?: { name: string; description?: string }[];
  error?: string;
};

export type UploadResponse = {
  status: string;
  database_id: string;
  database_name: string;
  row_count?: number;
  total_rows?: number;
  tables?: { name: string; row_count: number }[];
  message: string;
};

export type Database = {
  id: string;
  name: string;
  original_file: string;
  tables: { name: string; row_count: number }[];
  size_bytes: number;
  uploaded_at: string;
  is_active: boolean;
};

export type DatabasesResponse = {
  databases: Database[];
  active_database_id?: string | null;
};

export type DatabaseInfoResponse = {
  id: string;
  name: string;
  tables: {
    name: string;
    row_count: number;
    columns: {
      name: string;
      type: string;
      nullable: boolean;
      primary_key: boolean;
    }[];
  }[];
  size_bytes: number;
  uploaded_at: string;
};

export type SwitchDatabaseResponse = {
  status: string;
  database_name: string;
  database_id: string;
  tables?: { name: string }[];
};

const API_BASE_RAW = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

const normalizeBase = (base: string | undefined | null): string => {
  const b = (base ?? "").trim();
  if (!b) return "/api";
  // If absolute URL, return without trailing slash
  if (/^https?:\/\//i.test(b)) return b.replace(/\/$/, "");
  // Ensure leading slash and no trailing slash
  const withLeading = b.startsWith("/") ? b : `/${b}`;
  return withLeading.replace(/\/$/, "");
};

const API_BASE = normalizeBase(API_BASE_RAW);

const toUrl = (path: string) => {
  const p = path.startsWith("/") ? path : `/${path}`;
  // Absolute base
  if (/^https?:\/\//i.test(API_BASE)) return `${API_BASE}${p}`;
  // Relative base (same origin)
  return `${API_BASE}${p}`;
};

export const api = {
  async status(): Promise<StatusResponse> {
    const res = await fetch(toUrl("/status"), { credentials: "include" });
    if (!res.ok && res.status !== 401) throw new Error(`Status check failed: ${res.status}`);
    if (res.status === 401) return { connected: false, server: null, model: null, tools: [], conversation_length: 0 };
    return res.json();
  },
  async servers(): Promise<{ servers: string[]; count: number }> {
    const res = await fetch(toUrl("/servers"), { credentials: "include" });
    if (res.status === 401) return { servers: [], count: 0 };
    if (!res.ok) throw new Error(`Failed to load servers: ${res.status}`);
    return res.json();
  },
  async models(): Promise<{ models: string[]; count: number }> {
    const res = await fetch(toUrl("/models"), { credentials: "include" });
    if (res.status === 401) return { models: [], count: 0 };
    if (!res.ok) throw new Error(`Failed to load models: ${res.status}`);
    return res.json();
  },
  async connect(body: ConnectRequest): Promise<ConnectResponse> {
    const res = await fetch(toUrl("/connect"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      // Backend expects only server_name; model is fixed server-side
      body: JSON.stringify({ server_name: body.server_name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Connection failed");
    return data;
  },
  async disconnect(): Promise<{ status: string; message?: string }> {
    const res = await fetch(toUrl("/disconnect"), { method: "POST", credentials: "include" });
    return res.json();
  },

  // --- Auth ---
  async signup(username: string, password: string): Promise<{ status: string; username: string }> {
    const res = await fetch(toUrl("/auth/signup"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Signup failed");
    return data;
  },
  async signin(username: string, password: string): Promise<{ status: string; username: string }> {
    const res = await fetch(toUrl("/auth/signin"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Signin failed");
    return data;
  },
  async signout(): Promise<{ status: string }> {
    const res = await fetch(toUrl("/auth/signout"), { method: "POST", credentials: "include" });
    return res.json();
  },
  async me(): Promise<{ username?: string | null }> {
    const res = await fetch(toUrl("/auth/me"), { credentials: "include" });
    return res.json();
  },
  async clear(): Promise<{ status: string; message?: string }> {
    const res = await fetch(toUrl("/clear"), { method: "POST", credentials: "include" });
    return res.json();
  },
  async history(limit = 50): Promise<{ messages: { role: string; content: string }[] }> {
    const res = await fetch(toUrl(`/history?limit=${limit}`), { credentials: "include" });
    return res.json();
  },
  streamChat(message: string, handlers: {
    onEvent: (data: any) => void;
    onError?: (err: any) => void;
    onDone?: () => void;
  }) {
    const url = new URL(toUrl("/chat/stream"), window.location.origin);
    url.searchParams.set("message", message);

    const es = new EventSource(url.toString());

    es.addEventListener("message", (evt) => {
      try {
        const data = JSON.parse((evt as MessageEvent).data);
        handlers.onEvent(data);
        if (data?.type === "done") {
          es.close();
          handlers.onDone?.();
        }
      } catch (e) {
        console.error("SSE parse error", e);
      }
    });

    es.onerror = (err) => {
      try { es.close(); } catch {}
      handlers.onError?.(err);
    };

    return {
      close: () => {
        try { es.close(); } catch {}
      },
      raw: es,
    };
  },

  // File upload and database management
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(toUrl("/upload"), {
      method: "POST",
      credentials: "include",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    return data;
  },

  async listDatabases(): Promise<DatabasesResponse> {
    const res = await fetch(toUrl("/databases"), { credentials: "include" });
    if (res.status === 401) return { databases: [], active_database_id: null };
    if (!res.ok) throw new Error(`Failed to list databases: ${res.status}`);
    return res.json();
  },

  async switchDatabase(databaseId: string): Promise<SwitchDatabaseResponse> {
    const res = await fetch(toUrl("/switch-database"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ database_id: databaseId }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to switch database");
    return data;
  },

  async getDatabaseInfo(databaseId: string): Promise<DatabaseInfoResponse> {
    const res = await fetch(toUrl(`/database/${databaseId}/info`), { credentials: "include" });
    if (!res.ok) throw new Error(`Failed to get database info: ${res.status}`);
    return res.json();
  },

  async deleteDatabase(databaseId: string): Promise<{ status: string; message: string }> {
    const res = await fetch(toUrl(`/database/${databaseId}`), {
      method: "DELETE",
      credentials: "include",
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to delete database");
    return data;
  },
};
