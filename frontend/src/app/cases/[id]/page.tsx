"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CostPanel, StatusBadge } from "@/components/case-bits";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, heads, HEADS, inr, type CaseView, type GroundState } from "@/lib/api";

const CAUSE_LABEL: Record<string, string> = {
  timing_difference: "Timing difference",
  credit_note: "Credit note",
  amendment_later_period: "Amendment in a later period",
  itc_reversed: "ITC reversed",
  genuine_short_payment: "Genuine short payment",
};

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [view, setView] = useState<CaseView | null>(null);
  const [selected, setSelected] = useState(1);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<CaseView>(`/cases/${id}`).then(setView).catch((e) => setError(e.message));
  }, [id]);

  async function act(label: string, path: string, init?: Parameters<typeof api>[1]) {
    setBusy(label);
    setError("");
    try {
      setView(await api<CaseView>(path, init));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  if (!view) return <p className="text-sm text-muted-foreground">{error || "Loading…"}</p>;
  const { case: c, sources, cost } = view;
  const g = c.grounds.find((x) => x.ground.ground_no === selected) ?? c.grounds[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">ASMT-10 · FY {c.notice.financial_year}</p>
          <h1 className="text-2xl font-semibold tracking-tight">{c.notice.notice_ref}</h1>
          <p className="text-sm text-muted-foreground">
            GSTIN <span className="font-mono">{c.notice.gstin}</span> · issued {c.notice.issue_date} · reply due{" "}
            <span className="font-medium text-foreground">{c.notice.reply_due_date}</span>
            {c.notice.due_date_computed && " (not stated; computed as issue date + 30 days)"}
          </p>
        </div>
        <Button asChild>
          <Link href={`/cases/${id}/draft`}>{c.draft ? "Open draft reply" : "Draft reply"}</Link>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-6">
          <div className="rounded-xl ring-1 ring-foreground/10">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Officer says</TableHead>
                  <TableHead>Our figure</TableHead>
                  <TableHead>Difference</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {c.grounds.map((x) => (
                  <TableRow
                    key={x.ground.ground_no}
                    onClick={() => setSelected(x.ground.ground_no)}
                    data-state={x === g ? "selected" : undefined}
                    className="cursor-pointer"
                  >
                    <TableCell>{x.ground.ground_no}</TableCell>
                    <TableCell>{x.ground.tax_period}</TableCell>
                    <TableCell className="tabular-nums">{heads(x.ground.officer_amount)}</TableCell>
                    <TableCell className="tabular-nums">{x.recon ? heads(x.recon.our_amount) : "—"}</TableCell>
                    <TableCell className="tabular-nums">{x.recon ? heads(x.recon.difference) : "—"}</TableCell>
                    <TableCell><StatusBadge status={x.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {g && (
            <GroundDetail
              c={c}
              g={g}
              sources={sources.filter((s) => g.source_ids.includes(s.id))}
              busy={busy}
              onAnalyse={() => act("analyse", `/cases/${id}/grounds/${g.ground.ground_no}/analyse`, { method: "POST" })}
              onConfirm={(facts) =>
                act("confirm", `/cases/${id}/grounds/${g.ground.ground_no}/confirmed`, { method: "PUT", json: { facts } })}
            />
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <aside className="space-y-4">
          <CostPanel rows={cost} />
        </aside>
      </div>
    </div>
  );
}

function GroundDetail({ c, g, sources, busy, onAnalyse, onConfirm }: {
  c: CaseView["case"];
  g: GroundState;
  sources: CaseView["sources"];
  busy: string;
  onAnalyse: () => void;
  onConfirm: (facts: string[]) => void;
}) {
  const [extra, setExtra] = useState("");
  const candidates = [
    ...(g.recon?.evidence.map((e) => ({ text: e.text, tag: "From your returns", sub: heads(e.amount) })) ?? []),
    ...g.causes.map((c) => ({ text: c.why, tag: CAUSE_LABEL[c.cause] ?? c.cause, sub: `Proof: ${c.proof_document}` })),
    ...g.confirmed.filter((f) => !g.recon?.evidence.some((e) => e.text === f) && !g.causes.some((c) => c.why === f))
      .map((f) => ({ text: f, tag: "Added by you", sub: "" })),
  ];
  const toggle = (f: string) => onConfirm(g.confirmed.includes(f) ? g.confirmed.filter((x) => x !== f) : [...g.confirmed, f]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">Ground {g.ground.ground_no} <StatusBadge status={g.status} /></CardTitle>
        <CardDescription className="italic">“{g.ground.description}”</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {!g.recon ? (
          <p className="text-sm text-muted-foreground">
            This ground is outside the two supported categories. The draft will mark it for review by your CA.
          </p>
        ) : (
          <>
            <section className="space-y-2">
              <h3 className="text-sm font-medium">Reconciliation by month, FY {c.notice.financial_year}</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month</TableHead>
                    {HEADS.map((h) => <TableHead key={h} className="text-right uppercase">{h}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {g.recon.periods.map((p) => (
                    <TableRow key={p.period} data-state={p.period === g.ground.tax_period ? "selected" : undefined}>
                      <TableCell>{p.period}</TableCell>
                      {HEADS.map((h) => (
                        <TableCell key={h} className={`text-right tabular-nums ${Number(p[h]) < 0 ? "text-emerald-700 dark:text-emerald-400" : ""}`}>
                          {inr(p[h])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                  <TableRow className="font-medium">
                    <TableCell>Net for year</TableCell>
                    {HEADS.map((h) => <TableCell key={h} className="text-right tabular-nums">{inr(g.recon!.fy_net[h])}</TableCell>)}
                  </TableRow>
                </TableBody>
              </Table>
              <p className="text-xs text-muted-foreground">
                Positive = against you. A negative month offsets an earlier excess.
                {g.payable && <> Unexplained after netting: <span className="font-medium text-foreground">{heads(g.payable)}</span>.</>}
              </p>
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-medium">Facts for the reply</h3>
                <Button size="sm" variant="outline" disabled={!!busy} onClick={onAnalyse}>
                  {busy === "analyse" ? "Finding causes and sources…" : g.analysed ? "Re-run analysis" : "Suggest causes & find sources"}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">Only ticked facts go into the draft.</p>
              <ul className="space-y-2">
                {candidates.map((f) => (
                  <li key={f.text}>
                    <label className="flex cursor-pointer gap-3 rounded-lg border p-3 hover:bg-muted/50">
                      <input
                        type="checkbox"
                        className="mt-1 size-4 accent-primary"
                        checked={g.confirmed.includes(f.text)}
                        disabled={!!busy}
                        onChange={() => toggle(f.text)}
                      />
                      <span className="space-y-0.5 text-sm">
                        <span className="block text-xs font-medium text-muted-foreground">{f.tag}</span>
                        <span className="block">{f.text}</span>
                        {f.sub && <span className="block text-xs text-muted-foreground">{f.sub}</span>}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (extra.trim()) onConfirm([...g.confirmed, extra.trim()]);
                  setExtra("");
                }}
              >
                <Input value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Add a fact you can prove, e.g. a document reference" />
                <Button type="submit" variant="outline" disabled={!!busy}>Add</Button>
              </form>
            </section>

            <section className="space-y-2">
              <h3 className="text-sm font-medium">Sources found</h3>
              {!sources.length && <p className="text-sm text-muted-foreground">None yet. Run the analysis to search official GST sites.</p>}
              <ul className="space-y-2">
                {sources.map((s) => (
                  <li key={s.id} className="rounded-lg border p-3 text-sm">
                    <span className="mr-2 font-mono text-xs text-muted-foreground">S{s.id}</span>
                    <a href={s.url} target="_blank" rel="noreferrer" className="font-medium underline-offset-4 hover:underline">{s.title}</a>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{s.snippet}</p>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </CardContent>
    </Card>
  );
}
