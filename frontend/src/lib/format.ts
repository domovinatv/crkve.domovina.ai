import type { ChurchKind } from "./catalog";

/**
 * Hrvatski nazivi kanonskih tipova iz `src/kinds.py`. Skup je zatvoren —
 * ako se ondje doda tip, doda se i ovdje.
 */
export const KIND_LABEL: Record<ChurchKind, string> = {
  crkva: "Crkva",
  kapela: "Kapela",
  katedrala: "Katedrala",
  bazilika: "Bazilika",
  svetiste: "Svetište",
  samostan: "Samostan",
  "pravoslavna-crkva": "Pravoslavna crkva",
  dzamija: "Džamija",
  sinagoga: "Sinagoga",
  poklonac: "Poklonac",
  ostalo: "Ostalo",
};

/** Množina za naslove popisa. */
export const KIND_PLURAL: Record<ChurchKind, string> = {
  crkva: "Crkve",
  kapela: "Kapele",
  katedrala: "Katedrale",
  bazilika: "Bazilike",
  svetiste: "Svetišta",
  samostan: "Samostani",
  "pravoslavna-crkva": "Pravoslavne crkve",
  dzamija: "Džamije",
  sinagoga: "Sinagoge",
  poklonac: "Poklonci",
  ostalo: "Ostalo",
};

/** Vrste pravnih osoba iz `parishes.kind`. */
export const PARISH_KIND_LABEL: Record<string, string> = {
  zupa: "Župa",
  samostan: "Samostan",
  "crkvena-opcina": "Crkvena općina",
  svetiste: "Svetište",
  parohija: "Parohija",
  dzemat: "Džemat",
};

/** OSM `denomination` → hrvatski. Nepoznato se ispisuje kako jest. */
const DENOMINATION_LABEL: Record<string, string> = {
  roman_catholic: "rimokatolička",
  catholic: "katolička",
  greek_catholic: "grkokatolička",
  serbian_orthodox: "srpska pravoslavna",
  orthodox: "pravoslavna",
  evangelical: "evangelička",
  lutheran: "luteranska",
  reformed: "reformirana",
  baptist: "baptistička",
  pentecostal: "pentekostna",
  adventist: "adventistička",
  seventh_day_adventist: "adventistička",
  jehovahs_witness: "Jehovini svjedoci",
  mormon: "mormonska",
};

export function denominationLabel(value?: string): string | undefined {
  if (!value) return undefined;
  return DENOMINATION_LABEL[value] ?? value.replace(/_/g, " ");
}

/** OSM primitiv → što to znači za točnost lokacije. */
export function geomKindLabel(value?: string): string | undefined {
  if (value === "way" || value === "relation") return "tlocrt građevine";
  if (value === "node") return "točka";
  return undefined;
}

/**
 * Hrvatska sklonidba uz broj: 1 crkva, 2–4 crkve, 5+ crkava — i to po
 * ZADNJOJ znamenki, pa 21 ide u jedninu a 11 u množinu. Bez ovoga se dobiju
 * rečenice tipa „1 spojenih građevina", koje su bile u prvom deployu.
 */
export function sklon(n: number, one: string, few: string, many: string): string {
  const d1 = n % 10;
  const d2 = n % 100;
  if (d2 >= 11 && d2 <= 14) return many;
  if (d1 === 1) return one;
  if (d1 >= 2 && d1 <= 4) return few;
  return many;
}

/** Broj + ispravno sklonjena imenica: „3 građevine". */
export function broj(n: number, one: string, few: string, many: string): string {
  return `${num(n)} ${sklon(n, one, few, many)}`;
}

const NF = new Intl.NumberFormat("hr-HR");
export const num = (n: number) => NF.format(n);

/** "12.345,6 km²" bez lažne preciznosti. */
export const km2 = (n: number) => `${NF.format(Math.round(n))} km²`;

export const pct = (n: number) => `${n.toFixed(1).replace(".", ",")} %`;

/** ISO datum → "12. studenoga 2004." */
export function datum(iso?: string): string | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("hr-HR", { dateStyle: "long" }).format(d);
}

/**
 * Za pretragu bez dijakritike: "Šibenik" i "Sibenik" moraju pogađati isto.
 * Isti postupak kao FTS5 `remove_diacritics 2` u bazi.
 */
export function foldHr(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d");
}
