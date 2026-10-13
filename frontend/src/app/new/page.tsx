"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type CaseView } from "@/lib/api";

const FILES = [
  { name: "notice", label: "ASMT-10 notice", hint: "PDF, or a photo/scan", accept: ".pdf,image/*" },
  { name: "gstr1", label: "GSTR-1", hint: "CSV template", accept: ".csv" },
  { name: "gstr3b", label: "GSTR-3B", hint: "CSV template", accept: ".csv" },
  { name: "gstr2b", label: "GSTR-2B", hint: "CSV template", accept: ".csv" },
];

const SAMPLES = [
  { id: "case_a", title: "Case A", text: "Output tax gap explained by a later credit note" },
  { id: "case_b", title: "Case B", text: "ITC gap, part late-filed supplier, part payable" },
  { id: "case_c", title: "Case C", text: "Phone photo of the notice (vision model)" },
];

export default function NewCase() {
  const router = useRouter();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function start(label: string, req: () => Promise<CaseView>) {
    setBusy(label);
    setError("");
    try {
      const v = await req();
      router.push(`/cases/${v.case.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy("");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New case</h1>
        <p className="text-sm text-muted-foreground">
          Upload the notice and your returns. Jawab reads the notice, takes the GSTIN from it and reconciles each ground.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload files</CardTitle>
          <CardDescription>Use the CSV templates in samples/jawab for the returns.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              const body = new FormData(e.currentTarget);
              start("upload", () => api<CaseView>("/cases", { method: "POST", body }));
            }}
          >
            {FILES.map((f) => (
              <div key={f.name} className="grid gap-1.5">
                <Label htmlFor={f.name}>{f.label}</Label>
                <Input id={f.name} name={f.name} type="file" accept={f.accept} required />
                <span className="text-xs text-muted-foreground">{f.hint}</span>
              </div>
            ))}
            <div className="sm:col-span-2">
              <Button type="submit" disabled={!!busy}>{busy === "upload" ? "Reading notice…" : "Create case"}</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Or try a synthetic sample</CardTitle>
          <CardDescription>Fictional businesses and GSTINs.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          {SAMPLES.map((s) => (
            <button
              key={s.id}
              disabled={!!busy}
              onClick={() => start(s.id, () => api<CaseView>(`/cases/sample/${s.id}`, { method: "POST" }))}
              className="rounded-lg border p-3 text-left transition-colors hover:bg-muted disabled:opacity-50"
            >
              <div className="font-medium">{busy === s.id ? "Reading notice…" : s.title}</div>
              <div className="text-xs text-muted-foreground">{s.text}</div>
            </button>
          ))}
        </CardContent>
      </Card>

      {busy && (
        <p className="text-sm text-muted-foreground">
          Reading the notice with Nemotron and reconciling returns. This can take a minute or two on the free tier.
        </p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
