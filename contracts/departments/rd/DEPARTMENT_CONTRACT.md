# RD department contract

Owner: RD / Reduciendo Dano.
Consumer: the MAK Hub on port 8900 and the RD offline tools.

Allowed read roots are `src/flujo/rd`, `src/flujo/plano`, `projects/plano`,
`data/productoras`, `knowledge/venues`, `knowledge/logos` and the RD database
projection. Keep `data/rd_datos.db` classified as an empty runtime shell until
an explicit data authority exists.

Use Spanish or English ASCII keywords when searching. Code and machine-facing
metadata stay English ASCII. Human-facing RD output may use Spanish accents.

Validation must begin with static/import checks and GET-only database reads.
Mutators, provider calls and uploads require a separate explicit gate.

Rollback: restore the source JSON/YAML and regenerate `data/rd.db`; never edit
the SQLite projection by hand and never delete historical evidence.
