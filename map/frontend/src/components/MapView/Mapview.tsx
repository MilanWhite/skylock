// MapView.tsx
import "maplibre-gl/dist/maplibre-gl.css";
import maplibregl, { Map } from "maplibre-gl";
import { useEffect, useRef, useState, memo } from "react";

type Ping = {
	deviceId: string;
	ts: string; // ISO string
	lat: number;
	lon: number;
	mode: "SOS" | "OK";
	pdop: number;
	answers: unknown;
};

const MAX_PINS = 500; // cap history to avoid leaks

type QA = { q: string; a: string };
function parseAnswers(raw: unknown) {
	// answers is a list like [{q:"in_danger", a:"yes"}, ...]
	const list = Array.isArray(raw) ? (raw as QA[]) : [];
	const rec: Record<string, string> = {};
	for (const it of list) {
		const q = String(it?.q ?? "")
			.trim()
			.toLowerCase();
		const a = String(it?.a ?? "")
			.trim()
			.toLowerCase();
		if (q) rec[q] = a;
	}
	const inDanger = rec["in_danger"] === "yes";
	const view = inDanger
		? [
				["in_danger", rec["in_danger"] ?? "unknown"],
				["injured", rec["injured"] ?? "unknown"],
				["alone", rec["alone"] ?? "unknown"],
				["threat_active", rec["threat_active"] ?? "unknown"],
		  ]
		: [
				["in_danger", rec["in_danger"] ?? "unknown"],
				["status", rec["status"] ?? "unknown"],
		  ];
	return { inDanger, view }; // view is [key,value][] for rendering
}

export default function MapView() {
	const ref = useRef<HTMLDivElement>(null);
	const mapRef = useRef<Map | null>(null);
	const [pings, setPings] = useState<Ping[]>([]);

	// map init
	useEffect(() => {
		const map: Map = new maplibregl.Map({
			container: ref.current!,
			style: "https://api.maptiler.com/maps/basic-v2-dark/style.json?key=wpIC7wyBfkCmBLDxyN8K",
			center: [-79.7624, 43.7315],
			zoom: 12,
		});
		mapRef.current = map;

		return () => {
			mapRef.current = null;
			map.remove();
		};
	}, []);

	// websocket -> append ping
	useEffect(() => {
		const host = window.location.hostname || "localhost";
		const WS_URL = `ws://${host}:4000/ws`;
		const ws = new WebSocket(WS_URL);

		ws.onmessage = (evt) => {
			try {
				const data = JSON.parse(evt.data);
				if (data?.type === "hello") return;
				const p = data as Ping;
				setPings((prev) => {
					const next = [...prev, p];
					if (next.length > MAX_PINS)
						next.splice(0, next.length - MAX_PINS);
					return next;
				});
			} catch {}
		};

		return () => {
			try {
				ws.close(1000, "unmount");
			} catch {}
		};
	}, []);

	return (
		<>
			<div ref={ref} style={{ height: "100vh", width: "100%" }} />
			{mapRef.current &&
				pings.map((p) => (
					<Pin
						key={`${p.deviceId}-${p.ts}`} // unique per ping
						map={mapRef.current}
						ping={p}
					/>
				))}
		</>
	);
}

// put this above Pin (once in the file)
function ensurePulseCSS() {
	if (document.getElementById("pin-pulse-css")) return;
	const css = `
@keyframes pin-pulse {
  0%   { transform: scale(1.8);   opacity: 0.35; }
  70%  { transform: scale(2.6); opacity: 0; }
  100% { transform: scale(2.6); opacity: 0; }
}
.pin-wrap { position: relative; width: 22px; height: 22px; }
.pin-dot  { position:absolute; inset:0; border-radius:50%; border:3px solid #fff; box-shadow:0 0 6px rgba(0,0,0,.6); box-sizing:border-box; }
.pin-ring {
  position:absolute; inset:0;
  border-radius:50%;
  animation: pin-pulse 1.8s ease-out infinite;
  pointer-events:none;
}`;
	const style = document.createElement("style");
	style.id = "pin-pulse-css";
	style.textContent = css;
	document.head.appendChild(style);
}

// replace your Pin with this version
const Pin = memo(function Pin({ map, ping }: { map: Map; ping: Ping }) {
	const markerRef = useRef<maplibregl.Marker | null>(null);
	const popupRef = useRef<maplibregl.Popup | null>(null);

	useEffect(() => {
		ensurePulseCSS();

		const { inDanger, view } = parseAnswers(ping.answers);
		const color = inDanger ? "#e11d48" : "#22c55e";

		// element with pulse
		const wrap = document.createElement("div");
		wrap.className = "pin-wrap";

		const dot = document.createElement("div");
		dot.className = "pin-dot";
		dot.style.background = color;

		const ring = document.createElement("div");
		ring.className = "pin-ring";
		ring.style.boxShadow = `0 0 0 2px ${color}`;
		ring.style.background = color;
		ring.style.opacity = "0.35";

		wrap.appendChild(ring);
		wrap.appendChild(dot);

		const answersTable = view
			.map(
				([k, v]) =>
					`<tr><td>${k}</td><td style="padding-left:8px;"><b>${v}</b></td></tr>`
			)
			.join("");

		const popupHTML = `<div style="font:12px/1.35 system-ui,-apple-system,Segoe UI,Roboto">
        <div><b>${ping.deviceId}</b> (${ping.mode})</div>
        <div>${ping.lat.toFixed(6)}, ${ping.lon.toFixed(6)}</div>
        <div>PDOP: ${ping.pdop}</div>
        <div>${new Date(ping.ts).toLocaleString()}</div>
        <hr style="margin:6px 0;border:none;border-top:1px solid #444">
        <div><b>Answers</b></div>
        <table style="border-collapse:collapse;margin-top:4px;"><tbody>${answersTable}</tbody></table>
      </div>`;

		const popup = new maplibregl.Popup().setHTML(popupHTML);
		popupRef.current = popup;

		const marker = new maplibregl.Marker({
			element: wrap,
			anchor: "center",
		})
			.setLngLat([ping.lon, ping.lat])
			.setPopup(popup)
			.addTo(map);

		markerRef.current = marker;

		return () => {
			popup.remove();
			marker.remove();
			popupRef.current = null;
			markerRef.current = null;
		};
	}, [map, ping]);

	return null;
});
