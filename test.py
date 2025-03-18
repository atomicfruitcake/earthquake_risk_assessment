import unittest
import earthquake_risk_assessor


class TestEarthquakeRiskAssessor(unittest.TestCase):

    def test_us_state_code_to_name_map(self):
        self.assertEqual(earthquake_risk_assessor.us_state_code_to_name_map()["CA"], "California")

    def test_us_state_name_to_code_map(self):
        self.assertEqual(earthquake_risk_assessor.us_state_name_to_code_map()["California"], "CA")

    def test_parse_earthquake_location_with_code(self):
        location = earthquake_risk_assessor.parse_earthquake_location(place="5 km WNW of Dublin, CA")
        self.assertEqual(location.state_name, "California")
        self.assertEqual(location.state_code, "CA")

    def test_parse_earthquake_location_with_name(self):
        location = earthquake_risk_assessor.parse_earthquake_location(place="10 km SSW of Ackerly, Texas")
        self.assertEqual(location.state_name, "Texas")
        self.assertEqual(location.state_code, "TX")

    def test_haversine_distance(self):
        dist = earthquake_risk_assessor.haversine_distance(
            latitude_1=1.,
            longitude_1=1.,
            latitiude_2=100.,
            longitude_2=100.
        )
        self.assertEqual(dist, 9724.911585481681)

    def test_is_within_radius(self):
        self.assertTrue(
            earthquake_risk_assessor.is_within_radius(
                latitude_1=1.,
                longitude_1=1.,
                latitude_2=100.,
                longitude_2=100.,
                radius_km=10000
            )
        )
        self.assertFalse(
            earthquake_risk_assessor.is_within_radius(
                latitude_1=1.,
                longitude_1=1.,
                latitude_2=100.,
                longitude_2=100.,
                radius_km=9000
            )
        )


if __name__ == '__main__':
    unittest.main()
