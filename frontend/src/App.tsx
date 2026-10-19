import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowDown,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Copy,
  ExternalLink,
  FileText,
  Globe2,
  Image,
  KeyRound,
  LayoutDashboard,
  Layers2,
  LoaderCircle,
  LogOut,
  Menu,
  Pause,
  Play,
  Plus,
  Radio,
  Radar,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Trash2,
  Video,
  X,
} from "lucide-react";
import { api, setCsrf } from "./api";
import type { Asset, Job, Monitor, Post, Run, SDK, Summary, User } from "./api";

const copy = {
  zh: {
    overview: "概览",
    monitors: "监控对象",
    updates: "更新内容",
    settings: "个人设置",
    admin: "系统管理",
    workspace: "工作空间",
    login: "登录",
    register: "创建账号",
    logout: "退出登录",
    add: "添加监控",
    search: "搜索作者或用户名",
    watchTitle: "关注创作者，及时发现下一条好内容。",
    emptyTitle: "下一条好内容，从一个关注开始。",
    emptyText:
      "粘贴 TikTok、Twitter/X 或抖音主页、作品链接，选择检查频率，让 SuperHot 替你持续关注。",
    setKey: "设置 TikHub Key",
    keyNeeded: "先连接你的数据来源",
    keyText: "每位成员使用自己的 TikHub Key，监控列表和更新内容仅自己可见。",
    now: "立即检查",
    pause: "暂停",
    resume: "恢复",
    remove: "删除",
    interval: "检查间隔",
    creator: "创作者",
    status: "状态",
    lastCheck: "最近成功检查",
    nextCheck: "下次计划",
    operations: "操作",
    noResults: "没有匹配的结果",
    hours: "小时",
    every: "每",
    pending: "等待首次检查",
    running: "正在检查",
    idle: "监控中",
    backfill: "正在补查",
    error: "需处理",
    paused: "已暂停",
    never: "尚未检查",
    save: "保存设置",
    saved: "已保存",
    cancel: "取消",
    confirm: "确认",
    close: "关闭",
    connecting: "识别中…",
    resolve: "识别作者",
    confirmAuthor: "确认作者，开始监控",
    url: "TikTok、Twitter/X 或抖音主页、作品链接",
    urlPlaceholder: "粘贴平台主页、作品链接，或抖音分享消息",
    douyin: "抖音",
    platform: "平台",
    allPlatforms: "全部平台",
    textPost: "文字",
    mixedMedia: "混合素材",
    textOnly: "纯文字作品，可使用上方按钮复制正文。",
    downloadGif: "下载动图（MP4）",
    unavailableAsset: "暂无可下载直链",
    twitterScope: "Twitter/X 当前监控原创和引用帖，不包含回复及纯转发。",
    quotedPost: "引用的帖子",
    resolveHint:
      "识别作者和定时检查会使用你的 TikHub Key，并消耗对应 API 额度。",
    baselineHint: "首次加载的作品作为历史基线，之后发布的新作品标记为更新。",
    addTitle: "添加一个值得关注的作者",
    feedTitle: "新内容，集中在这里。",
    feedText: "查看作品、复制文案，把图片和视频保存到当前电脑。",
    all: "全部作品",
    unread: "未读更新",
    readAll: "全部标为已读",
    copy: "复制文案",
    copied: "文案已复制",
    download: "下载视频",
    downloadImage: "下载图片",
    original: "查看原作品",
    noPosts: "你的内容流，即将开始。",
    noPostsText:
      "添加监控后，首次检查会加载最近作品；之后的新作品会出现在这里。",
    noUnread: "暂时没有未读更新",
    noUnreadText: "新作品到来时，这里会为你保留未读标记。",
    history: "历史作品",
    new: "新作品",
    settingsText: "你的凭据、时间和偏好，由你掌控。",
    keyHelp: "Key 在服务端加密保存，不会回显完整内容。留空表示保持原值。",
    newKey: "粘贴你的 TikHub API Key",
    deleteKey: "移除 Key",
    timezone: "展示时区",
    name: "怎么称呼你",
    email: "邮箱",
    password: "密码",
    currentPassword: "当前密码",
    newPassword: "新密码（至少 10 位）",
    changePassword: "修改密码",
    changedPassword: "密码已修改，其他设备已退出",
    invite: "团队邀请码",
    authTitle: "把注意力留给好内容。",
    authText: "一个安静、有序的信息空间。让值得关注的内容，按你的节奏到来。",
    welcome: "欢迎回来",
    signup: "开始你的工作空间",
    passwordHelp: "至少 10 位字符",
    inviteHelp: "向部署管理员获取邀请码。首位注册成员成为系统管理员。",
    hasAccount: "已经有账号？",
    noAccount: "还没有账号？",
    backHome: "回到首页",
    privacy: "每人独立 Key · 个人数据私有",
    active: "正在监控",
    total: "关注的作者",
    needAttention: "需要处理",
    recent: "最近运行记录",
    noRuns: "还没有检查记录",
    workerOnline: "后台运行中",
    workerOffline: "后台尚未连接，请检查启动器",
    overviewText: "少一点来回切换，多一点专注。",
    manage: "管理我的监控",
    viewFeed: "查看更新",
    emptyRunText: "检查时间、发现的新作品和异常情况都会记录在这里。",
    success: "检查完成",
    partial: "继续补查",
    failed: "检查失败",
    results: "条新作品",
    pages: "页请求",
    sdkTitle: "让连接保持更新。",
    sdkText: "检查官方 SDK 发布，隔离验证后切换版本。仅管理员可操作。",
    checkVersion: "检查新版本",
    current: "当前版本",
    latest: "最新正式版本",
    notChecked: "尚未检查",
    upgrade: "验证并更新",
    upgradeHint:
      "更新期间后台检查会短暂暂停。离线验证无法保证上游接口行为不变，切换后仍需观察真实任务。",
    queued: "任务已提交，启动器将处理",
    members: "团队成员",
    member: "成员",
    administrator: "管理员",
    deploymentLog: "更新记录",
    noJobs: "还没有 SDK 更新记录",
    notConfigured: "尚未设置",
    connected: "已保存",
    account: "账号与偏好",
    security: "账号安全",
    noKey: "尚未填写 Key",
    refresh: "刷新",
    deleteMonitor: "删除该作者的监控及已保存作品记录？本地下载的文件不受影响。",
    deleteKeyConfirm: "移除 Key 后，你的监控将无法继续请求 TikHub。确定移除？",
    downloadHint:
      "下载时刷新媒体地址可能产生一次 TikHub 请求；文件保存到当前电脑。",
    downloading: "正在准备下载…",
    downloadStarted: "文件已交给浏览器保存",
    noAsset: "暂未取得可下载素材",
    loading: "正在加载…",
    errorTitle: "操作未完成",
    retry: "重试",
    details: "作品详情",
    joined: "注册时间",
    language: "界面语言",
    updated: "刚刚更新",
    auto: "后台自动刷新",
    customHours: "检查间隔（小时，1–168）",
  },
  en: {
    overview: "Overview",
    monitors: "Watchlist",
    updates: "Content feed",
    settings: "Settings",
    admin: "Administration",
    workspace: "Workspace",
    login: "Log in",
    register: "Create account",
    logout: "Log out",
    add: "Add creator",
    search: "Search creators or usernames",
    watchTitle: "Follow creators. Discover their next good idea.",
    emptyTitle: "Good content starts with a follow.",
    emptyText:
      "Paste a TikTok, Twitter/X or Douyin profile or post link, choose a schedule, and let SuperHot keep an eye on it.",
    setKey: "Connect TikHub Key",
    keyNeeded: "Connect your data source",
    keyText: "Your own TikHub Key. Your watchlist and content stay private.",
    now: "Check now",
    pause: "Pause",
    resume: "Resume",
    remove: "Delete",
    interval: "Interval",
    creator: "Creator",
    status: "Status",
    lastCheck: "Last successful check",
    nextCheck: "Next check",
    operations: "Actions",
    noResults: "No matching results",
    hours: "hours",
    every: "Every",
    pending: "Awaiting baseline",
    running: "Checking",
    idle: "Monitoring",
    backfill: "Catching up",
    error: "Needs attention",
    paused: "Paused",
    never: "Not checked yet",
    save: "Save changes",
    saved: "Saved",
    cancel: "Cancel",
    confirm: "Confirm",
    close: "Close",
    connecting: "Resolving…",
    resolve: "Find creator",
    confirmAuthor: "Confirm and monitor",
    url: "TikTok, Twitter/X or Douyin profile or post link",
    urlPlaceholder: "Paste a profile, post link or Douyin share message",
    douyin: "Douyin",
    platform: "Platform",
    allPlatforms: "All platforms",
    textPost: "Text",
    mixedMedia: "Mixed media",
    textOnly: "This is a text post. Use the button above to copy its content.",
    downloadGif: "Download animation (MP4)",
    unavailableAsset: "No direct download available",
    twitterScope:
      "Twitter/X currently monitors original and quote posts, excluding replies and reposts.",
    quotedPost: "Quoted post",
    resolveHint:
      "Resolving and monitoring use your TikHub Key and consume your API allowance.",
    baselineHint:
      "The first batch is historical. Later posts are marked as updates.",
    addTitle: "Add someone worth following",
    feedTitle: "Fresh ideas. In one place.",
    feedText:
      "Explore posts, copy captions, and download images or videos to this computer.",
    all: "All posts",
    unread: "Unread",
    readAll: "Mark all as read",
    copy: "Copy caption",
    copied: "Caption copied",
    download: "Download video",
    downloadImage: "Download image",
    original: "Open original",
    noPosts: "Your feed starts here.",
    noPostsText:
      "Add a creator. The first check loads recent posts; future updates appear here.",
    noUnread: "You’re all caught up",
    noUnreadText: "New posts will keep an unread marker here.",
    history: "Historical",
    new: "New post",
    settingsText: "Your credentials, time, and preferences.",
    keyHelp:
      "Encrypted on the server. The full key is never returned. Leave blank to keep your key.",
    newKey: "Paste your TikHub API Key",
    deleteKey: "Remove Key",
    timezone: "Display timezone",
    name: "Your name",
    email: "Email",
    password: "Password",
    currentPassword: "Current password",
    newPassword: "New password (10+ characters)",
    changePassword: "Change password",
    changedPassword: "Password changed. Other sessions revoked.",
    invite: "Team invitation code",
    authTitle: "Make room for good ideas.",
    authText:
      "A quiet, organized space for content that matters. On your schedule.",
    welcome: "Welcome back",
    signup: "Start your workspace",
    passwordHelp: "At least 10 characters",
    inviteHelp:
      "Ask your deployment administrator for a code. The first member becomes administrator.",
    hasAccount: "Already have an account?",
    noAccount: "New to SuperHot?",
    backHome: "Back to home",
    privacy: "Your own Key · Private data",
    active: "Monitoring",
    total: "Creators followed",
    needAttention: "Needs attention",
    recent: "Recent activity",
    noRuns: "No checks yet",
    workerOnline: "Background worker online",
    workerOffline: "Worker disconnected. Check the launcher.",
    overviewText: "Less switching. More focus.",
    manage: "Manage watchlist",
    viewFeed: "Open content feed",
    emptyRunText: "Check times, new posts, and errors will appear here.",
    success: "Check complete",
    partial: "Catching up",
    failed: "Check failed",
    results: "new posts",
    pages: "pages requested",
    sdkTitle: "Keep your connection current.",
    sdkText:
      "Check official SDK releases, verify in isolation, then switch. Administrators only.",
    checkVersion: "Check for updates",
    current: "Installed version",
    latest: "Latest stable release",
    notChecked: "Not checked",
    upgrade: "Verify and update",
    upgradeHint:
      "Monitoring pauses briefly during updates. Offline checks cannot guarantee upstream behavior; observe live jobs after switching.",
    queued: "Update queued for the launcher",
    members: "Members",
    member: "Member",
    administrator: "Administrator",
    deploymentLog: "Update history",
    noJobs: "No SDK updates yet",
    notConfigured: "Not configured",
    connected: "Saved",
    account: "Account & preferences",
    security: "Account security",
    noKey: "No Key configured",
    refresh: "Refresh",
    deleteMonitor:
      "Delete this creator and their saved post records? Files already downloaded stay on your computer.",
    deleteKeyConfirm: "Removing your Key stops your TikHub requests. Continue?",
    downloadHint:
      "Refreshing media may consume a TikHub request. The file is saved to this computer.",
    downloading: "Preparing download…",
    downloadStarted: "File sent to your browser",
    noAsset: "No downloadable media yet",
    loading: "Loading…",
    errorTitle: "Action incomplete",
    retry: "Retry",
    details: "Post details",
    joined: "Joined",
    language: "Language",
    updated: "Just updated",
    auto: "Refreshes automatically",
    customHours: "Check interval (hours, 1–168)",
  },
};
type TextKey = keyof typeof copy.zh;
function platformLabel(platform: string, douyinLabel: string, compact = false) {
  if (platform === "douyin") return douyinLabel;
  if (platform === "twitter") return compact ? "X" : "Twitter / X";
  return "TikTok";
}
type View = "overview" | "monitors" | "updates" | "settings" | "admin";
const icons = {
  overview: LayoutDashboard,
  monitors: Radar,
  updates: Layers2,
  settings: Settings2,
  admin: ShieldCheck,
};
function Logo({ onClick }: { onClick: () => void }) {
  return (
    <button className="logo" onClick={onClick} aria-label="SuperHot home">
      <span className="brand-mark">S</span>SuperHot
      <span className="brand-dot">.</span>
    </button>
  );
}
function Spinner() {
  return <LoaderCircle className="spin" size={17} />;
}
function Avatar({ name, url }: { name: string; url?: string }) {
  const [bad, setBad] = useState(false);
  return (
    <span className="avatar">
      {url && !bad ? (
        <img
          src={url}
          alt=""
          referrerPolicy="no-referrer"
          onError={() => setBad(true)}
        />
      ) : (
        name.slice(0, 1).toUpperCase()
      )}
    </span>
  );
}
function Dialog({
  title,
  children,
  close,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
  wide?: boolean;
}) {
  const container = useRef<HTMLElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        container.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)",
        ) || [],
      ).filter((element) => element.offsetParent !== null);
    const initial =
      container.current?.querySelector<HTMLElement>("textarea, input") ||
      focusable()[0];
    initial?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const elements = focusable(),
          first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener("keydown", handler);
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = old;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [close]);
  return (
    <motion.div
      className="dialog-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={close}
    >
      <motion.section
        ref={container}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={"dialog " + (wide ? "dialog-wide" : "")}
        initial={{ y: 15 }}
        animate={{ y: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-button" aria-label="Close" onClick={close}>
            <X size={20} />
          </button>
        </header>
        {children}
      </motion.section>
    </motion.div>
  );
}

export default function App() {
  const [path, setPath] = useState(location.pathname),
    [user, setUser] = useState<User | null>(null),
    [boot, setBoot] = useState(true),
    [locale, setLocale] = useState<"zh" | "en">("zh"),
    [toast, setToast] = useState(""),
    [busy, setBusy] = useState(""),
    [summary, setSummary] = useState<Summary | null>(null),
    [monitors, setMonitors] = useState<Monitor[]>([]),
    [runs, setRuns] = useState<Run[]>([]),
    [posts, setPosts] = useState<Post[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1),
    [query, setQuery] = useState(""),
    [scope, setScope] = useState("all"),
    [authorFilter, setAuthorFilter] = useState(""),
    [platformFilter, setPlatformFilter] = useState(""),
    [adding, setAdding] = useState(false),
    [selected, setSelected] = useState<Post | null>(null),
    [confirm, setConfirm] = useState<{
      message: string;
      action: () => Promise<void>;
    } | null>(null),
    [mobileNav, setMobileNav] = useState(false),
    [loadError, setLoadError] = useState("");
  const t = (key: TextKey) => copy[locale][key];
  const navigate = useCallback((next: string) => {
    history.pushState(null, "", next);
    setPath(next);
    setQuery("");
    setPage(1);
    setMobileNav(false);
    window.scrollTo(0, 0);
  }, []);
  const view: View = (
    ["overview", "monitors", "updates", "settings", "admin"].includes(
      path.split("/")[2],
    )
      ? path.split("/")[2]
      : "overview"
  ) as View;
  const notify = (message: string) => setToast(message);
  const perform = async (id: string, fn: () => Promise<void>) => {
    setBusy(id);
    try {
      await fn();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy("");
    }
  };
  useEffect(() => {
    const pop = () => setPath(location.pathname),
      expired = () => {
        setUser(null);
        setCsrf("");
      };
    window.addEventListener("popstate", pop);
    window.addEventListener("session-expired", expired);
    api<{ user: User; csrf_token: string }>("/auth/me")
      .then((data) => {
        setUser(data.user);
        setLocale(data.user.language);
        setCsrf(data.csrf_token);
      })
      .catch(() => {})
      .finally(() => setBoot(false));
    return () => {
      window.removeEventListener("popstate", pop);
      window.removeEventListener("session-expired", expired);
    };
  }, []);
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 6500);
    return () => clearTimeout(timer);
  }, [toast]);
  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const [s, m, r] = await Promise.all([
        api<Summary>("/overview"),
        api<Monitor[]>("/monitors"),
        api<Run[]>("/runs"),
      ]);
      setSummary(s);
      setMonitors(m);
      setRuns(r);
      setLoadError("");
    } catch (error) {
      setLoadError((error as Error).message);
    }
  }, [user]);
  useEffect(() => {
    void refresh();
    if (!user) return;
    const interval = setInterval(() => void refresh(), 15000);
    return () => clearInterval(interval);
  }, [refresh, user]);
  const refreshPosts = useCallback(async () => {
    if (!user) return;
    try {
      const result = await api<{ items: Post[]; total: number }>(
        `/posts?page=${page}&scope=${scope}&q=${encodeURIComponent(query)}&author=${encodeURIComponent(authorFilter)}&platform=${platformFilter}`,
      );
      setPosts(result.items);
      setTotal(result.total);
    } catch (error) {
      setLoadError((error as Error).message);
    }
  }, [user, page, scope, query, authorFilter, platformFilter]);
  useEffect(() => {
    if (view !== "updates") return;
    const timer = setTimeout(() => void refreshPosts(), 250),
      interval = setInterval(() => void refreshPosts(), 15000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [view, refreshPosts]);
  const date = (value: number | null | undefined) =>
    value
      ? new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-GB", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: user?.timezone || "Asia/Shanghai",
        }).format(new Date(value * 1000))
      : t("never");
  const hourly = (hours: number) =>
    locale === "zh"
      ? `每 ${hours} 小时`
      : `Every ${hours} hour${hours === 1 ? "" : "s"}`;
  const goAdd = () => {
    if (!user?.has_key) {
      navigate("/app/settings");
      notify(t("keyNeeded"));
    } else setAdding(true);
  };
  const handleAuth = (data: { user: User; csrf_token: string }) => {
    setUser(data.user);
    setLocale(data.user.language);
    setCsrf(data.csrf_token);
    navigate("/app/monitors");
  };
  const download = async (post: Post, asset: Asset) => {
    await perform("download", async () => {
      const response = await fetch(
        `/api/posts/${post.id}/assets/${encodeURIComponent(asset.id)}/download`,
        {
          credentials: "same-origin",
        },
      );
      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: t("errorTitle") }));
        throw new Error(error.detail);
      }
      const blob = await response.blob(),
        url = URL.createObjectURL(blob),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${post.platform}-${post.platform_id}-${asset.order + 1}.${asset.kind === "image" ? "jpg" : "mp4"}`;
      anchor.download =
        response.headers
          .get("Content-Disposition")
          ?.match(/filename="([^"]+)"/)?.[1] || anchor.download;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      notify(t("downloadStarted"));
    });
  };
  const markPost = async (post: Post) => {
    setSelected(post);
    if (!post.read) {
      await perform("read", async () => {
        await api(`/posts/${post.id}/read`, "POST");
        await refreshPosts();
        await refresh();
      });
    }
  };
  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      notify(t("copied"));
    } catch {
      notify(
        locale === "zh"
          ? "请选中文字后手动复制"
          : "Select the caption and copy it manually.",
      );
    }
  };
  const toggleLanguage = async () => {
    const language = locale === "zh" ? "en" : "zh";
    setLocale(language);
    if (user) {
      const saved = await api<User>("/settings", "PUT", { language });
      setUser(saved);
    }
  };
  const closeAdd = useCallback(() => setAdding(false), []),
    closePost = useCallback(() => setSelected(null), []),
    closeConfirm = useCallback(() => setConfirm(null), []);
  if (boot)
    return (
      <div className="boot">
        <Logo onClick={() => navigate("/")} />
        <Spinner />
      </div>
    );
  const notice = (
    <AnimatePresence>
      {toast && (
        <motion.div
          className="toast"
          role="status"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
        >
          <span>{toast}</span>
          <button aria-label={t("close")} onClick={() => setToast("")}>
            <X size={16} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
  if (!path.startsWith("/app") && path !== "/login" && path !== "/register")
    return (
      <>
        <Home
          navigate={navigate}
          user={user}
          locale={locale}
          toggleLanguage={() => void perform("language", toggleLanguage)}
        />
        {notice}
      </>
    );
  if (!user)
    return (
      <>
        <Auth
          register={path === "/register"}
          navigate={navigate}
          onAuth={handleAuth}
          t={t}
          locale={locale}
          toggleLanguage={() => setLocale(locale === "zh" ? "en" : "zh")}
        />
        {notice}
      </>
    );
  const visibleMonitors = monitors.filter(
    (row) =>
      (!platformFilter || row.platform === platformFilter) &&
      `${row.nickname} ${row.username}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const platformSelect = (
    <select
      aria-label={t("platform")}
      value={platformFilter}
      onChange={(event) => {
        setPlatformFilter(event.target.value);
        setAuthorFilter("");
        setPage(1);
      }}
    >
      <option value="">{t("allPlatforms")}</option>
      <option value="tiktok">TikTok</option>
      <option value="twitter">Twitter / X</option>
      <option value="douyin">{t("douyin")}</option>
    </select>
  );
  const stateLabel = (row: Monitor) =>
    !row.enabled
      ? t("paused")
      : t(
          (["running", "backfill", "error", "pending"].includes(row.state)
            ? row.state
            : "idle") as TextKey,
        );
  return (
    <div className="workspace">
      <aside className={"sidebar " + (mobileNav ? "nav-open" : "")}>
        <Logo onClick={() => navigate("/")} />
        <span className="nav-label">{t("workspace")}</span>
        <nav>
          {(["overview", "monitors", "updates"] as View[]).map((key) => {
            const Icon = icons[key];
            return (
              <button
                key={key}
                className={view === key ? "active" : ""}
                onClick={() => navigate("/app/" + key)}
              >
                <Icon size={18} />
                <span>{t(key)}</span>
                {key === "updates" && !!summary?.unread && (
                  <b className="nav-count">{summary.unread}</b>
                )}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <nav>
            {(
              [
                "settings",
                ...(user.role === "admin" ? ["admin"] : []),
              ] as View[]
            ).map((key) => {
              const Icon = icons[key];
              return (
                <button
                  key={key}
                  className={view === key ? "active" : ""}
                  onClick={() => navigate("/app/" + key)}
                >
                  <Icon size={18} />
                  <span>{t(key)}</span>
                </button>
              );
            })}
          </nav>
          <div className="profile">
            <Avatar name={user.name} />
            <div>
              <strong>{user.name}</strong>
              <small>
                {user.role === "admin" ? t("administrator") : t("member")}
              </small>
            </div>
            <button
              className="icon-button"
              aria-label={t("logout")}
              onClick={() =>
                void perform("logout", async () => {
                  await api("/auth/logout", "POST");
                  setUser(null);
                  setCsrf("");
                  navigate("/");
                })
              }
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              aria-label="Menu"
              onClick={() => setMobileNav(!mobileNav)}
            >
              <Menu size={19} />
            </button>
            <span>{t("workspace")}</span>
            <span className="slash">/</span>
            <strong>{t(view)}</strong>
          </div>
          <div>
            <span className="timezone">
              <Globe2 size={14} />
              {user.timezone}
            </span>
            <button
              className="language-button"
              onClick={() => void perform("language", toggleLanguage)}
            >
              {locale === "zh" ? "EN" : "中文"}
            </button>
            <span
              className={
                "worker-indicator " + (summary?.worker_online ? "online" : "")
              }
              title={
                summary?.worker_online ? t("workerOnline") : t("workerOffline")
              }
            />
          </div>
        </header>
        <main className="content" id="main-content">
          {loadError && (
            <div className="error-banner" role="alert">
              <span>{loadError}</span>
              <button onClick={() => void refresh()}>{t("retry")}</button>
            </div>
          )}
          {view === "overview" && (
            <>
              <PageHeading
                eyebrow="A LITTLE MORE FOCUS"
                title={
                  locale === "zh"
                    ? `${user.name}，你好。`
                    : `Hello, ${user.name}.`
                }
                description={t("overviewText")}
                action={
                  <button className="primary" onClick={goAdd}>
                    <Plus size={17} />
                    {t("add")}
                  </button>
                }
              />
              <div className="stat-grid">
                {(
                  ["total", "active", "unread", "needAttention"] as TextKey[]
                ).map((label, index) => (
                  <button
                    className="stat"
                    key={label}
                    onClick={() =>
                      navigate("/app/" + (index === 2 ? "updates" : "monitors"))
                    }
                  >
                    <span>{t(label)}</span>
                    <strong>
                      {summary
                        ? [
                            summary.monitors,
                            summary.active,
                            summary.unread,
                            summary.errors,
                          ][index]
                        : "—"}
                    </strong>
                    <ArrowUpRight size={17} />
                  </button>
                ))}
              </div>
              {!user.has_key && (
                <div className="connect-banner">
                  <span className="key-icon">
                    <KeyRound size={22} />
                  </span>
                  <div>
                    <h3>{t("keyNeeded")}</h3>
                    <p>{t("keyText")}</p>
                  </div>
                  <button
                    className="secondary"
                    onClick={() => navigate("/app/settings")}
                  >
                    {t("setKey")}
                    <ArrowRight size={16} />
                  </button>
                </div>
              )}
              <div className="section-heading">
                <h2>{t("recent")}</h2>
                <span className="meta">{t("auto")}</span>
              </div>
              {runs.length ? (
                <div className="run-list">
                  {runs.slice(0, 8).map((run) => (
                    <div className="run-row" key={run.id}>
                      <span className={"activity-icon " + run.status}>
                        {run.status === "error" ? (
                          <X size={16} />
                        ) : (
                          <Check size={16} />
                        )}
                      </span>
                      <div>
                        <strong>
                          {monitors.find((m) => m.id === run.monitor_id)
                            ?.nickname || "TikTok"}
                        </strong>
                        <p>
                          {run.message ||
                            (run.status === "partial"
                              ? t("partial")
                              : `${run.new_count} ${t("results")} · ${run.pages} ${t("pages")}`)}
                        </p>
                      </div>
                      <time>{date(run.finished_at)}</time>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty
                  icon={<Clock3 />}
                  title={t("noRuns")}
                  text={t("emptyRunText")}
                />
              )}
            </>
          )}
          {view === "monitors" && (
            <>
              <PageHeading
                eyebrow="YOUR WATCHLIST"
                title={t("monitors")}
                description={t("watchTitle")}
                action={
                  <button className="primary" onClick={goAdd}>
                    <Plus size={17} />
                    {t("add")}
                  </button>
                }
              />
              <div className="list-toolbar">
                {platformSelect}
                <label className="search">
                  <Search size={16} />
                  <input
                    value={query}
                    placeholder={t("search")}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </label>
                <span className="meta">
                  {visibleMonitors.length}{" "}
                  {locale === "zh" ? "个监控对象" : "creators"}
                </span>
              </div>
              {!monitors.length ? (
                <Empty
                  icon={<Radar />}
                  title={t("emptyTitle")}
                  text={t("emptyText")}
                  action={
                    <button className="primary" onClick={goAdd}>
                      {user.has_key ? t("add") : t("setKey")}
                      <ArrowRight size={16} />
                    </button>
                  }
                />
              ) : !visibleMonitors.length ? (
                <Empty icon={<Search />} title={t("noResults")} text="" />
              ) : (
                <div className="table-shell">
                  <table>
                    <thead>
                      <tr>
                        <th>{t("creator")}</th>
                        <th>{t("interval")}</th>
                        <th>{t("status")}</th>
                        <th>{t("lastCheck")}</th>
                        <th>{t("operations")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleMonitors.map((row) => (
                        <tr key={row.id}>
                          <td>
                            <div className="author-cell">
                              <Avatar name={row.nickname} url={row.avatar} />
                              <div>
                                <strong>{row.nickname}</strong>
                                <small>
                                  <span className="platform-badge">
                                    {platformLabel(
                                      row.platform,
                                      t("douyin"),
                                      true,
                                    )}
                                  </span>{" "}
                                  @{row.username || row.author_id}
                                </small>
                                {row.last_error && (
                                  <span className="row-error">
                                    {row.last_error}
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td>
                            <label
                              className="sr-only"
                              htmlFor={"interval-" + row.id}
                            >
                              {t("interval")}
                            </label>
                            <select
                              id={"interval-" + row.id}
                              className="interval-select"
                              value={row.interval_hours}
                              disabled={busy === row.id}
                              onChange={(e) =>
                                void perform(row.id, async () => {
                                  await api(`/monitors/${row.id}`, "PATCH", {
                                    interval_hours: Number(e.target.value),
                                  });
                                  await refresh();
                                })
                              }
                            >
                              {[
                                ...new Set([
                                  1,
                                  2,
                                  3,
                                  6,
                                  12,
                                  24,
                                  48,
                                  72,
                                  168,
                                  row.interval_hours,
                                ]),
                              ]
                                .sort((a, b) => a - b)
                                .map((n) => (
                                  <option key={n} value={n}>
                                    {hourly(n)}
                                  </option>
                                ))}
                            </select>
                          </td>
                          <td>
                            <span
                              className={
                                "status " +
                                (!row.enabled ? "paused" : row.state)
                              }
                            >
                              <i />
                              {stateLabel(row)}
                            </span>
                            <small className="next-check">
                              {row.enabled &&
                                `${t("nextCheck")} ${date(row.next_check_at)}`}
                            </small>
                          </td>
                          <td>
                            <span className="date-text">
                              {date(row.last_success_at)}
                            </span>
                          </td>
                          <td>
                            <div className="row-actions">
                              <button
                                className="icon-button"
                                title={t("now")}
                                aria-label={`${t("now")} ${row.nickname}`}
                                disabled={
                                  busy === row.id || row.state === "running"
                                }
                                onClick={() =>
                                  void perform(row.id, async () => {
                                    await api(
                                      `/monitors/${row.id}/check`,
                                      "POST",
                                    );
                                    notify(
                                      locale === "zh"
                                        ? "已加入检查队列"
                                        : "Added to check queue",
                                    );
                                    await refresh();
                                  })
                                }
                              >
                                <RefreshCw size={16} />
                              </button>
                              <button
                                className="icon-button"
                                title={row.enabled ? t("pause") : t("resume")}
                                aria-label={`${row.enabled ? t("pause") : t("resume")} ${row.nickname}`}
                                disabled={busy === row.id}
                                onClick={() =>
                                  void perform(row.id, async () => {
                                    await api(`/monitors/${row.id}`, "PATCH", {
                                      enabled: !row.enabled,
                                    });
                                    await refresh();
                                  })
                                }
                              >
                                {row.enabled ? (
                                  <Pause size={16} />
                                ) : (
                                  <Play size={16} />
                                )}
                              </button>
                              <button
                                className="icon-button danger"
                                title={t("remove")}
                                aria-label={`${t("remove")} ${row.nickname}`}
                                onClick={() =>
                                  setConfirm({
                                    message: t("deleteMonitor"),
                                    action: async () => {
                                      await api(
                                        `/monitors/${row.id}`,
                                        "DELETE",
                                      );
                                      await refresh();
                                    },
                                  })
                                }
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="list-footer">
                <span>
                  <RefreshCw size={13} />
                  {summary?.worker_online
                    ? t("workerOnline")
                    : t("workerOffline")}
                </span>
                <span>{t("privacy")}</span>
              </div>
            </>
          )}
          {view === "updates" && (
            <>
              <PageHeading
                eyebrow="LESS NOISE. MORE IDEAS."
                title={t("feedTitle")}
                description={t("feedText")}
                action={
                  <button
                    className="secondary"
                    onClick={() =>
                      void perform("readAll", async () => {
                        await api("/posts/read-all", "POST");
                        await refreshPosts();
                        await refresh();
                      })
                    }
                  >
                    <CheckCheck size={17} />
                    {t("readAll")}
                  </button>
                }
              />
              <div className="feed-toolbar">
                <div className="segmented">
                  {["all", "unread"].map((key) => (
                    <button
                      key={key}
                      className={scope === key ? "selected" : ""}
                      onClick={() => {
                        setScope(key);
                        setPage(1);
                      }}
                    >
                      {t(key as TextKey)}
                    </button>
                  ))}
                </div>
                <div className="feed-filters">
                  {platformSelect}
                  <label className="search">
                    <Search size={16} />
                    <input
                      placeholder={
                        locale === "zh" ? "搜索作品文案" : "Search captions"
                      }
                      value={query}
                      onChange={(e) => {
                        setQuery(e.target.value);
                        setPage(1);
                      }}
                    />
                  </label>
                  <select
                    aria-label={t("creator")}
                    value={authorFilter}
                    onChange={(e) => {
                      setAuthorFilter(e.target.value);
                      setPage(1);
                    }}
                  >
                    <option value="">
                      {locale === "zh" ? "全部作者" : "All creators"}
                    </option>
                    {monitors
                      .filter(
                        (m) => !platformFilter || m.platform === platformFilter,
                      )
                      .map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.nickname}
                        </option>
                      ))}
                  </select>
                </div>
              </div>
              {posts.length ? (
                <>
                  <div className="post-grid">
                    {posts.map((post) => (
                      <button
                        className="post-card"
                        key={post.id}
                        onClick={() => void markPost(post)}
                      >
                        <div
                          className={
                            "post-cover" +
                            (post.kind === "text" ? " text-post-cover" : "")
                          }
                        >
                          {post.cover ? (
                            <img
                              src={post.cover}
                              alt=""
                              loading="lazy"
                              referrerPolicy="no-referrer"
                              onError={(e) => {
                                e.currentTarget.style.display = "none";
                              }}
                            />
                          ) : (
                            <div className="cover-placeholder">
                              {post.kind === "text" ? (
                                <p className="text-post-preview">{post.text}</p>
                              ) : (
                                <span className="brand-mark">S</span>
                              )}
                            </div>
                          )}
                          <span className="post-type">
                            {post.kind === "text" ? (
                              <FileText size={14} />
                            ) : post.kind === "mixed" ? (
                              <Layers2 size={14} />
                            ) : post.kind === "images" ? (
                              <Image size={14} />
                            ) : (
                              <Video size={14} />
                            )}{" "}
                            {post.kind === "text"
                              ? t("textPost")
                              : post.kind === "mixed"
                                ? t("mixedMedia")
                                : post.kind === "images"
                                  ? post.asset_count
                                  : "VIDEO"}
                          </span>
                          {!post.read && <span className="unread-dot" />}
                        </div>
                        <div className="post-body">
                          <span className="post-author">
                            <span>
                              <span className="platform-badge">
                                {platformLabel(
                                  post.platform,
                                  t("douyin"),
                                  true,
                                )}
                              </span>{" "}
                              {post.author}
                            </span>
                            <ArrowUpRight size={15} />
                          </span>
                          <p>
                            {post.text ||
                              platformLabel(post.platform, t("douyin"))}
                          </p>
                          <div>
                            <time>
                              {date(post.published_at || post.found_at)}
                            </time>
                            <span>{post.is_new ? t("new") : t("history")}</span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                  <div className="pagination">
                    <span>
                      {total} {locale === "zh" ? "条作品" : "posts"}
                    </span>
                    <div>
                      <button
                        className="icon-button"
                        aria-label="Previous"
                        disabled={page <= 1}
                        onClick={() => setPage(page - 1)}
                      >
                        <ChevronLeft size={18} />
                      </button>
                      <span>
                        {page} / {Math.max(1, Math.ceil(total / 24))}
                      </span>
                      <button
                        className="icon-button"
                        aria-label="Next"
                        disabled={page * 24 >= total}
                        onClick={() => setPage(page + 1)}
                      >
                        <ChevronRight size={18} />
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <Empty
                  icon={<Layers2 />}
                  title={scope === "unread" ? t("noUnread") : t("noPosts")}
                  text={
                    scope === "unread" ? t("noUnreadText") : t("noPostsText")
                  }
                  action={
                    <button
                      className="secondary"
                      onClick={() => navigate("/app/monitors")}
                    >
                      {t("manage")}
                      <ArrowRight size={16} />
                    </button>
                  }
                />
              )}
            </>
          )}
          {view === "settings" && (
            <Settings
              user={user}
              t={t}
              busy={busy}
              perform={perform}
              notify={notify}
              saveUser={(saved) => {
                setUser(saved);
                setLocale(saved.language);
              }}
            />
          )}
          {view === "admin" &&
            (user.role === "admin" ? (
              <Admin t={t} date={date} notify={notify} />
            ) : (
              <Empty
                icon={<ShieldCheck />}
                title={t("administrator")}
                text=""
              />
            ))}
        </main>
        <footer className="app-footer">
          <span>SuperHot</span>
          <span>Stay curious. Stay ahead.</span>
        </footer>
      </div>
      <AnimatePresence>
        {adding && (
          <AddMonitor
            t={t}
            close={closeAdd}
            onCreated={async () => {
              setAdding(false);
              setPlatformFilter("");
              setAuthorFilter("");
              setQuery("");
              await refresh();
            }}
          />
        )}
        {selected && (
          <Dialog title={t("details")} close={closePost} wide>
            <div className="post-detail">
              <div className="detail-heading">
                <Avatar name={selected.author} />
                <div>
                  <strong>
                    <span className="platform-badge">
                      {platformLabel(selected.platform, t("douyin"), true)}
                    </span>{" "}
                    {selected.author}
                  </strong>
                  <small>
                    {date(selected.published_at || selected.found_at)}
                  </small>
                </div>
                {selected.kind === "text" ? (
                  <FileText size={19} />
                ) : selected.kind === "mixed" ? (
                  <Layers2 size={19} />
                ) : selected.kind === "images" ? (
                  <Image size={19} />
                ) : (
                  <Video size={19} />
                )}
              </div>
              {selected.cover && (
                <img
                  className="detail-cover"
                  src={selected.cover}
                  referrerPolicy="no-referrer"
                  alt=""
                />
              )}
              <p className="caption">{selected.text || "—"}</p>
              {selected.references?.map((reference) => (
                <blockquote className="quoted-post" key={reference.id}>
                  <a href={reference.url} target="_blank" rel="noreferrer">
                    {t("quotedPost")}
                    {reference.username ? ` · @${reference.username}` : ""}{" "}
                    <ExternalLink size={13} />
                  </a>
                  {reference.text && <p>{reference.text}</p>}
                </blockquote>
              ))}
              <div className="detail-actions">
                <button
                  className="secondary"
                  onClick={() => void copyText(selected.text)}
                >
                  <Copy size={16} />
                  {t("copy")}
                </button>
                <a
                  className="secondary"
                  href={selected.share_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("original")}
                  <ExternalLink size={15} />
                </a>
              </div>
              <hr />
              <p className="form-help">
                {selected.kind === "text" ? t("textOnly") : t("downloadHint")}
              </p>
              <div className="asset-grid">
                {selected.assets?.length ? (
                  selected.assets.map((asset, index) => (
                    <div className="asset-item" key={asset.id}>
                      {asset.preview && (
                        <img
                          className="asset-preview"
                          src={asset.preview}
                          alt={`${asset.kind} ${index + 1}`}
                          referrerPolicy="no-referrer"
                          loading="lazy"
                        />
                      )}
                      <button
                        className="primary"
                        disabled={busy === "download" || !asset.downloadable}
                        onClick={() => void download(selected, asset)}
                      >
                        {busy === "download" ? (
                          <Spinner />
                        ) : (
                          <ArrowDownToLine size={16} />
                        )}{" "}
                        {!asset.downloadable
                          ? t("unavailableAsset")
                          : asset.kind === "image"
                            ? `${t("downloadImage")} ${index + 1}`
                            : `${asset.kind === "animated_gif" ? t("downloadGif") : t("download")} ${index + 1}`}
                      </button>
                    </div>
                  ))
                ) : selected.kind !== "text" ? (
                  <p className="meta">{t("noAsset")}</p>
                ) : null}
              </div>
            </div>
          </Dialog>
        )}
        {confirm && (
          <Dialog title={t("confirm")} close={closeConfirm}>
            <p className="confirm-message">{confirm.message}</p>
            <div className="dialog-actions">
              <button className="secondary" onClick={closeConfirm}>
                {t("cancel")}
              </button>
              <button
                className="primary"
                disabled={busy === "confirm"}
                onClick={() =>
                  void perform("confirm", async () => {
                    await confirm.action();
                    setConfirm(null);
                  })
                }
              >
                {busy === "confirm" ? <Spinner /> : t("confirm")}
              </button>
            </div>
          </Dialog>
        )}
      </AnimatePresence>
      {notice}
    </div>
  );
}

function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function Empty({
  icon,
  title,
  text,
  action,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-art">
        <span />
        <span />
        {icon}
      </div>
      <h2>{title}</h2>
      {text && <p>{text}</p>}
      {action}
    </div>
  );
}

function Auth({
  register,
  navigate,
  onAuth,
  t,
  locale,
  toggleLanguage,
}: {
  register: boolean;
  navigate: (path: string) => void;
  onAuth: (data: { user: User; csrf_token: string }) => void;
  t: (key: TextKey) => string;
  locale: string;
  toggleLanguage: () => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      const body = {
        email: data.get("email"),
        password: data.get("password"),
        ...(register
          ? { name: data.get("name"), invite_code: data.get("invite_code") }
          : {}),
      };
      onAuth(
        await api("/auth/" + (register ? "register" : "login"), "POST", body),
      );
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <aside className="auth-editorial">
        <Logo onClick={() => navigate("/")} />
        <div>
          <span className="eyebrow">YOUR NEXT GOOD IDEA</span>
          <h1>{t("authTitle")}</h1>
          <p>{t("authText")}</p>
          <div className="auth-orbit">
            <Radio size={45} />
            <span />
            <span />
          </div>
        </div>
        <small>MONITOR. DISCOVER. CREATE.</small>
      </aside>
      <main className="auth-main">
        <div className="auth-top">
          <button className="text-button" onClick={() => navigate("/")}>
            <ArrowLeft size={16} />
            {t("backHome")}
          </button>
          <button className="language-button" onClick={toggleLanguage}>
            {locale === "zh" ? "EN" : "中文"}
          </button>
        </div>
        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          <span className="eyebrow">WELCOME TO SUPERHOT</span>
          <h2>{register ? t("signup") : t("welcome")}</h2>
          <p className="auth-subtitle">{t("privacy")}</p>
          {register && (
            <label>
              {t("name")}
              <input
                name="name"
                required
                maxLength={80}
                autoComplete="nickname"
              />
            </label>
          )}
          <label>
            {t("email")}
            <input
              name="email"
              type="email"
              required
              maxLength={254}
              autoComplete="email"
              placeholder="you@team.com"
            />
          </label>
          <label>
            {t("password")}
            <input
              name="password"
              type="password"
              required
              minLength={register ? 10 : 1}
              maxLength={256}
              autoComplete={register ? "new-password" : "current-password"}
              placeholder={register ? t("passwordHelp") : ""}
            />
          </label>
          {register && (
            <label>
              {t("invite")}
              <input
                name="invite_code"
                required
                maxLength={200}
                autoComplete="off"
              />
              <span className="form-help">{t("inviteHelp")}</span>
            </label>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="primary full-width" disabled={busy}>
            {busy ? <Spinner /> : register ? t("register") : t("login")}
            <ArrowRight size={17} />
          </button>
          <p className="auth-switch">
            {register ? t("hasAccount") : t("noAccount")}{" "}
            <button
              type="button"
              onClick={() => {
                setError("");
                navigate(register ? "/login" : "/register");
              }}
            >
              {register ? t("login") : t("register")}
            </button>
          </p>
        </form>
        <footer>SuperHot · Your private content workspace</footer>
      </main>
    </div>
  );
}

function AddMonitor({
  t,
  close,
  onCreated,
}: {
  t: (key: TextKey) => string;
  close: () => void;
  onCreated: () => Promise<void>;
}) {
  const [url, setUrl] = useState(""),
    [hours, setHours] = useState(1),
    [resolved, setResolved] = useState<{
      resolution_id: string;
      author: {
        nickname: string;
        username: string;
        avatar: string;
        platform: string;
      };
    } | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const resolve = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResolved(await api("/monitors/resolve", "POST", { url }));
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title={t("addTitle")} close={close}>
      <form onSubmit={(event) => void resolve(event)} className="stack-form">
        <label>
          {t("url")}
          <textarea
            autoFocus
            required
            rows={3}
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setResolved(null);
            }}
            placeholder={t("urlPlaceholder")}
          />
        </label>
        <label>
          {t("customHours")}
          <input
            type="number"
            min={1}
            max={168}
            required
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          />
        </label>
        <p className="form-help">{t("resolveHint")}</p>
        {resolved ? (
          <>
            <div className="resolved-author">
              <Avatar
                name={resolved.author.nickname}
                url={resolved.author.avatar}
              />
              <div>
                <strong>{resolved.author.nickname}</strong>
                <small>
                  {platformLabel(resolved.author.platform, t("douyin"))} · @
                  {resolved.author.username}
                </small>
              </div>
              <Check className="success-color" size={20} />
            </div>
            <p className="form-help">{t("baselineHint")}</p>
            {resolved.author.platform === "twitter" && (
              <p className="form-help">{t("twitterScope")}</p>
            )}
            <button
              type="button"
              className="primary full-width"
              disabled={busy || hours < 1 || hours > 168}
              onClick={() => {
                setBusy(true);
                void api("/monitors", "POST", {
                  resolution_id: resolved.resolution_id,
                  interval_hours: hours,
                })
                  .then(onCreated)
                  .catch((error) => setError(error.message))
                  .finally(() => setBusy(false));
              }}
            >
              {busy ? <Spinner /> : <Check size={16} />} {t("confirmAuthor")}
            </button>
          </>
        ) : (
          <button className="primary full-width" disabled={busy}>
            {busy ? <Spinner /> : <Search size={16} />}{" "}
            {busy ? t("connecting") : t("resolve")}
          </button>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </Dialog>
  );
}

function Settings({
  user,
  t,
  busy,
  perform,
  notify,
  saveUser,
}: {
  user: User;
  t: (key: TextKey) => string;
  busy: string;
  perform: (id: string, fn: () => Promise<void>) => Promise<void>;
  notify: (message: string) => void;
  saveUser: (user: User) => void;
}) {
  const [key, setKey] = useState(""),
    [removing, setRemoving] = useState(false);
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await perform("settings", async () => {
      const saved = await api<User>("/settings", "PUT", {
        name: form.get("name"),
        timezone: form.get("timezone"),
        language: form.get("language"),
        ...(key ? { api_key: key } : {}),
      });
      saveUser(saved);
      setKey("");
      notify(t("saved"));
    });
  };
  const password = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const element = event.currentTarget,
      data = new FormData(element);
    await perform("password", async () => {
      await api("/settings/password", "PUT", {
        current_password: data.get("current"),
        new_password: data.get("new"),
      });
      element.reset();
      notify(t("changedPassword"));
    });
  };
  return (
    <>
      <PageHeading
        eyebrow="MADE FOR YOUR RHYTHM"
        title={t("settings")}
        description={t("settingsText")}
      />
      <div className="settings-layout">
        <form
          className="settings-card stack-form"
          onSubmit={(event) => void save(event)}
        >
          <div className="settings-heading">
            <KeyRound size={20} />
            <h2>TikHub API Key</h2>
            <span className={"status " + (user.has_key ? "idle" : "paused")}>
              <i />
              {user.has_key ? user.key_hint : t("notConfigured")}
            </span>
          </div>
          <label>
            {t("newKey")}
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              autoComplete="off"
              placeholder={user.has_key ? "••••••••••••••••" : "TikHub API Key"}
            />
            <span className="form-help">{t("keyHelp")}</span>
          </label>
          {user.has_key && (
            <div>
              {removing ? (
                <div className="inline-confirm">
                  <p>{t("deleteKeyConfirm")}</p>
                  <button
                    type="button"
                    className="text-button danger"
                    onClick={() =>
                      void perform("removeKey", async () => {
                        saveUser(
                          await api<User>("/settings", "PUT", { api_key: "" }),
                        );
                        setRemoving(false);
                        notify(t("saved"));
                      })
                    }
                  >
                    {t("confirm")}
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => setRemoving(false)}
                  >
                    {t("cancel")}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="text-button danger"
                  onClick={() => setRemoving(true)}
                >
                  {t("deleteKey")}
                </button>
              )}
            </div>
          )}
          <hr />
          <h3>{t("account")}</h3>
          <label>
            {t("name")}
            <input
              name="name"
              defaultValue={user.name}
              required
              maxLength={80}
            />
          </label>
          <label>
            {t("email")}
            <input value={user.email} disabled />
          </label>
          <div className="form-columns">
            <label>
              {t("timezone")}
              <input
                name="timezone"
                defaultValue={user.timezone}
                list="timezones"
                required
              />
              <datalist id="timezones">
                {[
                  "Asia/Shanghai",
                  "UTC",
                  "America/New_York",
                  "America/Los_Angeles",
                  "Europe/London",
                  "Asia/Tokyo",
                  "Asia/Singapore",
                ].map((zone) => (
                  <option key={zone}>{zone}</option>
                ))}
              </datalist>
            </label>
            <label>
              {t("language")}
              <select name="language" defaultValue={user.language}>
                <option value="zh">简体中文</option>
                <option value="en">English</option>
              </select>
            </label>
          </div>
          <div>
            <button className="primary" disabled={busy === "settings"}>
              {busy === "settings" ? <Spinner /> : <Check size={16} />}{" "}
              {t("save")}
            </button>
          </div>
        </form>
        <form
          className="settings-card stack-form"
          onSubmit={(event) => void password(event)}
        >
          <div className="settings-heading">
            <ShieldCheck size={20} />
            <h2>{t("security")}</h2>
          </div>
          <label>
            {t("currentPassword")}
            <input
              type="password"
              name="current"
              required
              autoComplete="current-password"
            />
          </label>
          <label>
            {t("newPassword")}
            <input
              type="password"
              name="new"
              required
              minLength={10}
              maxLength={256}
              autoComplete="new-password"
            />
          </label>
          <div>
            <button className="secondary" disabled={busy === "password"}>
              {busy === "password" ? <Spinner /> : t("changePassword")}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

function Admin({
  t,
  date,
  notify,
}: {
  t: (key: TextKey) => string;
  date: (value: number) => string;
  notify: (message: string) => void;
}) {
  const [sdk, setSdk] = useState<SDK | null>(null),
    [jobs, setJobs] = useState<Job[]>([]),
    [launcher, setLauncher] = useState(false),
    [canRollback, setCanRollback] = useState(false),
    [installed, setInstalled] = useState(""),
    [users, setUsers] = useState<
      Pick<User, "id" | "name" | "email" | "role">[]
    >([]),
    [busy, setBusy] = useState(false),
    [confirmUpdate, setConfirmUpdate] = useState(false),
    [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try {
      const [result, members] = await Promise.all([
        api<{
          launcher_online: boolean;
          can_rollback: boolean;
          current: string;
          jobs: Job[];
        }>("/admin/updates"),
        api<Pick<User, "id" | "name" | "email" | "role">[]>("/admin/users"),
      ]);
      setJobs(result.jobs);
      setLauncher(result.launcher_online);
      setCanRollback(result.can_rollback);
      setInstalled(result.current);
      setUsers(members);
      setError("");
    } catch (error) {
      setError((error as Error).message);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 4000);
    return () => clearInterval(timer);
  }, [refresh]);
  const check = async () => {
    setBusy(true);
    setError("");
    try {
      setSdk(await api<SDK>("/admin/sdk?force=true"));
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const upgrade = async () => {
    setBusy(true);
    try {
      await api("/admin/updates", "POST", { target: sdk!.latest });
      notify(t("queued"));
      setConfirmUpdate(false);
      await refresh();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeading
        eyebrow="SYSTEM / TIKHUB"
        title={t("sdkTitle")}
        description={t("sdkText")}
        action={
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void check()}
          >
            {busy ? <Spinner /> : <RefreshCw size={16} />} {t("checkVersion")}
          </button>
        }
      />
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      <section className="sdk-panel">
        <div className="sdk-mark">
          <span className="brand-mark">T</span>
          <div>
            <h2>TikHub Python SDK</h2>
            <span className="meta">TikHub / TikHub-API-Python-SDK</span>
          </div>
        </div>
        <div className="sdk-versions">
          <div>
            <span>{t("current")}</span>
            <strong>{sdk?.current || installed || "—"}</strong>
          </div>
          <ArrowRight size={22} />
          <div>
            <span>{t("latest")}</span>
            <strong>{sdk?.latest || t("notChecked")}</strong>
          </div>
        </div>
        {sdk?.blocked && <p className="form-error">{sdk.blocked}</p>}
        {sdk?.can_update && (
          <button
            className="primary"
            disabled={
              busy ||
              !launcher ||
              jobs.some((job) =>
                ["queued", "preparing", "switching"].includes(job.state),
              )
            }
            onClick={() => setConfirmUpdate(true)}
          >
            <ArrowDownToLine size={16} />
            {t("upgrade")}
          </button>
        )}
        {sdk && (
          <a
            href={sdk.url}
            target="_blank"
            rel="noreferrer"
            className="text-button"
          >
            GitHub Release <ArrowUpRight size={15} />
          </a>
        )}
        {sdk?.notes && (
          <details>
            <summary>Release notes</summary>
            <pre className="release-notes">{sdk.notes}</pre>
          </details>
        )}
        <p className="form-help">{t("upgradeHint")}</p>
        <span className={"status " + (launcher ? "idle" : "error")}>
          <i />
          {launcher ? "Launcher online" : "Launcher offline"}
        </span>
      </section>
      <div className="section-heading">
        <h2>{t("deploymentLog")}</h2>
        {canRollback && (
          <button
            className="secondary"
            disabled={
              busy ||
              !launcher ||
              jobs.some((job) =>
                [
                  "queued",
                  "rollback_queued",
                  "preparing",
                  "switching",
                ].includes(job.state),
              )
            }
            onClick={() => {
              setBusy(true);
              void api("/admin/updates/rollback", "POST")
                .then(() => {
                  notify(t("queued"));
                  void refresh();
                })
                .catch((error) => setError(error.message))
                .finally(() => setBusy(false));
            }}
          >
            <RefreshCw size={15} />
            Rollback
          </button>
        )}
      </div>
      <div className="run-list">
        {jobs.length ? (
          jobs.map((job) => (
            <div className="run-row" key={job.id}>
              <span
                className={
                  "activity-icon " +
                  (["success", "rolled_back"].includes(job.state)
                    ? "success"
                    : job.state === "failed"
                      ? "error"
                      : "")
                }
              >
                <RefreshCw size={16} />
              </span>
              <div>
                <strong>
                  {job.previous} → {job.target}{" "}
                  <span className="meta">{job.state}</span>
                </strong>
                <p>{job.message}</p>
              </div>
              <time>{date(job.created_at)}</time>
            </div>
          ))
        ) : (
          <p className="muted-empty">{t("noJobs")}</p>
        )}
      </div>
      <div className="section-heading">
        <h2>
          {t("members")} <span className="meta">{users.length}</span>
        </h2>
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>{t("name")}</th>
              <th>{t("email")}</th>
              <th>{t("status")}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((member) => (
              <tr key={member.id}>
                <td>{member.name}</td>
                <td>{member.email}</td>
                <td>
                  {member.role === "admin" ? t("administrator") : t("member")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <AnimatePresence>
        {confirmUpdate && (
          <Dialog title={t("upgrade")} close={() => setConfirmUpdate(false)}>
            <p className="confirm-message">{t("upgradeHint")}</p>
            <div className="dialog-actions">
              <button
                className="secondary"
                onClick={() => setConfirmUpdate(false)}
              >
                {t("cancel")}
              </button>
              <button
                className="primary"
                disabled={busy}
                onClick={() => void upgrade()}
              >
                {busy ? <Spinner /> : t("confirm")}
              </button>
            </div>
          </Dialog>
        )}
      </AnimatePresence>
    </>
  );
}

function Home({
  navigate,
  user,
  locale,
  toggleLanguage,
}: {
  navigate: (path: string) => void;
  user: User | null;
  locale: string;
  toggleLanguage: () => void;
}) {
  const reduced = useReducedMotion(),
    en = locale === "en";
  return (
    <div className="home">
      <header className="home-nav">
        <Logo onClick={() => navigate("/")} />
        <nav>
          <a href="#workflow">{en ? "How it works" : "如何使用"}</a>
          <a href="#built-for-focus">{en ? "Made for focus" : "专注内容"}</a>
        </nav>
        <div>
          <button className="language-button" onClick={toggleLanguage}>
            {en ? "中文" : "EN"}
          </button>
          <button
            className="home-login"
            onClick={() => navigate(user ? "/app/monitors" : "/login")}
          >
            {user
              ? en
                ? "My workspace"
                : "我的工作台"
              : en
                ? "Log in"
                : "登录"}
            <ArrowUpRight size={16} />
          </button>
        </div>
      </header>
      <main>
        <section className="hero">
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="hero-copy"
          >
            <span className="home-kicker">
              <i />
              {en ? "FOR THE CURIOUS. FOR YOUR TEAM." : "为专注内容的团队而造"}
            </span>
            <h1>
              {en ? "Follow what matters." : "关注值得关注的。"}
              <br />
              <span>
                {en ? "Make room for what’s next." : "其余，交给 SuperHot。"}
              </span>
            </h1>
            <p>
              {en ? (
                <>
                  Turn scattered creators into a clear content stream.
                  <br />
                  Discover TikTok, Twitter/X and Douyin posts on your schedule.
                </>
              ) : (
                <>
                  把散落的账号，变成清晰的信息流。
                  <br />
                  定时发现 TikTok、Twitter/X
                  与抖音新内容，留出时间做更重要的事。
                </>
              )}
            </p>
            <button
              className="primary hero-cta"
              onClick={() => navigate(user ? "/app/monitors" : "/register")}
            >
              {en ? "Open your workspace" : "开始我的监控"}
              <ArrowRight size={18} />
            </button>
            <div className="hero-promises">
              <span>
                <Radar size={15} />
                {en ? "Scheduled checks" : "定时关注"}
              </span>
              <span>
                <ArrowDownToLine size={15} />
                {en ? "Images & videos" : "图片与视频"}
              </span>
              <span>
                <KeyRound size={15} />
                {en ? "Your own API Key" : "自有 API Key"}
              </span>
            </div>
          </motion.div>
          <motion.div
            className="hero-visual"
            initial={reduced ? false : { opacity: 0, rotate: 3 }}
            animate={{ opacity: 1, rotate: 0 }}
            transition={{ duration: 0.9, delay: 0.15 }}
            aria-label={
              en ? "Illustration of a new content signal" : "新作品信号示意"
            }
          >
            <div className="orbit orbit-a" />
            <div className="orbit orbit-b" />
            <div className="orbit orbit-c" />
            <div className="signal-card">
              <span className="signal-kicker">YOUR NEXT GOOD IDEA</span>
              <Radio size={40} />
              <h2>{en ? "A little ahead." : "新的灵感，已到达。"}</h2>
              <p>
                {en
                  ? "A quieter way to stay in the loop."
                  : "让值得关注的，按你的节奏到来。"}
              </p>
              <div className="signal-footer">
                <span>
                  <i />
                  TikTok · X · {en ? "Douyin" : "抖音"}
                </span>
                <span>SuperHot</span>
              </div>
            </div>
            <div className="floating-tag">
              <Check size={16} />
              {en ? "Always on your radar" : "你的关注，持续在线"}
            </div>
            <span className="signal-coordinate">SIGNAL / 001</span>
          </motion.div>
        </section>
        <div className="home-divider">
          <span>LESS NOISE. MORE IDEAS.</span>
          <a href="#workflow">
            <ArrowDown size={17} />
            {en ? "Explore" : "向下探索"}
          </a>
        </div>
        <section className="workflow-section" id="workflow">
          <div className="home-section-title">
            <span className="eyebrow">A SIMPLE RHYTHM</span>
            <h2>
              {en ? "Three steps. A clearer view." : "让关注，变得简单。"}
            </h2>
            <p>
              {en
                ? "A focused workflow, from discovery to your next idea."
                : "从关注到发现，一条清晰的工作流。"}
            </p>
          </div>
          <div className="workflow-grid">
            {(en
              ? [
                  [
                    "01",
                    "Find your people.",
                    "Paste a TikTok, Twitter/X or Douyin profile or post link. Confirm the creator you want to follow.",
                  ],
                  [
                    "02",
                    "Set your rhythm.",
                    "Choose an hourly schedule. Your workspace keeps checking in the background.",
                  ],
                  [
                    "03",
                    "Keep the good stuff.",
                    "See updates together. Copy captions and save videos or images to your computer.",
                  ],
                ]
              : [
                  [
                    "01",
                    "粘贴一个链接",
                    "主页或作品链接都可以。识别作者，确认这正是你想关注的人。",
                  ],
                  [
                    "02",
                    "设定你的节奏",
                    "每小时、每两小时，或更适合你的间隔。后台会按计划持续检查。",
                  ],
                  [
                    "03",
                    "留下值得留下的",
                    "集中查看更新，复制文案，把图片和视频保存到自己的电脑。",
                  ],
                ]
            ).map(([number, title, text]) => (
              <article key={number}>
                <span className="step-number">{number}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="focus-section" id="built-for-focus">
          <div>
            <span className="eyebrow">A SPACE OF YOUR OWN</span>
            <h2>
              {en ? (
                <>
                  Your creators.
                  <br />
                  Your quiet corner.
                </>
              ) : (
                <>
                  给好内容，
                  <br />
                  留一个专注的空间。
                </>
              )}
            </h2>
            <p>
              {en
                ? "Your watchlist stays private. Each teammate brings their own TikHub Key. No shared allowances, no clutter."
                : "监控列表与更新内容仅自己可见，每位成员使用自己的 TikHub Key。把工作留在清晰的空间里。"}
            </p>
            <button
              className="text-button"
              onClick={() => navigate(user ? "/app/monitors" : "/register")}
            >
              {en ? "Make it yours" : "进入我的工作空间"}
              <ArrowUpRight size={18} />
            </button>
          </div>
          <div className="focus-note">
            <KeyRound size={26} />
            <span>{en ? "A private workspace" : "个人工作空间"}</span>
            <h3>
              {en ? "Built around your attention." : "围绕你的注意力而设计。"}
            </h3>
            <ul>
              <li>
                <Check size={15} />
                {en ? "Private watchlist and content" : "独立的关注与内容记录"}
              </li>
              <li>
                <Check size={15} />
                {en ? "Your credentials, encrypted" : "加密保存个人凭据"}
              </li>
              <li>
                <Check size={15} />
                {en ? "A schedule that fits your day" : "适合自己的检查节奏"}
              </li>
            </ul>
          </div>
        </section>
        <section className="home-final">
          <span className="eyebrow">STAY CURIOUS. STAY AHEAD.</span>
          <h2>
            {en ? "Your next idea is out there." : "下一条好内容，正在发生。"}
          </h2>
          <button
            className="primary"
            onClick={() => navigate(user ? "/app/monitors" : "/register")}
          >
            {en ? "Start following" : "开始关注"}
            <ArrowRight size={18} />
          </button>
        </section>
      </main>
      <footer className="home-footer">
        <Logo onClick={() => navigate("/")} />
        <span>© {new Date().getFullYear()} SuperHot</span>
        <span>MONITOR. DISCOVER. CREATE.</span>
      </footer>
    </div>
  );
}
