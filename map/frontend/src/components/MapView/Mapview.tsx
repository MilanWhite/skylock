// MapView.tsx
import maplibregl from "maplibre-gl";
import { Map } from "maplibre-gl";
import { useEffect, useRef } from "react";
export default function MapView() {
	const ref = useRef<HTMLDivElement>(null);
	useEffect(() => {
		const map: Map = new maplibregl.Map({
			container: ref.current!,
			style: `https://api.maptiler.com/maps/basic-v2-dark/style.json?key=wpIC7wyBfkCmBLDxyN8K`,
			center: [-79.7624, 43.7315],
			zoom: 12,
		});
		return () => map.remove();
	}, []);
	return <div ref={ref} style={{ height: "100vh" }} />;
}
