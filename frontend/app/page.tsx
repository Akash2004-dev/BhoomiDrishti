'use client';

import React, { useState } from 'react';
import { GoogleMap, useJsApiLoader, MarkerF, CircleF } from '@react-google-maps/api';
import { Camera, Upload, AlertCircle, CheckCircle2, ShieldCheck, FileSpreadsheet, Loader2, RefreshCw } from 'lucide-react';

interface ClaimResult {
  claim_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  crop_type: string;
  damage_phenotype: string;
  visual_loss_percentage: number;
  satellite_source: 'earth_engine' | 'unavailable' | 'simulated';
  pre_event_ndvi?: number | null;
  post_event_ndvi?: number | null;
  satellite_ndvi_delta?: number | null;
  estimate_basis: string;
  evidence_note?: string | null;
  computed_final_loss_percentage: number | null;
  audit_verdict: string;
  tamper_hash: string;
  salvage_guidance: string;
  transcribed_context?: string;
}

function MapFallback() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-950 text-slate-500 text-xs">
      Map requires a configured Google Maps browser key. Coordinates are shown in the form.
    </div>
  );
}

function ConfiguredMap({ coords, apiKey }: { coords: { lat: number; lng: number }; apiKey: string }) {
  const { isLoaded } = useJsApiLoader({ id: 'google-map-script', googleMapsApiKey: apiKey });
  if (!isLoaded) return <MapFallback />;
  return (
    <GoogleMap
      mapContainerStyle={{ width: '100%', height: '100%' }}
      center={coords}
      zoom={15}
      options={{ mapTypeId: 'hybrid', disableDefaultUI: true, zoomControl: true }}
    >
      <MarkerF position={coords} />
      <CircleF center={coords} radius={200} options={{
        strokeColor: '#60a5fa', strokeOpacity: 0.8, strokeWeight: 2,
        fillColor: '#60a5fa', fillOpacity: 0.25,
      }} />
    </GoogleMap>
  );
}

