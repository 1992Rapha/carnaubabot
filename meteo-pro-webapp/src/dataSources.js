export const dataSources = [
  {
    name: 'INMET',
    country: 'Brazil',
    region: 'Brazil',
    category: 'observations',
    access: 'public API / station data',
    url: 'https://portal.inmet.gov.br/',
    features: ['surface observations', 'temperature', 'humidity', 'wind', 'rain', 'pressure']
  },
  {
    name: 'CPTEC/INPE',
    country: 'Brazil',
    region: 'Brazil / South America',
    category: 'forecast and satellite',
    access: 'public products',
    url: 'https://www.cptec.inpe.br/',
    features: ['forecast', 'satellite', 'rain', 'temperature', 'wind']
  },
  {
    name: 'CEMADEN',
    country: 'Brazil',
    region: 'Brazil',
    category: 'hydrology and risk',
    access: 'public monitoring products',
    url: 'https://www.gov.br/cemaden/',
    features: ['risk monitoring', 'rain gauges', 'flood risk', 'landslide risk']
  },
  {
    name: 'ANA HidroWeb / SNIRH',
    country: 'Brazil',
    region: 'Brazil',
    category: 'hydrology',
    access: 'public data portal',
    url: 'https://www.snirh.gov.br/hidroweb/',
    features: ['river levels', 'flow', 'rainfall stations', 'basin monitoring']
  },
  {
    name: 'REDEMET / DECEA',
    country: 'Brazil',
    region: 'Brazil',
    category: 'aviation',
    access: 'public aviation weather portal',
    url: 'https://redemet.decea.mil.br/',
    features: ['METAR', 'TAF', 'SIGMET', 'aviation weather']
  },
  {
    name: 'INPE Queimadas',
    country: 'Brazil',
    region: 'Brazil / South America',
    category: 'fire and smoke',
    access: 'public portal',
    url: 'https://terrabrasilis.dpi.inpe.br/queimadas/',
    features: ['fire hotspots', 'smoke context', 'burned area']
  },
  {
    name: 'Open-Meteo',
    country: 'Global',
    region: 'Global',
    category: 'forecast API',
    access: 'free API for many uses',
    url: 'https://open-meteo.com/',
    features: ['multi-model forecast', 'hourly forecast', 'daily forecast', 'air quality', 'marine']
  },
  {
    name: 'NOAA / NWS / NCEP',
    country: 'United States',
    region: 'United States / Global',
    category: 'forecast, warnings, radar, satellite',
    access: 'public datasets and APIs',
    url: 'https://www.weather.gov/',
    features: ['GFS', 'HRRR', 'warnings', 'radar', 'satellite', 'surface analysis']
  },
  {
    name: 'ECMWF Open Data',
    country: 'Europe',
    region: 'Global',
    category: 'forecast model',
    access: 'open selected model data',
    url: 'https://www.ecmwf.int/en/forecasts/datasets/open-data',
    features: ['global forecast model', 'ensemble products', 'pressure levels']
  },
  {
    name: 'DWD ICON Open Data',
    country: 'Germany',
    region: 'Global / Europe',
    category: 'forecast model',
    access: 'open data',
    url: 'https://www.dwd.de/EN/ourservices/opendata/opendata.html',
    features: ['ICON', 'ICON-EU', 'forecast fields']
  },
  {
    name: 'MeteoFrance',
    country: 'France',
    region: 'France / Europe / selected territories',
    category: 'forecast model',
    access: 'open data and APIs depending on product',
    url: 'https://meteofrance.com/',
    features: ['AROME', 'ARPEGE', 'warnings', 'forecast products']
  },
  {
    name: 'NASA FIRMS',
    country: 'United States',
    region: 'Global',
    category: 'fire',
    access: 'public API / maps',
    url: 'https://firms.modaps.eosdis.nasa.gov/',
    features: ['active fires', 'thermal anomalies', 'satellite fire detection']
  },
  {
    name: 'OpenAQ',
    country: 'Global',
    region: 'Global',
    category: 'air quality',
    access: 'public API',
    url: 'https://openaq.org/',
    features: ['PM2.5', 'PM10', 'ozone', 'NO2', 'air quality stations']
  },
  {
    name: 'Copernicus Atmosphere Monitoring Service',
    country: 'European Union',
    region: 'Global / Europe',
    category: 'atmosphere and air quality',
    access: 'public products / API registration may be required',
    url: 'https://atmosphere.copernicus.eu/',
    features: ['aerosols', 'dust', 'smoke', 'ozone', 'air quality forecast']
  }
];

export const featureGroups = [
  {
    title: 'Forecast Engine',
    items: ['multi-model forecast', 'model comparison', 'forecast confidence', 'hyperlocal forecast', 'hourly and daily forecast', 'minute-by-minute precipitation']
  },
  {
    title: 'Radar System',
    items: ['live radar', 'rain intensity', 'radar animation', 'storm tracking', 'hail risk', 'velocity radar placeholder', 'echo tops placeholder', 'nowcasting']
  },
  {
    title: 'Satellite System',
    items: ['visible satellite', 'infrared satellite', 'water vapor imagery', 'air mass RGB', 'dust and smoke visualization', 'cloud-top temperature']
  },
  {
    title: 'Severe Weather',
    items: ['thunderstorm alerts', 'lightning alerts', 'hail risk', 'wind gust warnings', 'flood warnings', 'convective parameters']
  },
  {
    title: 'Atmospheric Analysis',
    items: ['surface wind', 'gusts', 'streamlines', 'jet stream', 'pressure maps', 'isobars', 'humidity', 'dew point', 'freezing level']
  },
  {
    title: 'Air Quality',
    items: ['AQI', 'PM2.5', 'PM10', 'ozone', 'smoke transport', 'dust concentration', 'pollen placeholder']
  },
  {
    title: 'Marine and Outdoor',
    items: ['wave height', 'swell direction', 'swell period', 'tides', 'sea temperature', 'visibility', 'fog']
  },
  {
    title: 'Aviation',
    items: ['METAR', 'TAF', 'ceiling', 'visibility', 'turbulence', 'icing', 'winds aloft']
  },
  {
    title: 'Hydrology',
    items: ['river levels', 'flood prediction', 'rain accumulation', 'watershed runoff', 'soil saturation']
  },
  {
    title: 'Historical and Climate',
    items: ['historical radar playback', 'historical temperature', 'historical rainfall', 'climate anomalies', 'seasonal outlooks', 'ENSO status']
  }
];

export const mapLayers = [
  'Radar', 'Satellite', 'Lightning', 'Rain accumulation', 'Wind', 'Gusts', 'Temperature',
  'Dew point', 'Pressure', 'Isobars', 'Clouds', 'Air quality', 'Smoke', 'Dust',
  'Waves', 'Tides', 'River levels', 'Severe alerts', 'Aviation weather'
];
