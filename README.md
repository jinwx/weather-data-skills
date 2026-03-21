# weather-data-skills

A plugin with skills for downloading and processing weather and climate data. Works with Claude Code, Cursor, Codex, VS Code, and other AI coding assistants that support skills/plugins.

> This project is in its early stages. Only the `cds-download` skill is available so far. More skills are planned.

Downloading weather data sounds simple — until it isn't. Data archives have undocumented API quirks, format traps, versioning nightmares, and efficiency strategies that only domain experts know. These skills encode that hard-won knowledge so your AI assistant gets it right the first time.

## Vision

1. **Find the right dataset** — Recommend the most suitable dataset and provider for your use case.
2. **Download the data correctly** — Handle archive-specific constraints like system versioning, product type availability, request splitting, and API authentication — so you get the data you actually need.
3. **Parse and process the data** — Some datasets are notoriously painful to work with. For example, GHCN station data requires non-trivial parsing and QC flag handling — a planned skill for this project.

## Skills

### `cds-download`

Downloads climate data from the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu) (CDS) — the world's largest open climate data archive, hosting ERA5, seasonal forecasts, satellite observations, and more.

**Example: downloading seasonal forecasts from 1993 to present.** This is a task where the skill really shines, because getting it right requires knowledge that is critical but surprisingly hard to piece together:

- ECMWF's current system is System 51 (SEAS5.1), not System 5 which was discontinued in 2022.
- The `ensemble_mean` product type only covers real-time years (~2017 onward) — to get 1993-present, you must use `monthly_mean` and compute the ensemble mean yourself.
- UKMO has gone through 10+ system versions, each covering only 1-2 years of real-time data — the skill knows how to chain them for maximum temporal coverage.
- The CDS constraints API can dynamically verify which system versions and year-month combinations are actually available, avoiding hardcoded values that go stale.

The skill encodes all of this and guides your AI assistant to produce correct, efficient downloads.

## Installation

### Claude Code

```
/plugin marketplace add jinwx/weather-data-skills
/plugin install weather-data-skills@weather-skills
```

Or via npx:

```
npx skills add git@github.com:jinwx/weather-data-skills.git
```

### Codex

Type the following in the Codex chat:

```
$skill-installer https://github.com/jinwx/weather-data-skills/tree/main/skills/cds-download
```

### Other AI assistants

Ask your AI assistant:

> Install the cds-download skill from `https://github.com/jinwx/weather-data-skills`

You can also manually copy the `skills/` directory to the dedicated skills directory required by your agent.

## Contributing

Contributions are welcome! Whether it's a bug report, a new skill idea, or a pull request — all are appreciated.

- **Found incorrect or outdated information?** Open an issue. Weather data APIs change frequently, and keeping up is a community effort.
- **Have domain knowledge about a dataset?** Consider contributing a new skill. If you've spent hours figuring out the quirks of a data source, that knowledge is exactly what this project is for.
- **Want to improve an existing skill?** PRs are welcome. Please include a brief description of what the change fixes or improves.

If you're unsure whether something is worth raising, open an issue anyway — it probably is.

## License

MIT
