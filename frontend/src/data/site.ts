/**
 * Središnji podaci o projektu. Sve što se pojavljuje u headeru, footeru,
 * meta tagovima i structured dataju čita se odavde — nikad hardkodirano
 * u komponenti.
 *
 * Ovo NIJE web lokalnog biznisa (za što je template pisan) nego katalog
 * otvorenih podataka, pa nema telefona, adrese ni radnog vremena.
 */
export const site = {
  name: "crkve.domovina.ai",
  fullName: "Katalog crkava i sakralnih objekata u Hrvatskoj",
  slogan: "Svaka crkva, kapela i župa u Hrvatskoj — na jednom mjestu, iz javnih izvora",

  /** Produkcijski origin, bez završnog "/". Canonical i og:url. */
  url: "https://crkve.domovina.ai",

  /** Za footer i /o-projektu. */
  repo: "https://github.com/domovinatv/crkve.domovina.ai",
  karta: "https://gis.domovina.ai",
  email: "",

  /** Licenca podataka — OSM je ODbL i nameće share-alike, vidi LICENSE-DATA. */
  licence: "ODbL 1.0 (OpenStreetMap) + CC-BY izvori",
} as const;

/**
 * Glavna navigacija. Svaka ruta mora postojati u src/routes/ —
 * TanStack Router neće kompajlirati link na nepostojeću rutu.
 */
export const nav = [
  { label: "Karta", to: "/karta" },
  { label: "Crkve", to: "/crkve" },
  { label: "Župe", to: "/zupe" },
  { label: "Biskupije", to: "/biskupije" },
  { label: "Brojke", to: "/brojke" },
  { label: "O projektu", to: "/o-projektu" },
] as const;

/** Izvori podataka — ispisuju se na /o-projektu i u Dataset structured dataju. */
export const izvori = [
  {
    naziv: "OpenStreetMap (Overpass API)",
    sto: "Jedini izvor s koordinatama za sve građevine; 5256 zapisa su tlocrti, ne točke.",
    licenca: "ODbL 1.0",
    url: "https://www.openstreetmap.org/copyright",
  },
  {
    naziv: "Ministarstvo pravosuđa i uprave — evidencije vjerskih zajednica",
    sto: "Jedini strojno čitljiv popis župa u RH: pravne osobe Katoličke Crkve i ostale vjerske zajednice, s OIB-om.",
    licenca: "Otvorena dozvola",
    url: "https://data.gov.hr/",
  },
  {
    naziv: "Ministarstvo kulture i medija — Registar kulturnih dobara",
    sto: "Zaštita i klasifikacija sakralne baštine. Nema koordinate, pa se spaja heuristikom.",
    licenca: "Otvorena dozvola",
    url: "https://data.gov.hr/",
  },
  {
    naziv: "Wikidata / Wikimedia Commons",
    sto: "Fotografije, poveznice na Wikipediju, arhitekt i godina gradnje.",
    licenca: "CC0",
    url: "https://www.wikidata.org/",
  },
] as const;
