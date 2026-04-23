"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import PrakritiLoader from "@/components/PrakritiLoader";
import { ArrowPathIcon, DocumentArrowDownIcon, ClockIcon } from "@heroicons/react/24/outline";
import {
  ComposedChart,
  Line,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

type SeriesPoint = { date: string; count: number };

type ThemeRow = { id: string; label: string; count: number; percent: number };

type QuestionThemesBlock = {
  themes: ThemeRow[];
  user_messages_sampled: number;
  capped: boolean;
  note: string;
  top_theme?: { id: string; label: string; count: number; percent: number } | null;
  general_other_percent?: number;
  avg_user_messages_per_session?: number | null;
  sessions_with_user_messages?: number;
};

type AnalyticsSummary = {
  metric: string;
  days: number;
  series: SeriesPoint[];
  last_7_days_total: number;
  previous_7_days_total: number;
  percent_change_vs_prev_week: number | null;
  earliest_event_at: string | null;
  total_in_range: number;
  event_rows_in_range?: number;
  legacy_bot_replies_merged?: number;
  include_legacy_chat_sessions?: boolean;
  question_themes?: QuestionThemesBlock | null;
};

const THEME_BAR_COLORS = [
  "#2563eb",
  "#4f46e5",
  "#7c3aed",
  "#9333ea",
  "#c026d3",
  "#db2777",
  "#dc2626",
  "#ea580c",
  "#ca8a04",
  "#16a34a",
];

const cardClass =
  "rounded-2xl border border-slate-200/70 bg-white/80 shadow-md shadow-slate-200/50 backdrop-blur-sm transition-all duration-300 hover:border-slate-300/80 hover:shadow-lg hover:shadow-slate-300/40 hover:-translate-y-0.5 motion-reduce:transition-shadow motion-reduce:hover:translate-y-0";
const innerStatClass =
  "rounded-xl border border-slate-200/60 bg-gradient-to-br from-slate-50/90 to-indigo-50/30 p-3 transition-shadow duration-200 hover:shadow-md";

const brandPrimary = "var(--brand-primary, #2563eb)";
const brandFillHex = "#2563eb";
const brandFillId = "analyticsEngagementFill";

/** API accepts 7–120; we expose friendly presets. */
const RANGE_OPTIONS: { value: number; label: string }[] = [
  { value: 28, label: "28d" },
  { value: 42, label: "42d" },
  { value: 90, label: "90d" },
];

function escapeCsvField(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const s = String(value);
  if (/[",\r\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function buildAnalyticsCsv(d: AnalyticsSummary): string {
  const lines: string[] = [];
  lines.push("metric,value");
  lines.push(
    [escapeCsvField("generated_utc"), escapeCsvField(new Date().toISOString())].join(",")
  );
  lines.push([escapeCsvField("chart_range_days"), escapeCsvField(d.days)].join(","));
  lines.push("");
  lines.push("kpi,value");
  lines.push([escapeCsvField("last_7_days"), escapeCsvField(d.last_7_days_total)].join(","));
  lines.push([escapeCsvField("previous_7_days"), escapeCsvField(d.previous_7_days_total)].join(","));
  lines.push(
    [
      escapeCsvField("change_vs_prev_week_pct"),
      escapeCsvField(
        d.percent_change_vs_prev_week == null ? "" : d.percent_change_vs_prev_week
      ),
    ].join(",")
  );
  lines.push("");
  lines.push("date_utc,completed_ai_responses");
  for (const p of d.series) {
    lines.push([escapeCsvField(p.date), escapeCsvField(p.count)].join(","));
  }
  if (d.question_themes?.themes?.length) {
    lines.push("");
    lines.push("theme_id,theme_label,count,percent");
    for (const t of d.question_themes.themes) {
      lines.push(
        [escapeCsvField(t.id), escapeCsvField(t.label), escapeCsvField(t.count), escapeCsvField(t.percent)].join(
          ","
        )
      );
    }
  }
  return lines.join("\n");
}

function downloadTextFile(filename: string, content: string, mime: string) {
  const blob = new Blob([`\uFEFF${content}`], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.click();
  URL.revokeObjectURL(url);
}

function formatDayLabel(iso: string) {
  try {
    const d = new Date(iso + "T12:00:00.000Z");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

function AnalyticsContent() {
  const { profile } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname() || "/admin/analytics";
  const [rangeDays, setRangeDays] = useState(42);
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

  useEffect(() => {
    if (!searchParams) return;
    const p = searchParams.get("days");
    if (p) {
      const n = parseInt(p, 10);
      if (n >= 7 && n <= 120) setRangeDays(n);
    }
  }, [searchParams]);

  const load = useCallback(async () => {
    if (!profile?.email) return;
    setLoading(true);
    setErr(null);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const url = new URL(`${backendUrl}/api/admin/ai-analytics/summary`);
      url.searchParams.set("email", profile.email);
      url.searchParams.set("days", String(rangeDays));
      const res = await fetch(url.toString());
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error((j as { detail?: string }).detail || res.statusText);
      }
      const json = (await res.json()) as AnalyticsSummary;
      setData(json);
      setLastUpdatedAt(new Date());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [profile?.email, rangeDays]);

  const applyRange = useCallback(
    (d: number) => {
      setRangeDays(d);
      const next = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
      next.set("days", String(d));
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [pathname, router]
  );

  const exportCsv = useCallback(() => {
    if (!data) return;
    const name = `ai-analytics-${data.days}d-${new Date().toISOString().slice(0, 10)}.csv`;
    downloadTextFile(name, buildAnalyticsCsv(data), "text/csv");
  }, [data]);

  useEffect(() => {
    if (profile?.email) {
      void load();
    }
  }, [profile?.email, load]);

  if (loading && !data) {
    return <PrakritiLoader message="Loading analytics…" />;
  }
  if (err) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className={cardClass + " p-6"}>
          <p className="text-red-600 font-medium">{err}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-md transition hover:opacity-95 hover:shadow-lg active:scale-[0.98]"
            style={{ backgroundColor: brandPrimary }}
          >
            <ArrowPathIcon className="h-4 w-4" aria-hidden />
            Retry
          </button>
        </div>
      </div>
    );
  }
  if (!data) return null;

  const chartData = data.series.map((p) => ({
    ...p,
    label: formatDayLabel(p.date),
  }));
  const pct = data.percent_change_vs_prev_week;
  const changeTone =
    pct === null ? "text-slate-800" : pct > 0 ? "text-emerald-600" : pct < 0 ? "text-rose-600" : "text-slate-800";

  const isRefreshing = loading && !!data;

  return (
    <div className="relative p-4 sm:p-6 max-w-5xl mx-auto z-10">
      {isRefreshing ? (
        <div
          className="fixed top-0 left-0 right-0 z-[60] h-0.5 motion-safe:animate-pulse"
          style={{ background: `linear-gradient(90deg, transparent, ${brandFillHex}, transparent)` }}
          aria-hidden
        />
      ) : null}
      <div className="mb-8 space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight bg-gradient-to-r from-slate-800 via-slate-900 to-indigo-800 bg-clip-text text-transparent">
              AI engagement
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600 leading-relaxed">{data.metric}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end sm:gap-2">
            <div className="flex items-center gap-1.5 rounded-xl border border-slate-200/80 bg-slate-100/60 p-1 shadow-inner">
              <span className="pl-1.5 pr-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                Chart range
              </span>
              {RANGE_OPTIONS.map((opt) => {
                const active = rangeDays === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => applyRange(opt.value)}
                    disabled={isRefreshing}
                    className={
                      "rounded-lg px-2.5 py-1.5 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/50 disabled:cursor-wait " +
                      (active
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-600 hover:bg-white/60 hover:text-slate-900")
                    }
                    aria-pressed={active}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              onClick={exportCsv}
              disabled={isRefreshing}
              className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200/80 bg-white/90 px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-white hover:shadow-md active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-indigo-400/30 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <DocumentArrowDownIcon className="h-4 w-4 text-slate-500" aria-hidden />
              Export CSV
            </button>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200/80 bg-white/90 px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-white hover:shadow-md active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-indigo-400/30 disabled:cursor-wait disabled:opacity-80"
            >
              <ArrowPathIcon
                className={`h-4 w-4 text-slate-500${isRefreshing ? " motion-safe:animate-spin" : ""}`}
                aria-hidden
              />
              {isRefreshing ? "Refreshing…" : "Refresh data"}
            </button>
          </div>
        </div>
        {lastUpdatedAt ? (
          <p className="flex items-center gap-1.5 text-xs text-slate-500">
            <ClockIcon className="h-3.5 w-3.5 text-slate-400" aria-hidden />
            Last updated {lastUpdatedAt.toLocaleString()}
          </p>
        ) : null}
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className={cardClass + " p-5"}>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Last 7 days</div>
          <div className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">
            {data.last_7_days_total}
          </div>
        </div>
        <div className={cardClass + " p-5"}>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Previous 7 days</div>
          <div className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">
            {data.previous_7_days_total}
          </div>
        </div>
        <div className={cardClass + " p-5 ring-1 ring-indigo-100/60"}>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Change vs previous week</div>
          <div className={`mt-1 text-3xl font-semibold tabular-nums ${changeTone}`}>
            {pct === null ? "—" : `${pct > 0 ? "+" : ""}${pct}%`}
          </div>
        </div>
      </div>

      {data.question_themes &&
        (data.question_themes.themes?.length ?? 0) > 0 && (
          <div className={cardClass + " p-4 sm:p-5 mb-6 ring-1 ring-slate-100/50"}>
            <h2 className="text-base font-semibold text-slate-800">What people ask about (estimate)</h2>
            <p className="mt-1.5 text-xs text-slate-500 leading-relaxed max-w-3xl">
              Keyword-based categories from saved user messages in the same period — not a full
              transcript. {data.question_themes.note}
              {data.question_themes.capped
                ? ` (Stopped after ${data.question_themes.user_messages_sampled} messages.)`
                : ` Sampled ${data.question_themes.user_messages_sampled} user messages.`}
            </p>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-3">
              <div className={innerStatClass}>
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Top question type</div>
                <div className="text-sm font-semibold text-slate-900 mt-1 line-clamp-2">
                  {data.question_themes.top_theme?.label ?? "—"}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {data.question_themes.top_theme != null
                    ? `${data.question_themes.top_theme.percent}% of sampled user messages`
                    : "—"}
                </div>
              </div>
              <div className={innerStatClass}>
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">General / uncategorized</div>
                <div className="text-2xl font-semibold tabular-nums text-slate-900">
                  {data.question_themes.general_other_percent != null
                    ? `${data.question_themes.general_other_percent}%`
                    : "—"}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">no keyword match</div>
              </div>
              <div className={innerStatClass}>
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Avg user messages / session</div>
                <div className="text-2xl font-semibold tabular-nums text-slate-900">
                  {data.question_themes.avg_user_messages_per_session != null
                    ? data.question_themes.avg_user_messages_per_session
                    : "—"}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {data.question_themes.sessions_with_user_messages != null
                    ? `${data.question_themes.sessions_with_user_messages} sessions with user text`
                    : ""}
                </div>
              </div>
            </div>

            <div className="mt-4 h-[min(28rem,60vh)] w-full min-h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={data.question_themes.themes.slice(0, 12)}
                  margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.35)" horizontal={false} />
                  <XAxis
                    type="number"
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: "#64748b" }}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={168}
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    interval={0}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(99, 102, 241, 0.06)" }}
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 12,
                      border: "1px solid #e2e8f0",
                      boxShadow: "0 10px 40px -10px rgba(15, 23, 42, 0.15)",
                    }}
                    formatter={(value: number, _n: string, item: { payload?: ThemeRow }) => {
                      const p = item?.payload;
                      return [`${value} (${p?.percent ?? 0}%)`, "User messages"];
                    }}
                  />
                  <Bar
                    dataKey="count"
                    name="User messages"
                    radius={[0, 6, 6, 0]}
                    maxBarSize={32}
                    animationDuration={800}
                    animationEasing="ease-out"
                  >
                    {data.question_themes.themes.slice(0, 12).map((t, i) => (
                      <Cell
                        key={t.id}
                        fill={THEME_BAR_COLORS[i % THEME_BAR_COLORS.length]}
                        className="transition-opacity"
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            {data.question_themes.themes.length > 12 ? (
              <p className="text-xs text-slate-500 mt-2">
                Showing top 12 of {data.question_themes.themes.length} categories (by message
                count).
              </p>
            ) : null}
          </div>
        )}

      {data.question_themes != null &&
        (data.question_themes.themes?.length ?? 0) === 0 && (
          <p
            className={
              "mb-6 rounded-2xl border border-dashed border-slate-300/70 bg-amber-50/40 px-4 py-3 text-sm text-slate-600 backdrop-blur-sm"
            }
          >
            {data.question_themes.note || "No question theme data for this period."}
          </p>
        )}

      <div className={cardClass + " p-4 sm:p-5 mb-6 overflow-hidden ring-1 ring-slate-100/50"}>
        <h2 className="text-base font-semibold text-slate-800">
          Daily completed AI responses (last {data.days} days)
        </h2>
        <p className="mt-0.5 text-xs text-slate-500">Hover a point to inspect the date and count</p>
        <div className="h-80 w-full min-h-[200px] mt-3">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={brandFillId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={brandFillHex} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={brandFillHex} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.4)" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: "#64748b" }}
                interval="preserveStartEnd"
                minTickGap={24}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 12, fill: "#64748b" }}
                width={36}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ stroke: brandPrimary, strokeWidth: 1, strokeOpacity: 0.35 }}
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 10px 40px -10px rgba(15, 23, 42, 0.15)",
                }}
                formatter={(value) => {
                  const n = typeof value === "number" ? value : Number(value);
                  return [Number.isFinite(n) ? n : 0, "Responses"];
                }}
                labelFormatter={(_label, items) => {
                  const p = items?.[0]?.payload as
                    | (SeriesPoint & { label: string })
                    | undefined;
                  return p?.date ?? "";
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                fill={`url(#${brandFillId})`}
                stroke="none"
                isAnimationActive
                animationDuration={900}
                animationEasing="ease-out"
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke={brandPrimary}
                strokeWidth={2.5}
                dot={false}
                activeDot={{
                  r: 6,
                  strokeWidth: 2,
                  stroke: "#fff",
                  fill: brandPrimary,
                }}
                name="Responses"
                isAnimationActive
                animationDuration={900}
                animationEasing="ease-out"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const { profile, loading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/admin/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return <PrakritiLoader message="Loading…" />;
  }
  if (!user) {
    return null;
  }
  if (!profile) {
    return <PrakritiLoader message="Loading profile…" />;
  }
  if (!profile.admin_privileges && profile.role !== "admin") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600">Admin privileges required.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden chat-grid-bg">
      <div
        className="pointer-events-none fixed inset-0 -z-0"
        aria-hidden
      >
        <div className="absolute -top-20 right-0 h-80 w-80 rounded-full bg-indigo-400/15 blur-3xl" />
        <div className="absolute top-1/3 -left-24 h-72 w-72 rounded-full bg-violet-400/12 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-64 w-64 rounded-full bg-cyan-300/10 blur-3xl" />
        <div className="absolute inset-0 bg-gradient-to-b from-slate-50/50 via-white/30 to-slate-100/40" />
      </div>
      <div className="relative z-10 border-b border-slate-200/70 bg-white/60 px-3 py-2.5 shadow-sm shadow-slate-200/30 backdrop-blur-md sm:px-6 sm:py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => router.push("/admin")}
              className="text-sm font-medium transition hover:opacity-80"
              style={{ color: "var(--brand-primary)" }}
            >
              Admin home
            </button>
            <span className="text-slate-300">|</span>
            <span className="text-sm text-slate-600">Analytics</span>
          </div>
          <button
            type="button"
            onClick={() => router.push("/")}
            className="text-sm text-slate-600 transition hover:text-slate-900 rounded-lg px-2 py-1 hover:bg-slate-100/80"
          >
            Back to chat
          </button>
        </div>
      </div>
      <Suspense fallback={<PrakritiLoader message="Loading analytics…" />}>
        <AnalyticsContent />
      </Suspense>
    </div>
  );
}
