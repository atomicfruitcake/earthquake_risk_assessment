import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import requests
from geopy.geocoders import Nominatim

# Conterminous U.S. Coordinates plus Canada and Alaska
min_latitude = 24.6
max_latitude = 71.2
min_longitude = -168.7
max_longitude = -65

EARTHQUAKE_DATA_URL = f"https://earthquake.usgs.gov/fdsnws/event/1/query"
RADIUS_OF_EARTH = 6371.0  # Radius of the Earth in kilometers
MAX_MAGNITUDE = 10  # Assume 10 on Richter scale is the max
MAX_RISK_FACTOR_TO_INSURE = 0.22  # Arbitrary threshold to decide whether to insure a property or not

@dataclass
class EarthquakeLocation:
    state_name: str
    state_code: str


@dataclass
class Earthquake:
    time: datetime
    magnitude: float
    latitude: float
    longitude: float
    earthquake_location: EarthquakeLocation


@dataclass
class EarthquakeRisk:
    nearby_earthquakes: int
    nearby_total_magnitude: float
    avg_magnitude: float
    magnitude_factor: float
    num_quakes_factor: float
    total_risk_factor: float
    should_insure: bool


@dataclass
class ClientLocation:
    building_name: str
    location: str
    city: str
    state: str
    full_address: str
    latitude: float
    longitude: float
    earthquake_risk = EarthquakeRisk


def us_state_code_to_name_map() -> Dict[str, str]:
    with open("./data/us_states.txt") as f:  # Hawaii is not included in this list
        return {
            raw_state.split("|")[0]: raw_state.split("|")[-1].replace("\n", "")
            for raw_state in f.readlines()
        }


def us_state_name_to_code_map() -> Dict[str, str]:
    return {v: k for k, v in us_state_code_to_name_map().items()}


def parse_earthquake_location(place: str) -> Optional[EarthquakeLocation]:
    # These State codes are not valid but fall within longitude and latitude parameters
    skipped_states = ["Canada", "MX", "Mexico"]
    place_split = place.split(", ")
    state_name = place_split.pop()
    local = " ".join(place_split)
    if state_name in skipped_states:
        return None
    try:
        if len(state_name) == 2:
            state_code = state_name
            state_name = us_state_code_to_name_map()[state_code]
        else:
            state_code = us_state_name_to_code_map()[state_name]
    except KeyError:
        print(f"Warning, state {state_name} not recognised")
        return None
    return EarthquakeLocation(
        state_name=state_name,
        state_code=state_code,
    )


@lru_cache()
def fetch_raw_earthquake_data(
    start_time=(datetime.today() - timedelta(weeks=1)).strftime("%Y-%m-%d"),
    end_time=datetime.today().strftime("%Y-%m-%d"),
) -> csv.DictReader:
    """
    Fetch list of earthquakes from USGS API.
    By default, this will get all earthquakes in the conterminous US in the last week
    """
    print("Fetching raw earthquake data from USGS")
    response: requests.Response = requests.get(
        url=EARTHQUAKE_DATA_URL,
        params={
            "format": "csv",
            "eventtype": "earthquake",
            "minlatitude": min_latitude,
            "maxlatitude": max_latitude,
            "minlongitude": min_longitude,
            "maxlongitude": max_longitude,
            "starttime": start_time,
            "endtime": end_time,
        },
    )
    response.raise_for_status()
    return csv.DictReader(response.content.decode("utf-8").splitlines(), delimiter=",")


@lru_cache()
def parse_raw_earthquake_data(
    start_time=(datetime.today() - timedelta(weeks=1)).strftime("%Y-%m-%d"),
    end_time=datetime.today().strftime("%Y-%m-%d"),
) -> List[Earthquake]:
    print("Parsing the raw earthquake data")
    earthquakes: List[Earthquake] = []
    for earthquake in fetch_raw_earthquake_data(
        start_time=start_time, end_time=end_time
    ):
        earthquake_location: EarthquakeLocation = parse_earthquake_location(
            earthquake["place"]
        )
        if not earthquake_location:
            continue

        earthquakes.append(
            Earthquake(
                time=datetime.strptime(earthquake["time"], "%Y-%m-%dT%H:%M:%S.%f%z"),
                magnitude=float(earthquake["mag"]),
                latitude=float(earthquake["latitude"]),
                longitude=float(earthquake["longitude"]),
                earthquake_location=earthquake_location,
            )
        )
    return earthquakes


