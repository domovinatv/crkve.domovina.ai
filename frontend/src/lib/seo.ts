import { site, openingHours } from "@/data/site";

/** Pretvara relativni path u apsolutni URL (canonical i og:url traže apsolutni). */
function abs(path: string) {
  return path.startsWith("http") ? path : `${site.url.replace(/\/$/, "")}${path}`;
}

type MetaArgs = {
  /** Puni <title>. Uključi lokaciju gdje je prirodno, bez keyword stuffinga. */
  title: string;
  /** 140–160 znakova. Jedinstven po stranici. */
  description: string;
  /** Relativan path rute, npr. "/kontakt". */
  path: string;
  type?: "website" | "article";
  /** Apsolutni URL naslovne fotografije za dijeljenje (og:image). */
  image?: string | undefined;
};

export function pageHead({ title, description, path, type = "website", image }: MetaArgs) {
  const url = abs(path);
  return {
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: type },
      { property: "og:url", content: url },
      { property: "og:site_name", content: site.name },
      { property: "og:locale", content: "hr_HR" },
      { name: "twitter:card", content: "summary_large_image" },
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
 * LocalBusiness za hrvatski lokalni biznis. Ide u __root.tsx pa vrijedi
 * za cijeli site. Prazna polja iz site.ts se izostavljaju — Google radije
 * nema polje nego prazno polje.
 */
export function localBusinessLd() {
  return {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: site.fullName,
    alternateName: site.name,
    url: site.url,
    ...(site.slogan ? { slogan: site.slogan } : {}),
    telephone: site.phone,
    email: site.email,
    address: {
      "@type": "PostalAddress",
      streetAddress: site.street,
      addressLocality: site.city,
      postalCode: site.postalCode,
      addressCountry: "HR",
    },
    areaServed: site.city,
    ...(openingHours.length
      ? {
          openingHoursSpecification: openingHours.map((slot) => ({
            "@type": "OpeningHoursSpecification",
            dayOfWeek: slot.days,
            description: slot.hours,
          })),
        }
      : {}),
    ...(site.instagram || site.facebook
      ? { sameAs: [site.instagram, site.facebook].filter(Boolean) }
      : {}),
  };
}

/**
 * Za pojedinu uslugu/program koji ima svoju stranicu.
 * Ako klijent prodaje tečajeve, zamijeni "@type" u "Course".
 */
export function serviceLd(args: {
  name: string;
  description: string;
  audience?: string;
  price?: string;
  currency?: string;
}) {
  return {
    type: "application/ld+json",
    children: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "Service",
      name: args.name,
      description: args.description,
      provider: localBusinessLd(),
      areaServed: site.city,
      ...(args.audience ? { audience: { "@type": "Audience", audienceType: args.audience } } : {}),
      ...(args.price
        ? {
            offers: {
              "@type": "Offer",
              price: args.price,
              priceCurrency: args.currency ?? "EUR",
            },
          }
        : {}),
    }),
  };
}
