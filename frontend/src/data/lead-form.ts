/**
 * Definicija polja kontakt/upit forme. Jedan izvor istine — iz ovoga se
 * generiraju i Zod validacija (src/lib/lead-schema.ts) i UI (LeadDialog).
 *
 * Popunjava skill /intake prema sekciji "Forma" u BRIEF.md.
 * Dodavanje polja ovdje je jedini korak — ne diraj schemu ni komponentu.
 */
export type LeadField = {
  /** Ključ u payloadu i u mailu. camelCase, bez dijakritike. */
  name: string;
  /** Vidljiva oznaka iznad polja i u mailu. */
  label: string;
  type: "text" | "email" | "tel" | "textarea" | "select";
  required?: boolean;
  maxLength?: number;
  /** Samo za type: "select". */
  options?: readonly string[];
  placeholder?: string;
  /** Kratka pomoć ispod polja. */
  hint?: string;
};

export const leadFields: readonly LeadField[] = [
  { name: "name", label: "Ime i prezime", type: "text", required: true, maxLength: 100 },
  { name: "phone", label: "Telefon", type: "tel", maxLength: 30 },
  { name: "email", label: "E-mail", type: "email", maxLength: 255 },
  {
    name: "message",
    label: "Poruka",
    type: "textarea",
    maxLength: 1000,
    placeholder: "Kako vam možemo pomoći?",
  },
] as const;

/** Prefiks subjecta maila koji stiže klijentu. */
export const leadSubject = "Novi upit s weba";

/**
 * Ako su prisutna i email i tel polja, a nijedno nije required,
 * forma traži barem jedan od njih. Postavi na false da isključiš.
 */
export const requireOneContact = true;
