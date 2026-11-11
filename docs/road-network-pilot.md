# Road-network pilot (OSRM drive times)

Question: do drive times between hromada centres explain real domestic ММС ties better than straight-line distance?

## Method
- OSM Ukraine extract (Geofabrik, 2026-11-11), OSRM car profile, MLD, run locally (`brew install osrm-backend`; Docker VM ran out of memory on extract).
- Nodes: 1469 hromada centres (`lat_center`/`lon_center` from KSE `geography.csv`, admin-centre settlements).
- Known ties: KSE partnerships network + bilateral-confirmed Пліч-о-пліч pairs (995 pairs; 900 within 150 km).
- Script: `scripts/analysis/road_network_pilot.py`; output `data/research-log/road-network-pilot.json`.

## Findings
1. **Drive time adds no predictive power over straight-line distance for existing ties.** AUC (pairs ≤150 km): km 0.877, drive time 0.843; logistic CV: km 0.863, km+drive 0.865, with oblast/raion 0.862 → 0.864. Per-pair test against same-distance decoys: 388 wins / 391 losses.
2. Known ties are mostly near: median 31 km / 56 min; 79% same oblast, 56% same raion. Existing ties already reflect administrative geography, which straight-line distance and `geo_score` capture.
3. Where roads matter is the barrier cases: coastal estuaries (Одещина), Dnipro/Kakhovka (Херсонщина, Нікополь), frontline. Bucha–Hostomel: 5.4 km / 12 min (consistent with the cluster Suprun mentioned).
4. Clusters at ≤30 min drive: 329 groups, largest 234 hromadas, 192 isolated.

## Caveats
- OSM reflects the post-war network: Kherson left/right bank pairs show 15+ hours (destroyed crossings). Cap or exclude these.
- Occupied/frontline hromadas have unreliable roads.
- A null result for *predicting past ties* does not rule out value for *feasibility* (joint services, catchments).

## Suggested use
Do not swap `geo_score` for drive time. Use drive time as a feasibility filter/feature for service-sharing (waste, ЦНАП, ambulance), for agglomeration clusters, and to flag pairs close by km but separated by barriers.
