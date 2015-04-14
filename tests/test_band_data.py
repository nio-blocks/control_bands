import pickle
from ..band_data import BandData, LIMIT_FACTOR
from nio.util.support.block_test_case import NIOBlockTestCase

EXAMPLE_DATA = [49.6, 47.6, 49.9, 51.3, 47.8, 51.2, 52.6, 52.4, 53.6, 52.1]


class TestBandData(NIOBlockTestCase):

    """ Makes sure that the math performed by BandData objects is good.

        Use the examples from this site to test:
            http://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm
    """

    def test_calculation(self):
        """ Test that the calculations are correct for a single object """
        bd = BandData()
        [bd.register_value(data) for data in EXAMPLE_DATA]
        self._assert_correct_band_data(bd)

    def test_multiple(self):
        """ Test that the calculation can be split across multiple objects """
        bd1 = BandData()
        # Work over the first half of the example data
        [bd1.register_value(data) for data in EXAMPLE_DATA[:5]]

        # Start it off with the last value we used in the last one
        bd2 = BandData(EXAMPLE_DATA[4])
        # Work over the second half of the example data
        [bd2.register_value(data) for data in EXAMPLE_DATA[5:]]

        # The sum of the two band data objects should be correct
        self._assert_correct_band_data(bd1 + bd2)

    def test_picklable(self):
        """ Make sure BandData objects are picklable """
        bd = BandData()
        [bd.register_value(data) for data in EXAMPLE_DATA]
        pickle_bytes = pickle.dumps(bd)
        unpickled = pickle.loads(pickle_bytes)

        self._assert_correct_band_data(unpickled)

    def _assert_correct_band_data(self, band_data):
        """ Make sure the BandData has performed the calcuation correctly """
        self.assertEqual(band_data.count_items, len(EXAMPLE_DATA))
        self.assertEqual(band_data.count_ranges, len(EXAMPLE_DATA) - 1)
        # These values should match the calculated values on the website
        self.assertAlmostEqual(band_data.get_mean(), 50.81, 2)
        self.assertAlmostEqual(band_data.get_range(), 1.8778 / LIMIT_FACTOR, 4)
