# sitegen

A command line tool that turns a short YAML description of a local business
into a complete, deployable [Astro](https://astro.build) website styled with
Tailwind CSS.

```bash
sitegen init business.yaml     # write a starter file to fill in
sitegen validate business.yaml # check it without generating anything
sitegen build business.yaml    # generate the site into ./site
```

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
| `about` | A heading and a body; blank lines become paragraphs |
| `cta` | The main call to action; defaults to calling the phone number |
| `social` | Platform name to profile URL |
| `seo` | Page title and meta description; derived from the business if omitted |
| `site_url`, `lang` | Canonical URL and the page language, default `en` |

See [`examples/bike-shop.yaml`](examples/bike-shop.yaml) for a full file and
[`examples/minimal.yaml`](examples/minimal.yaml) for the smallest valid one.

## What gets generated

A standalone Astro project — `npm install && npm run dev` and it runs. All
content lands in `src/data/business.json`, which the components read, so the
text can be edited afterwards without touching any markup.

The brand color is expanded into a full `50`–`950` Tailwind scale in
`src/styles/global.css`, and a foreground color is chosen automatically for
legibility against it. The business details are also emitted as schema.org
`LocalBusiness` JSON-LD, including opening hours, which is what search engines
read for local results.

## Development

```bash
.venv\Scripts\python.exe -m pytest
```

The Astro project templates live in `src/sitegen/templates/project/`. Files
ending in `.j2` are rendered with Jinja; everything else is copied verbatim, so
the `.astro` components can be edited as ordinary Astro files. A `dot-` prefix
in a template filename becomes a leading dot in the output.
