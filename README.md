# sitegen

A command line tool that turns a short YAML description of a local business
into a complete, deployable [Astro](https://astro.build) website styled with
Tailwind CSS.

```bash
sitegen serve                  # fill in a form in the browser, download the site
sitegen init business.yaml     # write a starter file to fill in
sitegen validate business.yaml # check it without generating anything
sitegen build business.yaml    # generate the site into ./site
```

## The builder

`sitegen serve` opens a local page at <http://127.0.0.1:8765> with a form
covering every field below. It validates as you go using the same code the CLI
uses, previews the colour ramp your brand colour produces, and hands back
either the finished website as a ZIP or a `business.yaml` for the CLI. Nothing
leaves the machine — the server binds to the loopback interface only.

It is the route to hand a non-technical owner: they fill in the form, download
the ZIP, and the only remaining step is `npm install && npm run dev`.

## Installing

```bash
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The `sitegen` command is then available at `.venv\Scripts\sitegen.exe`, or on
your PATH whenever the virtual environment is active.

## The input file

Only `business.name` is required. Leave a section out and the matching part of
the website disappears with it — a business with no `services` list simply has
no services section.

| Section | Purpose |
| --- | --- |
| `business` | Name, tagline, description, phone, email, address, schema.org type |
| `brand` | `primary` and `accent` hex colors, and a Google Font family |
| `hours` | Per weekday opening times, or `closed` |
| `services` | List of `name` / `description` / `price` |
| `reviews` | Aggregate `rating` / `count` plus quoted `items` |
| `about` | A heading and a body; blank lines become paragraphs |
| `cta` | The main call to action; defaults to calling the phone number |
| `social` | Platform name to profile URL |
| `seo` | Page title and meta description; derived from the business if omitted |
| `site_url`, `lang` | Canonical URL and the page language, default `en` |

Add `lat` and `lon` under `business.address` and the contact section gains an
embedded OpenStreetMap map, which needs no API key. Without them it falls back
to a directions link.

See [`examples/bike-shop.yaml`](examples/bike-shop.yaml) for a full file and
[`examples/minimal.yaml`](examples/minimal.yaml) for the smallest valid one.

## What gets generated

A standalone Astro project — `npm install && npm run dev` and it runs. All
content lands in `src/data/business.json`, which the components read, so the
text can be edited afterwards without touching any markup.

The brand color is expanded into a full `50`–`950` Tailwind scale in
`src/styles/global.css`, along with a matching near-grey neutral ramp that
carries a trace of the brand hue, so the greys sit with the brand rather than
against it. Those feed semantic roles — `background`, `foreground`, `card`,
`muted`, `border`, `ring` — and the components only ever reference those, never
a raw palette step. A foreground color is chosen automatically by relative
luminance so text stays legible on any brand color.

Business details are emitted as schema.org `LocalBusiness` JSON-LD, including
opening hours, geo coordinates and `aggregateRating`, which is what search
engines read for local results.

Page structure follows a trust-first order — credibility, then offer, then the
details needed to act: hero with rating, reviews, services, about, hours,
contact. Accessibility is built in: a skip link, visible focus rings, 44px
minimum touch targets, `scroll-padding` so the sticky header never hides
focused elements, and full `prefers-reduced-motion` support. The mobile menu is
a `<details>` disclosure, so the whole page ships zero JavaScript.

## Development

```bash
.venv\Scripts\python.exe -m pytest
```

The Astro project templates live in `src/sitegen/templates/project/`. Files
ending in `.j2` are rendered with Jinja; everything else is copied verbatim, so
the `.astro` components can be edited as ordinary Astro files. A `dot-` prefix
in a template filename becomes a leading dot in the output.
