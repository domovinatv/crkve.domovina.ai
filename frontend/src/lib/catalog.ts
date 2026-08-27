/**
 * Tipovi za statički katalog iz `public/data/`, koji piše
 * `scripts/34_export_static.py`. Ako se export promijeni, promijeni i ovo.
 *
 * DVIJE JEDINICE, jer su i u bazi dva različita skupa (6966 građevina naspram
 * 2358 pravnih osoba, veza N:1):
 *
 *   Church  GRAĐEVINA — ima koordinate uvijek, župu ne mora imati
 *   Parish  PRAVNA OSOBA — ima OIB i sjedište, građevinu ne mora imati
 *
 * Prazna polja se u exportu izostavljaju, pa je gotovo sve opcionalno.
 */

export type ChurchKind =
  | "crkva"
  | "kapela"
  | "katedrala"
  | "bazilika"
  | "svetiste"
  | "samostan"
  | "pravoslavna-crkva"
  | "dzamija"
  | "sinagoga"
  | "poklonac"
  | "ostalo";

/** Slim zapis iz crkve-index.json — dovoljno za kartu, popis i pretragu. */
export type ChurchIndexItem = {
  slug: string;
  name: string;
  kind: ChurchKind;
  lat: number;
  lng: number;
  titular?: string;
  city?: string;
  county?: string;
  denomination?: string;
  /** 1 = zaštićeno kulturno dobro */
  heritage?: 1;
  /** 1 = ima fotografiju s Commonsa */
  image?: 1;
  parish_slug?: string;
  is_parish_church?: 1;
};

/** Slim zapis iz zupe-index.json. */
export type ParishIndexItem = {
  slug: string;
  name: string;
  kind: string;
  /** Segment URL-a: "zupa" ili "ustanova". */
  route: "zupa" | "ustanova";
  /** Nula je NALAZ ("nema nijedne spojene građevine"), ne odsutan podatak. */
  church_count: number;
  has_parish_church: 0 | 1;
  short_name?: string;
  titular?: string;
  city?: string;
  county?: string;
  diocese?: string;
  community?: string;
  lat?: number;
  lng?: number;
};

/** Građevina unutar stranice pravne osobe. */
export type ParishChurchRef = {
  slug: string;
  name: string;
  kind: ChurchKind;
  city?: string;
  lat?: number;
  lng?: number;
  heritage_id?: string;
  is_parish_church?: 1;
  image?: 1;
};

/** crkva/<slug>.json */
export type Church = {
  id: number;
  slug: string;
  name: string;
  kind: ChurchKind;
  lat: number;
  lng: number;
  name_official?: string;
  religion?: string;
  denomination?: string;
  titular?: string;
  address?: string;
  city?: string;
  settlement?: string;
  municipality?: string;
  county?: string;
  postal_code?: string;
  geom_kind?: "node" | "way" | "relation";
  is_parish_church?: 1;
  osm_type?: string;
  osm_id?: number;
  wikidata_id?: string;
  wikipedia_url?: string;
  commons_image?: string;
  heritage_id?: string;
  heritage_status?: string;
  heritage_class?: string;
  heritage_desc?: string;
  unesco?: 1;
  year_built?: string;
  architect?: string;
  style?: string;
  phone?: string;
  email?: string;
  website?: string;
  geo_verified?: 1;
  geo_verify_m?: number;
  source?: string[];
  parish?: {
    slug: string;
    name: string;
    short_name?: string;
    kind: string;
    diocese?: string;
    /** Prazno = pravna osoba nema vlastitu stranicu; tada se ne linka. */
    route?: "zupa" | "ustanova";
  };
  siblings?: { slug: string; name: string; kind: ChurchKind; is_parish_church?: 1 }[];
};

/** zupa/<slug>.json i ustanova/<slug>.json */
export type Parish = {
  slug: string;
  name: string;
  kind: string;
  route: "zupa" | "ustanova";
  churches: ParishChurchRef[];
  church_count: number;
  has_parish_church: 0 | 1;
  short_name?: string;
  religion?: string;
  denomination?: string;
  titular?: string;
  oib?: string;
  diocese?: string;
  community?: string;
  address?: string;
  city?: string;
  county?: string;
  lat?: number;
  lng?: number;
  geocode_source?: string;
  registry_no?: string;
  registry_id?: number;
  registry_status?: string;
  registered_at?: string;
  leader_title?: string;
  phone?: string;
  email?: string;
  website?: string;
  google_maps_uri?: string;
  source?: string[];
};

/** biskupija/<slug>.json — jedini DERIVIRANI sloj, pa nosi i svoju mjeru. */
export type Diocese = {
  slug: string;
  name: string;
  kind?: string;
  religion?: string;
  denomination?: string;
  oib?: string;
  seat?: string;
  parish_count?: number;
  /** 1 = ima deriviran teritorij (poligon). 15 od 70 zapisa. */
  has_area?: 0 | 1;
  area_km2?: number;
  population?: number;
  settlement_count?: number;
  area_parish_count?: number;
  area_church_count?: number;
  /** Kako je granica derivirana — teritorij nije preslikan nego izračunat. */
  method?: string;
  /** Slaganje s OSM granicom, u postocima. NULL ako OSM tu granicu nema. */
  osm_agreement?: number;
  listed_parish_count?: number;
  parishes?: ParishIndexItem[];
};

export type Manifest = {
  schema_version: number;
  generated_at: string;
  counts: {
    crkve: number;
    pravne_osobe_sa_stranicom: number;
    zupe: number;
    ustanove: number;
    biskupije: number;
    biskupije_s_teritorijem: number;
  };
};

/** stats.json — mjera iz scripts/40, jedino mjesto gdje se brojke računaju. */
export type Stats = {
  crkve_ukupno: number;
  crkve_s_koordinatama: number;
  crkve_s_titularom: number;
  crkve_sa_zastitom: number;
  crkve_sa_slikom: number;
  crkve_s_wikipedijom: number;
  crkve_sa_zupom: number;
  zupne_crkve: number;
  crkve_s_tlocrtom: number;
  crkve_lokacija_potvrdjena: number;
  geo_konflikti: number;
  pravne_osobe_ukupno: number;
  zupe_katolicke: number;
  zupe_aktivne: number;
  zupe_s_koordinatama: number;
  zupe_s_oib: number;
  zupe_s_telefonom: number;
  zupe_s_webom: number;
  zupe_bez_zupne_crkve: number;
  zupe_bez_ijedne_crkve: number;
  biskupije_i_zajednice: number;
  bastina_nespojena: number;
  zupe_po_izvoru_koordinata: Record<string, number>;
  po_tipu: Record<string, number>;
  po_zupaniji: Record<string, number>;
  po_konfesiji: Record<string, number>;
  zupe_po_biskupiji: Record<string, number>;
  najcesci_titulari: Record<string, number>;
};

/** Omotač indeksa — brojka putuje uz podatak, ne računa je potrošač. */
export type IndexFile<T> = { count: number; items: T[] };