export default function BhoomiDrishtiApp() {
  const [coords, setCoords] = useState({ lat: 20.7453, lng: 78.6022 });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [contextNotes, setContextNotes] = useState('Severe hailstorm flattened standing soybean crop.');
  const [eventDate, setEventDate] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClaimResult | null>(null);

  const handleCaptureLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      });
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!imageFile) {
      alert("Please upload a field damage image to audit.");
      return;
    }

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("latitude", coords.lat.toString());
    formData.append("longitude", coords.lng.toString());
    formData.append("event_date", eventDate);
    formData.append("context_notes", contextNotes);
    formData.append("image", imageFile);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/claims/process`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Error processing claim. Verify your backend server status.");
    } finally {
      setLoading(false);
    }
  };

  const loadVidarbhaExample = () => {
    setCoords({ lat: 20.7453, lng: 78.6022 });
    setContextNotes("Example coordinates only. Replace with the event and crop details for the field being reviewed.");
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold text-sm">
            BD
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">BhoomiDrishti भूमि दृष्टि</h1>
            <p className="text-xs text-slate-400">Satellite-to-ground crop damage evidence for human review</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={loadVidarbhaExample}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Set example coordinates</span>
          </button>
          <span className="text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-lg">
            Prototype · local configuration
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <section className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Field Damage Intake</h2>
            <span className="text-[11px] text-slate-500">Prototype · human review required</span>
          </div>

          <form onSubmit={handleFormSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Field coordinates (WGS84; not a cadastral boundary)</label>
              <div className="flex space-x-2">
                <input
                  type="number"
                  step="any"
                  value={coords.lat}
                  onChange={(e) => setCoords({ ...coords, lat: parseFloat(e.target.value) })}
                  className="w-1/2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono focus:border-emerald-500 outline-none"
                  placeholder="Latitude"
                />
                <input
                  type="number"
                  step="any"
                  value={coords.lng}
                  onChange={(e) => setCoords({ ...coords, lng: parseFloat(e.target.value) })}
                  className="w-1/2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono focus:border-emerald-500 outline-none"
                  placeholder="Longitude"
                />
              </div>
              <button
                type="button"
                onClick={handleCaptureLocation}
                className="mt-2 text-xs text-emerald-400 flex items-center space-x-1 hover:underline"
              >
                <Camera className="w-3.5 h-3.5" />
                <span>Acquire Precise Device Coordinates</span>
              </button>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1" htmlFor="event-date">Reported event date</label>
              <input
                id="event-date"
                type="date"
                value={eventDate}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono focus:border-emerald-500 outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Upload Ground Photo / Scan</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setImageFile(e.target.files ? e.target.files[0] : null)}
                className="w-full text-xs text-slate-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-500/20 file:text-emerald-400 hover:file:bg-emerald-500/30 cursor-pointer border border-slate-800 rounded-lg p-1 bg-slate-950"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">Farmer Observation & Weather Trigger</label>
              <textarea
                value={contextNotes}
                onChange={(e) => setContextNotes(e.target.value)}
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:border-emerald-500 outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 transition disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Synthesizing Space & Ground Telemetry...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>Execute Forensic Audit & Generate Dossier</span>
                </>
              )}
            </button>
          </form>

          {result && (
            <div className="mt-4 border border-emerald-500/30 bg-emerald-950/20 rounded-xl p-4 space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[10px] font-mono text-emerald-400 block">{result.claim_id}</span>
                  <h3 className="text-sm font-bold text-slate-100">{result.crop_type} ({result.damage_phenotype})</h3>
                </div>
                <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  {result.audit_verdict}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Visual Loss</span>
                  <span className="text-xs font-bold text-slate-200">{result.visual_loss_percentage}%</span>
                </div>
                <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 block">Sentinel-2 ΔNDVI</span>
                  <span className="text-xs font-bold text-slate-200">{result.satellite_ndvi_delta ?? 'Unavailable'}</span>
                </div>
                <div className="bg-slate-900/80 p-2 rounded-lg border border-emerald-500/40">
                  <span className="text-[10px] text-emerald-400 block">Prototype estimate</span>
                  <span className="text-xs font-extrabold text-emerald-300">{result.computed_final_loss_percentage == null ? 'Not calculated' : `${result.computed_final_loss_percentage}%`}</span>
                </div>
              </div>

              <div className="rounded border border-amber-500/30 bg-amber-950/20 p-2 text-[10px] text-amber-200">
                {result.satellite_source === 'earth_engine' ? 'Satellite source: Google Earth Engine.' : result.satellite_source === 'simulated' ? 'DEMO / SIMULATED SATELLITE DATA.' : 'Satellite evidence unavailable; no NDVI value was substituted.'}
                {' '}{result.estimate_basis}
              </div>

              {result.transcribed_context && (
                <div className="bg-slate-900/60 p-2 rounded border border-slate-800 text-[11px] text-slate-400 italic">
                  &ldquo;{result.transcribed_context}&rdquo;
                </div>
              )}

              <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-300">
                <strong className="text-emerald-400">AI suggestion · verify locally: </strong>
                {result.salvage_guidance}
              </div>

              <div className="text-[9px] font-mono text-slate-500 break-all border-t border-slate-800/80 pt-2">
                SHA-256 record fingerprint (integrity check, not proof of origin): {result.tamper_hash}
              </div>
            </div>
          )}
        </section>

        <section className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Location context & evidence availability
            </h2>
            <span className="text-xs text-slate-400 font-mono">Coordinate buffer is illustrative only</span>
          </div>

          <div className="flex-1 w-full min-h-[440px] rounded-xl overflow-hidden border border-slate-800 relative">
            {process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
              ? <ConfiguredMap coords={coords} apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY} />
              : <MapFallback />}
          </div>
        </section>
      </main>
    </div>
  );
}
