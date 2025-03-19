import unittest
import responses
from src.constants import EARTHQUAKE_DATA_URL
from src import earthquake_risk_assessor

_mock_earthquake_csv = """time,latitude,longitude,depth,mag,magType,nst,gap,dmin,rms,net,id,updated,place,type,horizontalError,depthError,magError,magNst,status,locationSource,magSource
2025-03-17T10:31:08.290Z,39.4998321533203,-122.950164794922,4.46999979019165,2.54,md,27,44,0.1867,0.15,nc,nc75150006,2025-03-17T12:42:18.823Z,"10 km NNE of Lake Pillsbury, CA",earthquake,0.27,1.79999995,0.17,26,automatic,nc,nc
2025-03-17T09:35:00.123Z,39.0627,-98.7019,5,3,mb_lg,35,42,0.639,0.61,us,us6000pzai,2025-03-17T14:44:30.012Z,"5 km SSW of Luray, Kansas",earthquake,3,1.995,0.046,126,reviewed,us,us
2025-03-17T09:17:24.610Z,33.4953333,-116.4495,4.76,2.57,ml,107,23,0.1164,0.19,ci,ci41081624,2025-03-17T13:16:40.682Z,"22 km ESE of Anza, CA",earthquake,0.1,0.58,0.15,25,automatic,ci,ci
"""


class TestEarthquakeRiskAssessor(unittest.TestCase):
    def setUp(self):
        # Mock the response from the USGS Earthquake API
        responses.add(
            method=responses.GET, url=EARTHQUAKE_DATA_URL, body=_mock_earthquake_csv
        )

    def test_us_state_code_to_name_map(self):
        self.assertEqual(
            earthquake_risk_assessor.us_state_code_to_name("CA"), "California"
        )

    def test_us_state_name_to_code_map(self):
        self.assertEqual(
            earthquake_risk_assessor.us_state_name_to_code("California"), "CA"
        )

    @responses.activate
    def test_fetch_raw_earthquake_data(self):
        raw_earthquake_data = earthquake_risk_assessor.fetch_raw_earthquake_data()
        self.assertEqual(len(list(raw_earthquake_data)), 3)

    @responses.activate
    def test_parse_raw_earthquake_data(self):
        earthquake_locations = earthquake_risk_assessor.parse_raw_earthquake_data()
        self.assertEqual(len(earthquake_locations), 3)

    def test_parse_earthquake_location_with_code(self):
        location = earthquake_risk_assessor.parse_earthquake_location(
            place="5 km WNW of Dublin, CA"
        )
        self.assertEqual(location.state_name, "California")
        self.assertEqual(location.state_code, "CA")

    def test_parse_earthquake_location_with_name(self):
        location = earthquake_risk_assessor.parse_earthquake_location(
            place="10 km SSW of Ackerly, Texas"
        )
        self.assertEqual(location.state_name, "Texas")
        self.assertEqual(location.state_code, "TX")

    def test_haversine_distance(self):
        dist = earthquake_risk_assessor.haversine_distance(
            latitude_1=1.0, longitude_1=1.0, latitude_2=100.0, longitude_2=100.0
        )
        self.assertEqual(dist, 9724.911585481681)

    def test_is_within_radius(self):
        self.assertTrue(
            earthquake_risk_assessor.is_within_distance(
                latitude_1=1.0,
                longitude_1=1.0,
                latitude_2=100.0,
                longitude_2=100.0,
                limit_distance=10000,
            )
        )
        self.assertFalse(
            earthquake_risk_assessor.is_within_distance(
                latitude_1=1.0,
                longitude_1=1.0,
                latitude_2=100.0,
                longitude_2=100.0,
                limit_distance=9000,
            )
        )


if __name__ == "__main__":
    unittest.main()
