from src.earthquake_risk_assessor import risk_rank_by_state
from src.logger import logger


def example_1():
    logger.info(
        "Running Example 1 - Finding which states experienced the most earthquakes last week"
    )
    for idx, (state, risk) in enumerate(risk_rank_by_state().items()):
        print(
            f"Ranking: {idx + 1} - "
            f"State: {state} - "
            f"Number of earthquakes: {risk['count']} - "
            f"Total Magnitude: {risk['magnitude']}"
        )


if __name__ == "__main__":
    example_1()
