# Meteo Pro Webapp

A frontend-only starter for a professional meteorological dashboard focused on Brazil and global data sources.

## Included feature groups

- Multi-source forecast model catalog
- Brazil and international weather data source registry
- Radar, satellite, lightning, wind, hydrology, marine, aviation and air quality panels
- Severe-weather alert architecture
- Map layer registry
- Source transparency: provider, country/region, data type, access mode and URL
- No external sensors/devices and no expert/raw-GRIB mode

## Important implementation note

This is a browser-first prototype. Many professional weather sources require API keys, CORS proxies, backend caching, paid licenses, or institutional agreements. The app therefore separates:

1. **UI feature model** — already implemented in `src/main.js`.
2. **Data source registry** — implemented in `src/dataSources.js`.
3. **Live integrations** — placeholders for future backend/API adapters.

## Run locally

```bash
cd meteo-pro-webapp
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Suggested live data integrations

Brazil:

- INMET — observations, forecasts, station data
- CPTEC/INPE — Brazilian weather forecasts and satellite products
- CEMADEN — hydrological/risk monitoring
- ANA HidroWeb/SNIRH — river and hydrology data
- REDEMET/DECEA — aviation weather, METAR/TAF where available
- INPE/Queimadas — fire/smoke monitoring

International/global:

- Open-Meteo — forecast API with multiple models
- NOAA/NWS/NCEP — GFS, HRRR, warnings, radar/satellite products
- ECMWF Open Data — selected model fields
- DWD ICON Open Data — ICON global/regional products
- MeteoFrance AROME/ARPEGE open data where available
- EUMETSAT / NOAA satellites
- NASA FIRMS — fire hot spots
- OpenAQ — air quality aggregation
- Copernicus Atmosphere Monitoring Service — aerosols/smoke/dust/air quality

## Limitations

- Radar mosaics and lightning data are highly country-dependent.
- Some Brazilian datasets have unstable endpoints or require backend normalization.
- Official warning integration should prefer governmental sources when available.
- Satellite/radar tiles usually need a tile server or map proxy for production use.
