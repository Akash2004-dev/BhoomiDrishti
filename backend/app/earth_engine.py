import os
from datetime import datetime, timedelta

from app.schemas import SatelliteSpectralSummary


def _unavailable(message: str, cloud_obscured: bool = False) -> SatelliteSpectralSummary:
    return SatelliteSpectralSummary(
        source="unavailable", cloud_obscured=cloud_obscured, message=message
    )


def get_satellite_spectral_data(lat: float, lon: float, event_date_str: str) -> SatelliteSpectralSummary:
# Query Sentinel-2 SR data. Missing access/data is reported, never replaced with made-up values.
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT", "")
    project = os.getenv("GEE_PROJECT_ID", "")
    if not (credentials_path and os.path.isfile(credentials_path) and service_account and project):
        return _unavailable("Earth Engine credentials/project are not configured; no satellite value was used.")

    try:
        # Earth Engine is optional; avoid loading its crypto stack when it is not configured.
        import ee

        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
        credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
        ee.Initialize(credentials, project=project)

        pre_start = (event_date - timedelta(days=30)).strftime("%Y-%m-%d")
        pre_end = (event_date - timedelta(days=1)).strftime("%Y-%m-%d")
        post_start = event_date.strftime("%Y-%m-%d")
        post_end = (event_date + timedelta(days=15)).strftime("%Y-%m-%d")
        roi = ee.Geometry.Point([lon, lat]).buffer(200).bounds()

        def add_clear_ndvi(image):
            scl = image.select("SCL")
            clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
            return image.updateMask(clear).addBands(
                image.normalizedDifference(["B8", "B4"]).rename("NDVI")
            )

        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi)
        pre = collection.filterDate(pre_start, pre_end).map(add_clear_ndvi)
        post = collection.filterDate(post_start, post_end).map(add_clear_ndvi)

        pre_count, post_count = ee.List([pre.size(), post.size()]).getInfo()
        if not pre_count or not post_count:
            return _unavailable("No Sentinel-2 scenes were available in both comparison windows.", cloud_obscured=True)

        def mean_ndvi(images):
            value = images.select("NDVI").median().reduceRegion(
                reducer=ee.Reducer.mean(), geometry=roi, scale=10, bestEffort=True, maxPixels=1_000_000
            ).get("NDVI").getInfo()
            return float(value) if value is not None else None

        before, after = mean_ndvi(pre), mean_ndvi(post)
        if before is None or after is None:
            return _unavailable("Sentinel-2 scenes were found, but a clear NDVI value was unavailable.", cloud_obscured=True)
        delta = max(0.0, before - after)
        return SatelliteSpectralSummary(
            source="earth_engine", pre_event_ndvi=round(before, 3),
            post_event_ndvi=round(after, 3), delta_ndvi=round(delta, 3),
            spectral_loss_detected=delta > 0.15, cloud_obscured=False,
            message="Sentinel-2 surface-reflectance observations; 200 m buffer around the supplied coordinate.",
        )
    except Exception as exc:
        # Provider errors are deliberately not returned verbatim to public clients.
        return _unavailable(f"Earth Engine query failed ({type(exc).__name__}); satellite evidence is unavailable.")
