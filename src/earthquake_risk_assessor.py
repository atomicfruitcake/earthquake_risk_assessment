import csv
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import backoff
from geopy.geocoders import Nominatim
from requests import Response, Session
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import HTTPError

from src.constants import *
from src.logger import logger

session = Session()

session.mount(
    prefix=EARTHQUAKE_DATA_URL,
    adapter=HTTPAdapter(
        max_retries=Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[
                400,
                401,
                403,
                500,
                502,
                503,
                504,
            ],  # Retry on these codes as USGS API can fail unexpectedly
        )
    ),
)


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


@lru_cache()
def __us_state_code_to_name_map() -> Dict[str, str]:
    # Cached here to save reading from disk each time we lookup a state name
    with open(
        f"{Path(os.path.realpath(__file__)).parent}/data/us_states.txt"
    ) as f:  # Hawaii is not included in this list as we do not insure property there
        return {
            raw_state.split("|")[0]: raw_state.split("|")[-1].replace("\n", "")
            for raw_state in f.readlines()
        }


@lru_cache()
def __us_state_name_to_code_map() -> Dict[str, str]:
    # Just invert and cache the code to name map for fast lookup
    return {v: k for k, v in __us_state_code_to_name_map().items()}


def us_state_code_to_name(state_code: str) -> str:
    """
    Lookup a US State code to from its name.
    For example, 'CA' would return 'California'
    :param state_code: str - Code of US State
    :return: str - Name of US State
    """
    return __us_state_code_to_name_map()[state_code]


def us_state_name_to_code(state_name: str) -> str:
    """
    Lookup a US State name to from its code.
    For example, 'California' would return 'CA'
    :param state_name: str - Name of US state
    :return: str - Code of US State
    """
    return __us_state_name_to_code_map()[state_name]


