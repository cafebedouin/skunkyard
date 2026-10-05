# C1 first cut: external replication at height 1,886,343 (odiseus, GitHub: odiseusme)

Four aggregate tables from an independent run of `q1/run.sh` at skunkyard 28331fe on a synced mainnet node
(ergo-6.0.6.jar matching the pin; state copied from a stopped node, scanned on a separate machine), received
2026-10-05 in the developer chat. Same run as the Q1 census re-run (tip 1,886,343, header c331d6a6…cbba; traversed root
= stored root 870e5a8d…b419; 0 label mismatches; box sum = genesis sum). Credit: "odiseus (GitHub: odiseusme)", as the
contributor asked.

Files as written by the run: `p2s_with_key_indicators.csv`, `p2s_with_key_top_templates.csv`,
`p2s_no_key_top_templates.csv`, `by_category_age.csv`. `top_boxes.csv` was deliberately not shared.

Checks done here (2026-10-05): the indicator rows sum to the published p2s_with_key line (37,027 boxes,
2,907,737.890 ERG); age buckets sum per category (printed by the check above; see commit message).

Reporting rule (SK-036): template level only. Some templates have very few boxes (e.g. a no-key template with 2 boxes);
quote classes and totals, not single low-count templates.
