# Constants to be used across the application

# Conterminous U.S. Coordinates plus Canada and Alaska
min_latitude = 24.6
max_latitude = 71.2
min_longitude = -168.7
max_longitude = -65

EARTHQUAKE_DATA_URL = f"https://earthquake.usgs.gov/fdsnws/event/1/query"
RADIUS_OF_EARTH = 6371.0  # Radius of the Earth in kilometers
MAX_MAGNITUDE = 10  # Assume 10 on Richter scale is the max
MAX_RISK_FACTOR_TO_INSURE = (
    0.22  # Arbitrary threshold to decide whether to insure a property or not
)
NEARBY_EARTHQUAKE_RADIUS_KM = (
    200  # Assume that we only care about earthquakes with 200KM of the property
)
