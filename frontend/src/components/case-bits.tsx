import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type CostRow, type Status } from "@/lib/api";

const STATUS: Record<Status, { label: string; className: string }> = {
  explained: { label: "Explained", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" },
  partly_explained: { label: "Partly explained", className: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" },
  payable: { label: "Payable", className: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300" },
  needs_ca: { label: "Needs CA review", className: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300" },
};

export function StatusBadge({ status }: { status: Status }) {
  const s = STATUS[status];
  return <Badge className={s.className}>{s.label}</Badge>;
}

export function CostPanel({ rows }: { rows: CostRow[] }) {
  const tokens = rows.reduce((n, r) => n + r.input_tokens + r.output_tokens, 0);
  const cost = rows.reduce((n, r) => n + Number(r.cost), 0); // display total only; billing maths is server-side
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Cost for this case</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-semibold tabular-nums">${cost.toFixed(4)}</span>
          <span className="text-muted-foreground tabular-nums">{tokens.toLocaleString()} tokens</span>
        </div>
        {rows.map((r) => (
          <div key={r.tier} className="flex justify-between text-muted-foreground tabular-nums">
            <span className="capitalize">{r.tier} · {r.calls} call{r.calls === 1 ? "" : "s"}</span>
            <span>{(r.input_tokens + r.output_tokens).toLocaleString()} tok</span>
          </div>
        ))}
        {!rows.length && <p className="text-muted-foreground">No model calls yet.</p>}
      </CardContent>
    </Card>
  );
}

export function Banner() {
  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
      Draft for review by you or a CA. Not legal advice. Nothing is filed automatically.
    </div>
  );
}