def parse_earthquake_location(place: str) -> Optional[EarthquakeLocation]:
    """
    Read a place name from the raw USGS API data and convert to an EarthquakeLocation object if it can be parsed
    :param place: str - place name from USGS API
    :return: EarthquakeLocation
    """
    # These State codes are not valid to be insured, but fall within longitude and latitude parameters
    skipped_states = ["Canada", "MX", "Mexico"]
    place_split = place.split(", ")
    state_name = place_split.pop()
    if state_name in skipped_states:
        logger.debug(
            f"State name {state_name} is not a valid location so will be skipped"
        )
        return None
    try:
        if len(state_name) == 2:
            state_code = state_name
            state_name = us_state_code_to_name(state_code)
        else:
            state_code = us_state_name_to_code(state_name)
    except KeyError:
        logger.info(f"Warning, state {state_name} not recognised")
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
    :param start_time: str - Date string in YYYY-MM-DD format by default set to 7 days ago
    :param end_time: str - Date string in YYYY-MM-DD format by default set to current day
    :return: csv.DictReader - Iterable list of dictionaries of earthquakes in date range
    """
    logger.info("Fetching raw earthquake data from USGS")
    response: Response = session.get(
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
    try:
        response.raise_for_status()
    except HTTPError:
        logger.exception("Error fetching raw earthquake data from USGS API.")
    return csv.DictReader(response.content.decode("utf-8").splitlines(), delimiter=",")


@lru_cache()
def parse_raw_earthquake_data(
    start_time=(datetime.today() - timedelta(weeks=1)).strftime("%Y-%m-%d"),
    end_time=datetime.today().strftime("%Y-%m-%d"),
) -> List[Earthquake]:
    """
    Parse the list of earthquakes from USGS API into a format suited for calculating risk to property
    By default, this will parse all earthquakes in the conterminous US in the last week
    :param start_time: str - Date string in YYYY-MM-DD format by default set to 7 days ago
    :param end_time: str - Date string in YYYY-MM-DD format by default set to current day
    :return: List[Earthquake] - List of Earthquake data classes
    """
    logger.info("Parsing the raw earthquake data")
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
    latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float
) -> float:
    """
    Calculate the distance between two points on the earths surface.
    :param latitude_1: float - latitude of first point
    :param longitude_1: float - longitude of first point
    :param latitude_2: float - latitude of second point
    :param longitude_2: float - longitude of second point
    :return: float - Distance in KM between the two points
    """
    # Convert degrees to radians
    latitude_1_rad = math.radians(latitude_1)
    longitude_1_rad = math.radians(longitude_1)
    latitude_2_rad = math.radians(latitude_2)
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

    # Distance in kilometers the between the points
    return RADIUS_OF_EARTH * central_angle


def is_within_distance(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
    limit_distance: float,
) -> bool:
    """
    Check whether two points on earth are within a given haver_distance
    :param latitude_1: float - latitude of first point
    :param longitude_1: float - longitude of first point
    :param latitude_2: float - latitude of second point
    :param longitude_2: float - longitude of second point
    :param limit_distance: float - haver_distance to check if points are within
    :return: bool - True if limit_distance between points is less that the haver_distance to check
    """
    haver_distance = haversine_distance(latitude_1, longitude_1, latitude_2, longitude_2)
    return haver_distance <= limit_distance


def risk_rank_by_state() -> dict[str, dict[str, int | float]]:
    logger.info("Calculating the risk rank by state")
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


# Add exponential backoff as network call can occasionally fail
@backoff.on_exception(backoff.expo, Exception, max_time=60)
def get_lat_long_from_location(city: str, country_code="US") -> Tuple[float, float]:
    """
    Get the global latitude and longitude coordinates for a given city
    :param city: str - Name of city
    :param country_code: str - Optional country code, by default uses 'US'
    :return: Tuple[float, float] - Latitude, Longitude
    """
    logger.info(f"Fetching latitude and longitude for {city}")
    geolocator = Nominatim(user_agent="python/earthquake_risk_assessor")
    loc = geolocator.geocode(city + f", {country_code}")
    return loc.latitude, loc.longitude


@lru_cache()
def parse_client_locations() -> List[ClientLocation]:
    """
    Parse the list of client locations provided from a CSV file into a list of ClientLocation objects
    """
    logger.info("Parsing client locations data")

    def parse_raw_location(raw_location: Dict[str, str]) -> ClientLocation:
        location = raw_location["Location"]
        city, state = location.split(", ")
        latitude, longitude = get_lat_long_from_location(city=city)
        return ClientLocation(
            building_name=raw_location["Building Name"],
            location=raw_location["Location"],
            full_address=raw_location["Full Address"],
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
        )

    with open(
        f"{Path(os.path.realpath(__file__)).parent}/data/client_locations.csv"
    ) as f:
        return [parse_raw_location(raw_location) for raw_location in csv.DictReader(f)]


def calculate_earthquake_risk_for_location(
    client_location: ClientLocation,
) -> ClientLocation:
    """
    Calculate the risk of an earthquake at a given client location
    :param client_location: ClientLocation - Location to check for earthquake risk
    :return: ClientLocation - Location with earthquake risk data added
    """
    logger.info(f"Calculating earthquake risk at {client_location.full_address}")
    earthquake_data = parse_raw_earthquake_data()
    nearby_total_magnitude = 0.0
    nearby_earthquakes = 0
    for earthquake in earthquake_data:
        if is_within_distance(
            latitude_1=earthquake.latitude,
            longitude_1=earthquake.longitude,
            latitude_2=client_location.latitude,
            longitude_2=client_location.longitude,
            limit_distance=NEARBY_EARTHQUAKE_RADIUS_KM,  # Assume that we only care about earthquakes with 200KM of the property
        ):
            nearby_total_magnitude += earthquake.magnitude
            nearby_earthquakes += 1

    # This section is a very basic approximation of generating a risk factor based on frequency of magnitude of nearby earthquakes
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


def get_client_locations_with_earthquake_risk() -> List[ClientLocation]:
    """
    Read the list of client locations and calculate the earthquake risk at each location
    """
    return [
        calculate_earthquake_risk_for_location(client_location=location)
        for location in parse_client_locations()
    ]
