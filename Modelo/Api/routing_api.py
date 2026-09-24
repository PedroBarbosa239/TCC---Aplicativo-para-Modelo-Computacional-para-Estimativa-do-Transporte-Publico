import json
from urllib.parse import quote
from urllib.request import urlopen


OSRM_URL = "https://router.project-osrm.org"


def get_route(coordinates):
    """
    coordinates = [(latitude, longitude), ...]

    Retorna:
    {
        "distance": metros,
        "duration": segundos,
        "geometry": [(latitude, longitude), ...],
        "legs": [...],
        "legs_geometry": [
            [(lat, lon), ...],
            [(lat, lon), ...],
            ...
        ]
    }
    """

    if len(coordinates) < 2:
        raise ValueError(
            "É necessário informar pelo menos duas coordenadas."
        )

    coordinate_string = ";".join(
        f"{longitude},{latitude}"
        for latitude, longitude in coordinates
    )

    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{quote(coordinate_string, safe=';,')}"
        f"?overview=full"
        f"&geometries=geojson"
        f"&steps=true"
    )

    with urlopen(url, timeout=10) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    if data.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM não conseguiu calcular a rota: "
            f"{data.get('code')}"
        )

    route = data["routes"][0]

    # Geometria completa da rota
    geometry = route["geometry"]["coordinates"]

    geometry = [
        (latitude, longitude)
        for longitude, latitude in geometry
    ]

    # Geometria individual de cada trecho entre paradas
    legs_geometry = []

    for leg in route.get("legs", []):

        leg_points = []

        for step in leg.get("steps", []):

            step_geometry = step.get(
                "geometry",
                {}
            )

            step_coordinates = step_geometry.get(
                "coordinates",
                []
            )

            for longitude, latitude in step_coordinates:

                point = (latitude, longitude)

                if not leg_points or leg_points[-1] != point:
                    leg_points.append(point)

        legs_geometry.append(leg_points)

    return {
        "distance": route["distance"],
        "duration": route["duration"],
        "geometry": geometry,
        "legs": route.get("legs", []),
        "legs_geometry": legs_geometry
    }