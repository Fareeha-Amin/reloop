import L from 'leaflet';
import { useEffect, useState } from 'react';
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';

import { MAP } from '../config';
import { t } from '../i18n';
import { Button } from '../ui/Button';

export interface Point {
  lat: number;
  lng: number;
}

/** A pin drawn with the theme's tokens, so no marker images need bundling. */
export function pinIcon(variant: 'brand' | 'clay' | 'ochre' = 'brand'): L.DivIcon {
  const fill = { brand: 'fill-brand-700', clay: 'fill-clay-500', ochre: 'fill-ochre-500' }[variant];
  return L.divIcon({
    className: '',
    iconSize: [34, 44],
    iconAnchor: [17, 42],
    html: `<svg viewBox="0 0 34 44" width="34" height="44" class="drop-shadow-md"><path class="${fill}" d="M17 43s15-14.4 15-26A15 15 0 0 0 2 17c0 11.6 15 26 15 26Z"/><circle cx="17" cy="17" r="6" class="fill-leaf"/></svg>`,
  });
}

/** Attribution required by OpenStreetMap's tile policy. */
export function Tiles() {
  return <TileLayer url={MAP.tileUrl} maxZoom={MAP.maxZoom} attribution={t('map.attribution')} />;
}

function ClickToPlace({ onPick }: { onPick: (p: Point) => void }) {
  useMapEvents({ click: (e) => onPick({ lat: e.latlng.lat, lng: e.latlng.lng }) });
  return null;
}

function FlyTo({ point }: { point: Point | null }) {
  const map = useMap();
  useEffect(() => {
    if (point) map.flyTo([point.lat, point.lng], Math.max(map.getZoom(), MAP.pinnedZoom), { duration: 0.6 });
    // Only when the point is set from outside the map (e.g. "use my location").
  }, [point?.lat, point?.lng]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

/**
 * The user drops (or drags) a pin; the pin's coordinates are what the API stores. The
 * address is typed separately: there is no geocoder (the backend's is a labelled stub).
 */
export function LocationPicker({
  value,
  onChange,
  error,
}: {
  value: Point | null;
  onChange: (p: Point) => void;
  error?: string;
}) {
  const [flyTarget, setFlyTarget] = useState<Point | null>(null);
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState(false);
  const canLocate = typeof navigator !== 'undefined' && 'geolocation' in navigator;

  function useMyLocation() {
    setLocating(true);
    setGeoError(false);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const p = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        onChange(p);
        setFlyTarget(p);
        setLocating(false);
      },
      () => {
        setGeoError(true);
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  return (
    <div>
      <div
        className={`relative overflow-hidden rounded-card border ${error ? 'border-danger-500' : 'border-line'} shadow-card`}
      >
        <MapContainer
          center={value ? [value.lat, value.lng] : MAP.center}
          zoom={value ? MAP.pinnedZoom : MAP.zoom}
          className="h-80 w-full sm:h-96"
          scrollWheelZoom
        >
          <Tiles />
          <ClickToPlace onPick={onChange} />
          <FlyTo point={flyTarget} />
          {value && (
            <Marker
              position={[value.lat, value.lng]}
              icon={pinIcon()}
              draggable
              eventHandlers={{
                dragend: (e) => {
                  const ll = (e.target as L.Marker).getLatLng();
                  onChange({ lat: ll.lat, lng: ll.lng });
                },
              }}
            />
          )}
        </MapContainer>
        {!value && (
          <div className="pointer-events-none absolute inset-x-0 top-3 z-[500] flex justify-center">
            <span className="rounded-pill bg-brand-900/90 px-4 py-1.5 text-sm font-semibold text-leaf shadow-card">
              {t('location.tapToPlace')}
            </span>
          </div>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className={error ? 'text-danger-700' : 'text-ink-muted'}>
          {error ??
            (value
              ? t('location.pinned', { lat: value.lat.toFixed(5), lng: value.lng.toFixed(5) })
              : t('location.noPin'))}
        </span>
        {canLocate && (
          <Button variant="ghost" size="sm" icon="locate" busy={locating} onClick={useMyLocation}>
            {t('location.useMine')}
          </Button>
        )}
      </div>
      {geoError && <p className="mt-1 text-sm text-danger-700">{t('location.geoFailed')}</p>}
    </div>
  );
}

/** A small read-only map with one pin. */
export function PointMap({ point, className = 'h-56' }: { point: Point; className?: string }) {
  return (
    <div className="overflow-hidden rounded-card border border-line">
      <MapContainer center={[point.lat, point.lng]} zoom={MAP.pinnedZoom} className={`${className} w-full`} scrollWheelZoom={false}>
        <Tiles />
        <Marker position={[point.lat, point.lng]} icon={pinIcon()} />
      </MapContainer>
    </div>
  );
}
