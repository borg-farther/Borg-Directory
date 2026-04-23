# external channel uat closure

## target channels
- telegram
- discord
- public web artifacts
- github/repo first-user surface

## uat rule
each channel must have:
1. explicit contract/standard artifact
2. independent proof artifacts
3. passing automated tests tied to canonical gate truth

## canonical machine matrix
- `eval/external_channel_uat_matrix.json`

## pass criteria
- `overall_status` is `pass`
- every channel has `enabled=true`, `independent=true`, `uat_status=pass`
- all declared proof artifacts exist

## channel notes
- telegram: uses checkpoint contract + linter and pytest contract
- discord: uses dedicated discord checkpoint contract + standard
- public web: readiness/value/proof/impact pages must align to gate snapshot
- github: install and metadata docs must align to new canonical home
