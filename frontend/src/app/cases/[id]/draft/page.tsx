"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Banner, CostPanel } from "@/components/case-bits";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, inr, type CaseView, type Issue, type Source } from "@/lib/api";

const ISSUE_LABEL: Record<Issue["kind"], string> = {
  number: "Amount not found in the computed figures",
  citation: "Citation is not a stored source",
  url: "URL is not a stored source",
};

export default function DraftPage() {
  const { id } = useParams<{ id: string }>();
  const [view, setView] = useState<CaseView | null>(null);
  const [text, setText] = useState("");
  const [paidOn, setPaidOn] = useState(new Date().toISOString().slice(0, 10));
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = (v: CaseView) => {
    setView(v);
    setText(v.case.draft ?? "");
    if (v.case.paid_on) setPaidOn(v.case.paid_on);
  };

  useEffect(() => {
    api<CaseView>(`/cases/${id}`).then(load).catch((e) => setError(e.message));
  }, [id]);

  async function act(label: string, path: string, init: Parameters<typeof api>[1]) {
    setBusy(label);
    setError("");
    try {
      load(await api<CaseView>(path, init));
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  if (!view) return <p className="text-sm text-muted-foreground">{error || "Loading…"}</p>;
  const c = view.case;
  const payable = c.grounds.filter((g) => g.payable);
  const dirty = text !== (c.draft ?? "");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div>
          <Link href={`/cases/${id}`} className="text-sm text-muted-foreground hover:underline">← {c.notice.notice_ref}</Link>
          <h1 className="text-2xl font-semibold tracking-tight">ASMT-11 reply draft</h1>
        </div>
        {c.draft && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setEditing(!editing)}>{editing ? "Preview" : "Edit"}</Button>
            <Button variant="outline" onClick={() => window.print()} disabled={dirty}>Print / save PDF</Button>
          </div>
        )}
      </div>

      <div className="print:hidden"><Banner /></div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-4">
          {c.draft && (
            <div className={`rounded-md px-3 py-2 text-sm print:hidden ${c.issues.length
              ? "bg-destructive/10 text-destructive" : "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"}`}>
              {c.issues.length
                ? `${c.issues.length} unverified claim${c.issues.length > 1 ? "s" : ""} highlighted in red. Fix or remove before sending.`
                : "Every amount and citation checks out against the computed figures and stored sources."}
            </div>
          )}

          {editing ? (
            <div className="space-y-2 print:hidden">
              <Textarea value={text} onChange={(e) => setText(e.target.value)} className="min-h-[60vh] font-mono text-sm" />
              <Button disabled={!dirty || !!busy}
                      onClick={() => act("verify", `/cases/${id}/draft`, { method: "PUT", json: { text } })}>
                {busy === "verify" ? "Checking…" : "Save and re-verify"}
              </Button>
            </div>
          ) : c.draft ? (
            <article className="rounded-xl bg-card p-6 text-sm leading-relaxed whitespace-pre-wrap ring-1 ring-foreground/10 print:p-0 print:ring-0">
              <Marked text={c.draft} issues={c.issues} sources={view.sources} />
            </article>
          ) : (
            <p className="rounded-xl p-6 text-sm text-muted-foreground ring-1 ring-foreground/10">
              No draft yet. Set the payment date and generate it.
            </p>
          )}
          {error && <p className="text-sm text-destructive print:hidden">{error}</p>}
        </div>

        <aside className="space-y-4 print:hidden">
          <Card size="sm">
            <CardHeader><CardTitle>{c.draft ? "Regenerate" : "Generate"}</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="grid gap-1.5">
                <Label htmlFor="paid">DRC-03 payment date</Label>
                <Input id="paid" type="date" value={paidOn} onChange={(e) => setPaidOn(e.target.value)} />
                <span className="text-xs text-muted-foreground">Interest under section 50 runs to this date.</span>
              </div>
              {payable.map((g) => (
                <div key={g.ground.ground_no} className="flex justify-between tabular-nums">
                  <span>Ground {g.ground.ground_no}</span>
                  <span>{inr(g.payable_total)} tax{g.interest_total != null && ` + ${inr(g.interest_total)} interest`}</span>
                </div>
              ))}
              <Button className="w-full" disabled={!!busy}
                      onClick={() => act("draft", `/cases/${id}/draft`, { method: "POST", json: { paid_on: paidOn } })}>
                {busy === "draft" ? "Drafting with Nemotron…" : c.draft ? "Regenerate draft" : "Generate draft"}
              </Button>
              {busy === "draft" && <p className="text-xs text-muted-foreground">Usually 1–3 minutes on the free tier.</p>}
            </CardContent>
          </Card>
          <CostPanel rows={view.cost} />
        </aside>
      </div>
    </div>
  );
}

/** Draft text with red marks on verifier issues and hover cards on valid [S<id>] citations. */
function Marked({ text, issues, sources }: { text: string; issues: Issue[]; sources: Source[] }) {
  const byId = new Map(sources.map((s) => [s.id, s]));
  const marks: { start: number; end: number; issue?: Issue; source?: Source }[] = issues.map((i) => ({ ...i, issue: i }));
  for (const m of text.matchAll(/\[S(\d+)\]/g)) {
    const source = byId.get(Number(m[1]));
    if (source) marks.push({ start: m.index, end: m.index + m[0].length, source });
  }
  marks.sort((a, b) => a.start - b.start);

  const out: React.ReactNode[] = [];
  let at = 0;
  for (const m of marks) {
    if (m.start < at) continue; // overlapping mark
    out.push(text.slice(at, m.start));
    const span = text.slice(m.start, m.end);
    out.push(m.issue ? (
      <mark key={m.start} title={ISSUE_LABEL[m.issue.kind]}
            className="rounded bg-destructive/15 px-0.5 text-destructive underline decoration-wavy print:bg-transparent">
        {span}
      </mark>
    ) : (
      <HoverCard key={m.start} openDelay={100}>
        <HoverCardTrigger asChild>
          <a href={m.source!.url} target="_blank" rel="noreferrer"
             className="rounded bg-primary/10 px-0.5 font-mono text-xs text-primary no-underline">{span}</a>
        </HoverCardTrigger>
        <HoverCardContent className="w-80 space-y-1 text-xs">
          <p className="font-medium text-sm">{m.source!.title}</p>
          <p className="break-all text-muted-foreground">{m.source!.url}</p>
          <p className="line-clamp-5">{m.source!.snippet}</p>
        </HoverCardContent>
      </HoverCard>
    ));
    at = m.end;
  }
  out.push(text.slice(at));
  return <>{out}</>;
}
