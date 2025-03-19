from src.earthquake_risk_assessor import get_client_locations_with_earthquake_risk
from src.logger import logger


def example_2():
    logger.info(
        "Running Example 2 - Calculating risk assessment for the client locations"
    )
    for client_location in get_client_locations_with_earthquake_risk():
        print(
            f"The earthquake risk factor for {client_location.full_address} is "
            f"should_insure={client_location.earthquake_risk.should_insure} "
            f"due to a total risk factor of {client_location.earthquake_risk.total_risk_factor}.\n"
            f"There were {client_location.earthquake_risk.nearby_earthquakes} nearby earthquakes "
            f"with an average magnitude of {client_location.earthquake_risk.avg_magnitude}"
        )


if __name__ == "__main__":
    example_2()
