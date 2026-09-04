# Japan prefecture map asset

- Asset: `deformed-japan-prefecture-map.svg`
- Creator: lalamalink
- Upstream: <https://github.com/lalamalink/japan-map-svg>
- Upstream commit: `b6008cd22e6993a62860f5afafcc810ef4f9c69f`
- Upstream version: `2026.06.30`
- License: CC0 1.0 Universal (`LICENSE.cc0`)
- SHA-256: `c4817c97dedab08d20a2f4afccd4a780befc57040d48f7f0cded79d10e084fbc`

The original SVG is kept unchanged. Run `npm run generate:map` to verify the pinned
SHA-256 and extract its 47 prefecture paths and border overlay into the deterministic
TypeScript module used by the dashboard. Generation stops before writing when the
asset bytes do not match the checked-in digest. The asset is intentionally deformed
and must not be described as representing exact geography, area, distance, or
administrative-survey geometry.