def haversine_distance(
    latitude_1: float, longitude_1: float, latitiude_2: float, longitude_2: float
):
    # Convert degrees to radians
    latitude_1_rad = math.radians(latitude_1)
    longitude_1_rad = math.radians(longitude_1)
    latitude_2_rad = math.radians(latitiude_2)
    longitude_2_rad = math.radians(longitude_2)

    # Difference in coordinates
    diff_latitude = latitude_2_rad - latitude_1_rad
    diff_longitude = longitude_2_rad - longitude_1_rad

    # Haversine formula
    chord = (
        math.sin(diff_latitude / 2) ** 2
        + math.cos(latitude_1_rad)
        * math.cos(latitude_2_rad)
        * math.sin(diff_longitude / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(chord), math.sqrt(1 - chord))

    # Distance in kilometers the between points
    distance = RADIUS_OF_EARTH * central_angle
    return distance


def is_within_radius(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
    radius_km: float,
) -> bool:
    distance = haversine_distance(latitude_1, longitude_1, latitude_2, longitude_2)
    return distance <= radius_km


def risk_rank_by_state() -> dict[str, dict[str, int | float]]:
    print("Calculating the risk rank by state")
    ranking = {}
    earthquake_data = parse_raw_earthquake_data()
    seen_states: List[str] = []
    for earthquake in earthquake_data:
        if earthquake.earthquake_location.state_code in seen_states:
            ranking[earthquake.earthquake_location.state_name]["magnitude"] += (
                earthquake.magnitude
            )
            ranking[earthquake.earthquake_location.state_name]["count"] += 1
        else:
            ranking[earthquake.earthquake_location.state_name] = {
                "magnitude": earthquake.magnitude,
                "count": 1,
            }
            seen_states.append(earthquake.earthquake_location.state_code)
    return {
        k: v
        for k, v in sorted(ranking.items(), key=lambda i: i[1]["count"], reverse=True)
    }


def get_lat_long_from_location(city: str) -> Tuple[float, float]:
    print(f"Fetching latitude and longitude for {city}")
    geolocator = Nominatim(user_agent="python/earthquake_risk_assessor")
    loc = geolocator.geocode(city + ", US")
    return loc.latitude, loc.longitude


@lru_cache()
def parse_client_locations() -> List[ClientLocation]:
    print("Parsing client locations data")
    client_locations: List[ClientLocation] = []
    with open("./data/client_locations.csv") as f:
        for raw_location in csv.DictReader(f):
            location = raw_location["Location"]
            city, state = location.split(", ")
            latitude, longitude = get_lat_long_from_location(city=city)
            client_locations.append(
                ClientLocation(
                    building_name=raw_location["Building Name"],
                    location=raw_location["Location"],
                    full_address=raw_location["Full Address"],
                    city=city,
                    state=state,
                    latitude=latitude,
                    longitude=longitude,
                )
            )
    return client_locations


def calculate_earthquake_risk_for_location(
    client_location: ClientLocation,
) -> ClientLocation:
    print(f"Calculating earthquake risk at {client_location.full_address}")
    earthquake_data = parse_raw_earthquake_data()
    nearby_total_magnitude = 0.0
    nearby_earthquakes = 0
    for earthquake in earthquake_data:
        if is_within_radius(
            latitude_1=earthquake.latitude,
            longitude_1=earthquake.longitude,
            latitude_2=client_location.latitude,
            longitude_2=client_location.longitude,
            radius_km=200,  # Assume that we only care about earthquakes with 200KM of the property
        ):
            nearby_total_magnitude += earthquake.magnitude
            nearby_earthquakes += 1

    client_location.nearby_total_magnitude = nearby_total_magnitude
    client_location.nearby_earthquakes = nearby_earthquakes
    avg_magnitude = nearby_total_magnitude / nearby_earthquakes
    magnitude_factor = 1 / (MAX_MAGNITUDE - avg_magnitude)
    num_quakes_factor = (1 / (1000 - nearby_earthquakes)) * 100
    total_risk_factor = magnitude_factor + num_quakes_factor
    should_insure = False if total_risk_factor >= 0.22 else True
    client_location.earthquake_risk = EarthquakeRisk(
        nearby_earthquakes=nearby_earthquakes,
        nearby_total_magnitude=nearby_total_magnitude,
        avg_magnitude=avg_magnitude,
        magnitude_factor=magnitude_factor,
        num_quakes_factor=num_quakes_factor,
        total_risk_factor=total_risk_factor,
        should_insure=should_insure,
    )
    return client_location


def get_client_locations_with_earthquake_risk():
    return [
        calculate_earthquake_risk_for_location(client_location=location)
        for location in parse_client_locations()
    ]

if __name__ == "__main__":
    get_client_locations_with_earthquake_risk()