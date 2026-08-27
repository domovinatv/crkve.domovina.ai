import { leadFields, leadSubject } from "@/data/lead-form";
import { site } from "@/data/site";
import type { LeadInput } from "./lead-schema";

function rows(data: LeadInput): Array<[string, string]> {
  return leadFields.map((field) => [field.label, String(data[field.name] ?? "").trim() || "—"]);
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatText(data: LeadInput) {
  return rows(data)
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
}

function formatHtml(data: LeadInput) {
  const body = rows(data)
    .map(
      ([label, value]) =>
        `<tr><td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:600;white-space:nowrap;">${escapeHtml(
          label,
        )}</td><td style="padding:8px 12px;border-bottom:1px solid #eee;">${escapeHtml(
          value,
        ).replace(/\n/g, "<br>")}</td></tr>`,
    )
    .join("");

  return `<div style="font-family:Arial,Helvetica,sans-serif;color:#222;">
  <h2 style="margin:0 0 16px;">${escapeHtml(leadSubject)}</h2>
  <table style="border-collapse:collapse;width:100%;max-width:600px;font-size:14px;">${body}</table>
  <p style="margin-top:16px;font-size:12px;color:#777;">Poslano s web stranice ${escapeHtml(site.name)}.</p>
</div>`;
}

/**
 * Šalje upit na e-mail klijenta putem Resend API-ja.
 *
 * VAŽNO: na Cloudflare Workeru nema pravog process.env — Nitro ga popunjava
 * iz Worker env bindinga. Ako RESEND_API_KEY nije postavljen kao secret,
 * upit se SAMO zapiše u log i nikad ne stigne na mail. Skill /ship to provjerava
 * prije deploya; ako mijenjaš ručno: wrangler secret put RESEND_API_KEY
 */
export async function deliverLead(data: LeadInput) {
  const text = formatText(data);
  const apiKey = process.env["RESEND_API_KEY"];
  const replyTo = leadFields.find((f) => f.type === "email")?.name;

  if (!apiKey) {
    console.warn(
      `[LEAD] RESEND_API_KEY nije postavljen — upit NIJE poslan mailom.\n${leadSubject}\n${text}`,
    );
    return { delivered: false as const };
  }

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: process.env["RESEND_FROM"] ?? `${site.name} web <onboarding@resend.dev>`,
      to: [process.env["LEAD_RECIPIENT"] ?? site.email],
      reply_to: replyTo ? String(data[replyTo] ?? "").trim() || undefined : undefined,
      subject: leadSubject,
      text,
      html: formatHtml(data),
    }),
  });

  if (!response.ok) {
    console.error(`[LEAD] Resend error ${response.status}\n${await response.text()}\n${text}`);
    throw new Error("Upit trenutno nije moguće poslati.");
  }

  return { delivered: true as const };
}
