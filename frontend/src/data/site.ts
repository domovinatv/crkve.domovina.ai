/**
 * Središnji podaci o klijentu. SVE kontakt informacije mijenjaju se ovdje
 * i nigdje drugdje — komponente ih uvijek čitaju iz ovog objekta.
 *
 * Popunjava skill /intake iz BRIEF.md. Vrijednosti s "TODO" znače da
 * podatak još nije prikupljen — ne izmišljaj ga.
 */
export const site = {
  name: "TODO",
  fullName: "TODO",
  slogan: "TODO",

  /** Produkcijski origin, bez završnog "/". Koristi se za canonical i og:url. */
  url: "https://TODO.hr",

  street: "TODO",
  city: "TODO",
  postalCode: "TODO",

  phone: "TODO",
  phoneHref: "tel:+385TODO",
  email: "TODO",
  emailHref: "mailto:TODO",

  /** Prazan string = link se ne prikazuje. Ne izmišljaj profile. */
  instagram: "",
  facebook: "",

  /** Prazno = sekcija s kartom se ne renderira. */
  mapsUrl: "",
  mapsEmbedUrl: "",

  /** Za impressum i privatnost. Prazno = redak se preskače. */
  legalName: "",
  oib: "",
} as const;

/**
 * Glavna navigacija. Rute moraju postojati u src/routes/ —
 * TanStack Router tipovi neće kompajlirati link na nepostojeću rutu.
 */
export const nav = [
  { label: "Naslovnica", to: "/" },
  { label: "O nama", to: "/o-nama" },
  { label: "Kontakt", to: "/kontakt" },
] as const;

/** Radno vrijeme. Prazan niz = sekcija se ne renderira. */
export const openingHours: { days: string; hours: string }[] = [];
