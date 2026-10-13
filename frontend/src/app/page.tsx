"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/case-bits";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type CaseRow } from "@/lib/api";

export default function Dashboard() {
  const [rows, setRows] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<CaseRow[]>("/cases").then(setRows).catch((e) => setError(e.message));
  }, []);

  const totalCost = (rows ?? []).reduce((n, r) => n + Number(r.cost), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Notices</h1>
          <p className="text-sm text-muted-foreground">ASMT-10 scrutiny notices and their reply drafts.</p>
        </div>
        <Button asChild>
          <Link href="/new">New case</Link>
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">Could not reach the API: {error}</p>}

      <div className="rounded-xl ring-1 ring-foreground/10">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Notice</TableHead>
              <TableHead>GSTIN</TableHead>
              <TableHead>Reply due</TableHead>
              <TableHead>Grounds</TableHead>
              <TableHead>Draft</TableHead>
              <TableHead className="text-right">Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows?.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <Link href={`/cases/${r.id}`} className="font-medium underline-offset-4 hover:underline">
                    {r.notice_ref}
                  </Link>
                </TableCell>
                <TableCell className="font-mono text-xs">{r.gstin}</TableCell>
                <TableCell>
                  <span className={r.days_left < 7 ? "font-medium text-destructive" : ""}>
                    {r.days_left < 0 ? `${-r.days_left} days overdue` : `${r.days_left} days left`}
                  </span>
                  <span className="block text-xs text-muted-foreground">{r.reply_due_date}</span>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {r.statuses.map((s, i) => <StatusBadge key={i} status={s} />)}
                  </div>
                </TableCell>
                <TableCell className="text-sm">
                  {!r.has_draft ? <span className="text-muted-foreground">Not drafted</span>
                    : r.issues ? <span className="text-destructive">{r.issues} unverified</span>
                    : <span className="text-emerald-700 dark:text-emerald-400">Verified</span>}
                </TableCell>
                <TableCell className="text-right tabular-nums">${Number(r.cost).toFixed(4)}</TableCell>
              </TableRow>
            ))}
            {rows?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  No notices yet. <Link href="/new" className="underline">Start a case</Link>.
                </TableCell>
              </TableRow>
            )}
            {!rows && !error && (
              <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">Loading…</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {!!rows?.length && (
        <p className="text-right text-sm text-muted-foreground tabular-nums">Total model cost: ${totalCost.toFixed(4)}</p>
      )}
    </div>
  );
}
