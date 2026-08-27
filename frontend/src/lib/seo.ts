import { site } from "@/data/site";

/** Relativan path → apsolutni URL (canonical i og:url traže apsolutni). */
function abs(path: string) {
  return path.startsWith("http") ? path : `${site.url.replace(/\/$/, "")}${path}`;
}

type MetaArgs = {
  /** Puni <title>. Jedinstven po stranici. */
  title: string;
  /** 140–160 znakova. Jedinstven po stranici. */
  description: string;
  /** Relativan path rute, npr. "/crkva/sv-marko-zagreb". */
  path: string;
  type?: "website" | "article";
  /** Apsolutni URL naslovne fotografije (og:image). */
  image?: string | undefined;
  /** Stranica koja ne smije u indeks (npr. filtrirani prikaz). */
  noindex?: boolean;
};

export function pageHead({ title, description, path, type = "website", image, noindex }: MetaArgs) {
  const url = abs(path);
  return {
    meta: [
      { title },
      { name: "description", content: description },
      ...(noindex ? [{ name: "robots", content: "noindex,follow" }] : []),
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: type },
      { property: "og:url", content: url },
      { property: "og:site_name", content: site.name },
      { property: "og:locale", content: "hr_HR" },
      { name: "twitter:card", content: image ? "summary_large_image" : "summary" },
      { name: "twitter:title", content: title },
      { name: "twitter:description", content: description },
      ...(image
        ? [
            { property: "og:image", content: abs(image) },
            { name: "twitter:image", content: abs(image) },
          ]
        : []),
    ],
    links: [{ rel: "canonical", href: url }],
  };
}

export function breadcrumbLd(items: { name: string; path: string }[]) {
  return {
    type: "application/ld+json",
    children: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: items.map((item, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: item.name,
        item: abs(item.path),
      })),
    }),
  };
}

/**
 * Dataset za cijeli katalog — ide u __root.tsx pa vrijedi svugdje.
 *
 * Namjerno Dataset, a ne LocalBusiness kako je bilo u templateu: ovo nije
 * poslovni subjekt nego skup otvorenih podataka. LocalBusiness bi Googleu
 * tvrdio da crkve.domovina.ai negdje ima adresu i radno vrijeme.
 */
export function datasetLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: site.fullName,
    alternateName: site.name,
    description: site.slogan,
    url: site.url,
    inLanguage: "hr",
    license: "https://opendatacommons.org/licenses/odbl/1-0/",
    isAccessibleForFree: true,
    creator: { "@type": "Organization", name: "DOMOVINA.ai", url: site.url },
    spatialCoverage: { "@type": "Place", name: "Hrvatska" },
    distribution: [
      {
        "@type": "DataDownload",
        encodingFormat: "application/geo+json",
        contentUrl: `${site.url}/data/crkve-index.json`,
      },
    ],
  };
}

/**
 * Jedna GRAĐEVINA. `PlaceOfWorship` je pravi schema.org tip i za džamiju i
 * za sinagogu; `CatholicChurch` bi lagao za 400-injak nekatoličkih objekata.
 */
export function placeOfWorshipLd(args: {
  name: string;
  path: string;
  lat: number;
  lng: number;
  address?: string | undefined;
  city?: string | undefined;
  image?: string | undefined;
  description?: string | undefined;
}) {
  return {
    type: "application/ld+json",
    children: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "PlaceOfWorship",
      name: args.name,
      url: abs(args.path),
      geo: { "@type": "GeoCoordinates", latitude: args.lat, longitude: args.lng },
      ...(args.description ? { description: args.description } : {}),
      ...(args.image ? { image: args.image } : {}),
      ...(args.address || args.city
        ? {
            address: {
              "@type": "PostalAddress",
              ...(args.address ? { streetAddress: args.address } : {}),
              ...(args.city ? { addressLocality: args.city } : {}),
              addressCountry: "HR",
            },
          }
        : {}),
    }),
  };
}

/** Jedna PRAVNA OSOBA (župa, samostan, crkvena općina). */
export function organizationLd(args: {
  name: string;
  path: string;
  oib?: string | undefined;
  address?: string | undefined;
  city?: string | undefined;
  phone?: string | undefined;
  email?: string | undefined;
  website?: string | undefined;
  parent?: string | undefined;
}) {
  return {
    type: "application/ld+json",
    children: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "Organization",
      name: args.name,
      url: abs(args.path),
      ...(args.oib ? { vatID: `HR${args.oib}`, taxID: args.oib } : {}),
      ...(args.phone ? { telephone: args.phone } : {}),
      ...(args.email ? { email: args.email } : {}),
      ...(args.website ? { sameAs: [args.website] } : {}),
      ...(args.parent
        ? { parentOrganization: { "@type": "Organization", name: args.parent } }
        : {}),
      ...(args.address || args.city
        ? {
            address: {
              "@type": "PostalAddress",
              ...(args.address ? { streetAddress: args.address } : {}),
              ...(args.city ? { addressLocality: args.city } : {}),
              addressCountry: "HR",
            },
          }
        : {}),
    }),
  };
}
