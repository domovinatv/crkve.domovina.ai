import { createFileRoute, Link } from "@tanstack/react-router";

import { izvori, site } from "@/data/site";
import { breadcrumbLd, pageHead } from "@/lib/seo";
import { PageHeading, Section } from "@/components/catalog/Bits";

export const Route = createFileRoute("/o-projektu")({
  head: () => ({
    ...pageHead({
      title: "O projektu — kako nastaje katalog crkava u Hrvatskoj",
      description:
        "Izvori, postupak i licenca kataloga sakralnih objekata. Sve se gradi reproducibilno iz javnih izvora, bez ijednog API ključa, a rupe u podacima se ispisuju.",
      path: "/o-projektu",
    }),
    scripts: [
      breadcrumbLd([
        { name: "Naslovnica", path: "/" },
        { name: "O projektu", path: "/o-projektu" },
      ]),
    ],
  }),
  component: OProjektu,
});

function OProjektu() {
  return (
    <Section>
      <PageHeading
        eyebrow="O projektu"
        title="Katalog sakralnih objekata u Hrvatskoj"
        lead="Jedno mjesto na kojem stoje i građevine i pravne osobe, spojene koliko se pošteno dalo spojiti — i na kojem se vidi gdje spoja nema."
      />

      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="max-w-3xl space-y-8">
          <div>
            <h2 className="text-lg">Zašto dvije vrste stranica</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/85">
              Građevina i pravna osoba nisu isti skup. Jedna župa ima župnu crkvu, filijalne crkve i
              kapele; mnoga crkva — samostanska, grobljanska, poklonac uz cestu — nema župu. Model
              zato ima dvije tablice, a katalog dvije vrste stranica koje se međusobno linkaju.
              Spajanje tih dvaju skupova je heuristika, ne činjenica, pa se svaka nespojena stavka
              ispisuje kao takva.
            </p>
          </div>

          <div>
            <h2 className="text-lg">Kako se objekti spajaju</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/85">
              Titular se uspoređuje po glavi, ne po punom nazivu: isti je objekt „sv. Ante" u
              OpenStreetMapu, „sv. Ante Padovanskog" u Registru kulturnih dobara i „SV. ANTUNA
              PADOVANSKOG" u državnoj evidenciji. Kandidati se blokiraju po naselju, pa po općini.
              Uz to vrijedi pravilo jedinstvenosti: ako u nekom mjestu postoji točno jedna katedrala
              tog titulara, spoj se prihvaća i kad se nazivi razilaze.
            </p>
          </div>

          <div>
            <h2 className="text-lg">Zašto su granice biskupija izračunate</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/85">
              Ne postoje kao javan podatak: OpenStreetMap ima tri od petnaest, Wikidata nijednu.
              Katalog ih zato derivira iz sjedišta župa preko granica naselja — a te tri OSM
              relacije služe kao neovisna mjera. Svaka derivirana granica nosi svoj postotak
              slaganja, jer izračunato nije isto što i preslikano.{" "}
              <Link to="/biskupije" className="underline">
                Pogledaj biskupije
              </Link>
              .
            </p>
          </div>

          <div>
            <h2 className="text-lg">Što nedostaje</h2>
            <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-foreground/85">
              <li>
                Kontakti župa — telefon i e-mail nisu u državnoj evidenciji, pa ih većina zapisa
                nema.
              </li>
              <li>
                Dio zaštićene baštine bez para u OpenStreetMapu. Izmjereno je da za gotovo sve takve
                zapise kandidat postoji — matcher ih je pogledao pa odbio, što znači da je posao
                dijagnoza praga, a ne ručno mapiranje.
              </li>
              <li>
                Konflikti lokacije čekaju ručni pregled. Većina ih je druga zgrada iste župe (župni
                ured, pastoralni centar), pa se ništa ne mijenja automatski.
              </li>
            </ul>
            <p className="mt-3 text-sm">
              <Link to="/brojke" className="underline">
                Sve brojke i pokrivenost →
              </Link>
            </p>
          </div>

          <div>
            <h2 className="text-lg">Licenca</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/85">
              Podaci nisu čisti CC-BY. OpenStreetMap je ODbL i nameće share-alike na izvedenu bazu,
              pa isto vrijedi i za ovaj katalog. Državne evidencije su pod otvorenom dozvolom,
              Wikidata je CC0. Ako preuzimate podatke, zadržite atribuciju svih izvora.
            </p>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="surface-card p-5">
            <p className="eyebrow">Izvori</p>
            <ul className="mt-3 space-y-4">
              {izvori.map((i) => (
                <li key={i.naziv}>
                  <a
                    href={i.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-sm font-semibold underline"
                  >
                    {i.naziv}
                  </a>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{i.sto}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Licenca: {i.licenca}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="surface-card p-5">
            <p className="eyebrow">Preuzimanje</p>
            <ul className="mt-2 space-y-1.5 text-sm">
              <li>
                <a href="/data/crkve-index.json" className="underline">
                  crkve-index.json
                </a>
              </li>
              <li>
                <a href="/data/zupe-index.json" className="underline">
                  zupe-index.json
                </a>
              </li>
              <li>
                <a href="/data/biskupije.geojson" className="underline">
                  biskupije.geojson
                </a>
              </li>
              <li>
                <a href="/data/stats.json" className="underline">
                  stats.json
                </a>
              </li>
            </ul>
          </div>

          <div className="surface-card p-5">
            <p className="eyebrow">Kod</p>
            <a
              href={site.repo}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-2 block text-sm underline"
            >
              Pipeline i izvorni kod
            </a>
            <a
              href={site.karta}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-1.5 block text-sm underline"
            >
              Isti podaci kao sloj na gis.domovina.ai
            </a>
          </div>
        </aside>
      </div>
    </Section>
  );
}
