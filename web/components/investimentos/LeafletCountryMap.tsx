"use client";

import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Layer } from "leaflet";

import type { InvestmentMapCountry } from "@/lib/types";

type LeafletCountryMapProps = {
  countries: InvestmentMapCountry[];
  selectedCode: string | null;
  onSelectCountry: (code: string) => void;
};

type CountryProperties = {
  ISO_A2?: string;
  iso_a2?: string;
  ADM0_A3?: string;
  name?: string;
  NAME?: string;
};

const DEFAULT_STYLE = {
  color: "#0f172a",
  fillColor: "#3A3A3E",
  fillOpacity: 0.68,
  opacity: 0.8,
  weight: 0.7,
};

function featureCode(feature: Feature<Geometry, CountryProperties>) {
  return (feature.properties?.ISO_A2 ?? feature.properties?.iso_a2 ?? "").toUpperCase();
}

export function LeafletCountryMap({ countries, selectedCode, onSelectCountry }: LeafletCountryMapProps) {
  const [geoJson, setGeoJson] = useState<FeatureCollection<Geometry, CountryProperties> | null>(null);
  const countryByCode = useMemo(
    () => new Map(countries.map((country) => [country.code.toUpperCase(), country])),
    [countries],
  );

  useEffect(() => {
    let cancelled = false;
    fetch("/world.geo.json")
      .then((response) => (response.ok ? response.json() : null))
      .then((data: FeatureCollection<Geometry, CountryProperties> | null) => {
        if (!cancelled) {
          setGeoJson(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setGeoJson(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!geoJson) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-md border border-border bg-surface2 text-sm text-muted">
        Carregando mapa...
      </div>
    );
  }

  return (
    <MapContainer
      center={[18, 0]}
      zoom={2}
      minZoom={2}
      scrollWheelZoom={false}
      className="h-full min-h-[320px] overflow-hidden rounded-md"
      attributionControl={false}
    >
      <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
      <GeoJSON
        key={`${countries.length}-${selectedCode ?? "none"}`}
        data={geoJson}
        style={(feature) => {
          const code = feature ? featureCode(feature as Feature<Geometry, CountryProperties>) : "";
          const country = countryByCode.get(code);
          const active = selectedCode?.toUpperCase() === code;
          return {
            ...DEFAULT_STYLE,
            color: active ? "#bfdbfe" : DEFAULT_STYLE.color,
            fillColor: country?.color ?? DEFAULT_STYLE.fillColor,
            fillOpacity: country ? (active ? 0.92 : 0.72) : 0.32,
            weight: active ? 1.6 : DEFAULT_STYLE.weight,
          };
        }}
        onEachFeature={(feature, layer: Layer) => {
          const code = featureCode(feature as Feature<Geometry, CountryProperties>);
          const country = countryByCode.get(code);
          if (!country) {
            return;
          }
          layer.on({
            click: () => onSelectCountry(country.code),
          });
          layer.bindTooltip(country.name);
        }}
      />
    </MapContainer>
  );
}
