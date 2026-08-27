import { z } from "zod";

import { leadFields, requireOneContact, type LeadField } from "@/data/lead-form";

function fieldSchema(field: LeadField) {
  let base = z.string().trim();

  if (field.type === "email") base = base.email("Unesite ispravnu e-mail adresu");
  if (field.maxLength) base = base.max(field.maxLength, `Najviše ${field.maxLength} znakova`);
  if (field.type === "select" && field.options?.length) {
    // Select se validira kao slobodan string pa provjerava protiv popisa,
    // da poruka o grešci ostane čitljiva umjesto Zod enum dumpa.
    return base.refine((v) => !v || field.options!.includes(v), {
      message: `Odaberite: ${field.label}`,
    });
  }

  if (field.required) {
    return base.min(field.type === "tel" ? 6 : 2, `${field.label} je obavezno polje`);
  }
  return base.optional().or(z.literal(""));
}

const shape = Object.fromEntries(leadFields.map((f) => [f.name, fieldSchema(f)]));

const hasEmail = leadFields.some((f) => f.type === "email" && !f.required);
const hasPhone = leadFields.some((f) => f.type === "tel" && !f.required);

const base = z.object(shape);

export const leadSchema =
  requireOneContact && hasEmail && hasPhone
    ? base.refine(
        (data) => {
          const email = leadFields.find((f) => f.type === "email")?.name;
          const phone = leadFields.find((f) => f.type === "tel")?.name;
          return Boolean(
            (email && String(data[email] ?? "").trim()) ||
            (phone && String(data[phone] ?? "").trim()),
          );
        },
        {
          message: "Unesite barem jedan način kontakta – telefon ili e-mail",
          path: ["form"],
        },
      )
    : base;

export type LeadInput = Record<string, string | undefined>;
