from __future__ import annotations

import os
from threading import Lock
import time

import httpx

from app.domain.models import LocationSearchResult


NER_STATES = {
    "assam",
    "arunachal pradesh",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "sikkim",
    "tripura",
}


class NominatimGeocodingService:
    provider = "Nominatim / OpenStreetMap"
    attribution = "© OpenStreetMap contributors"

    def __init__(self) -> None:
        self.base_url = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
        self.user_agent = os.getenv("NER_GEOCODER_USER_AGENT", "NER-Logistics-Control-Tower-PS26002/0.3")
        self._cache: dict[str, list[LocationSearchResult]] = {}
        self._request_lock = Lock()
        self._last_request_at = 0.0

    @staticmethod
    def _is_ner_state(state: str) -> bool:
        normalized = state.strip().lower()
        return normalized in NER_STATES or any(name in normalized for name in NER_STATES)

    def search(self, query: str) -> list[LocationSearchResult]:
        normalized_query = " ".join(query.strip().split())
        if len(normalized_query) < 2:
            return []
        cache_key = normalized_query.casefold()
        if cache_key in self._cache:
            return self._cache[cache_key]

        with self._request_lock:
            wait_seconds = 1.05 - (time.monotonic() - self._last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            with httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": self.user_agent}) as client:
                response = client.get(f"{self.base_url}/search", params={
                    "q": normalized_query,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "countrycodes": "in",
                    "viewbox": "87.5,30.5,98.5,21",
                    "bounded": 1,
                    "limit": 10,
                    "accept-language": "en",
                })
                self._last_request_at = time.monotonic()
                response.raise_for_status()
                payload = response.json()

        results: list[LocationSearchResult] = []
        for item in payload:
            address = item.get("address") or {}
            state = str(address.get("state") or "")
            if not self._is_ner_state(state):
                continue
            latitude = float(item["lat"])
            longitude = float(item["lon"])
            if not (21 <= latitude <= 30.5 and 87.5 <= longitude <= 98.5):
                continue
            results.append(LocationSearchResult(
                id=f"{item.get('osm_type', 'place')}-{item.get('osm_id', item.get('place_id'))}",
                label=str(item["display_name"]),
                latitude=latitude,
                longitude=longitude,
                state=state,
                district=address.get("state_district") or address.get("county") or address.get("district"),
                category=item.get("type") or item.get("category"),
                attribution=self.attribution,
            ))
        self._cache[cache_key] = results[:6]
        return self._cache[cache_key]

    def reverse(self, latitude: float, longitude: float) -> dict[str, str | None]:
        cache_key = f"reverse:{latitude:.4f}:{longitude:.4f}"
        cached = self._cache.get(cache_key)
        if cached:
            item = cached[0]
            return {"label": item.label, "state": item.state, "district": item.district}
        with self._request_lock:
            wait_seconds = 1.05 - (time.monotonic() - self._last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            with httpx.Client(timeout=8.0, follow_redirects=True, headers={"User-Agent": self.user_agent}) as client:
                response = client.get(f"{self.base_url}/reverse", params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "zoom": 14,
                    "accept-language": "en",
                })
                self._last_request_at = time.monotonic()
                response.raise_for_status()
                payload = response.json()
        address = payload.get("address") or {}
        state = str(address.get("state") or "")
        if not self._is_ner_state(state):
            raise ValueError("Selected point is not inside one of the eight NER states")
        district = address.get("state_district") or address.get("county") or address.get("district")
        label = str(payload.get("display_name") or f"{latitude:.5f}, {longitude:.5f}")
        cached_result = LocationSearchResult(
            id=cache_key, label=label, latitude=latitude, longitude=longitude,
            state=state, district=district, category="reverse_geocoded",
            attribution=self.attribution,
        )
        self._cache[cache_key] = [cached_result]
        return {"label": label, "state": state, "district": district}


geocoding_service = NominatimGeocodingService()
