let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T = unknown>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRF-Token": csrf } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const payload = await response
    .json()
    .catch(() => ({ detail: "Server unavailable. Please retry." }));
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login")
      window.dispatchEvent(new Event("session-expired"));
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : "请检查输入格式 / Check the input fields",
    );
  }
  return payload as T;
}
export type User = {
  id: string;
  email: string;
  name: string;
  role: string;
  has_key: boolean;
  key_hint: string | null;
  language: "zh" | "en";
  timezone: string;
};
export type Platform = "tiktok" | "twitter" | "douyin";
export type Monitor = {
  id: string;
  platform: Platform;
  author_id: string;
  username: string;
  nickname: string;
  avatar: string;
  source_url: string;
  interval_hours: number;
  enabled: boolean;
  next_check_at: number;
  last_attempt_at: number | null;
  last_success_at: number | null;
  baseline_at: number | null;
  state: string;
  last_error: string | null;
  created_at: number;
};
export type Post = {
  id: string;
  platform: Platform;
  platform_id: string;
  monitor_id: string;
  text: string;
  kind: string;
  cover: string;
  share_url: string;
  published_at: number;
  found_at: number;
  is_new: boolean;
  read: boolean;
  asset_count: number;
  assets: Asset[];
  post_type: "original" | "quote" | "reply" | "repost";
  references: {
    kind: string;
    id: string;
    username: string;
    text: string;
    url: string;
  }[];
  author: string;
  username: string;
};
export type Asset = {
  id: string;
  kind: "image" | "video" | "animated_gif";
  mime_type: string | null;
  order: number;
  preview: string;
  downloadable: boolean;
};
export type Summary = {
  monitors: number;
  active: number;
  errors: number;
  posts: number;
  unread: number;
  worker_online: boolean;
  worker_sdk: string | null;
};
export type Run = {
  id: string;
  monitor_id: string;
  status: string;
  new_count: number;
  pages: number;
  message: string | null;
  started_at: number;
  finished_at: number;
};
export type SDK = {
  current: string;
  latest: string;
  notes: string;
  url: string;
  checked_at: number;
  available: boolean;
  can_update: boolean;
  blocked: string | null;
};
export type Job = {
  id: string;
  target: string;
  previous: string;
  state: string;
  message: string;
  created_at: number;
  finished_at: number | null;
};
