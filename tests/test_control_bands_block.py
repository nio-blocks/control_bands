from collections import defaultdict
from unittest.mock import MagicMock
from time import time
from datetime import timedelta
from statistics import mean
from ..control_bands_block import ControlBands
from ..band_data import BandData
from nio.common.signal.base import Signal
from nio.util.support.block_test_case import NIOBlockTestCase


class BandDataFromList(BandData):

    def __init__(self, list_of_vals, prev_value=None):
        super().__init__(prev_value)
        for val in list_of_vals:
            self.register_value(val)


class TestControlBands(NIOBlockTestCase):

    def setUp(self):
        super().setUp()
        self._signals_notified = []
        self._blk = ControlBands()

        now = time()
        one_day_ago = now - timedelta(days=1).total_seconds()
        two_days_ago = now - timedelta(days=2).total_seconds()
        three_days_ago = now - timedelta(days=3).total_seconds()

        # Simulate some old data first
        self._blk._band_values = defaultdict(list, {
            'A': [
                (three_days_ago, BandDataFromList([1, 2, 3])),
                (two_days_ago, BandDataFromList([4, 5], 3)),
                (one_day_ago, BandDataFromList([6, 7, 8], 5))
            ],
            'B': [
                (two_days_ago, BandDataFromList([1, 2, 3])),
                (one_day_ago, BandDataFromList([8, 9], 3))
            ]
        })

        self.configure_block(self._blk, {
            "group_by": "{{$group}}",
            "value_expr": "{{$value}}",
            "band_interval": {
                "days": 2,
                "seconds": 300  # A little more than 2 days ago
            },
            "log_level": "DEBUG"
        })
        self._blk.start()

    def tearDown(self):
        self._blk.stop()
        super().tearDown()

    def get_test_modules(self):
        return super().get_test_modules() + ['persistence']

    def get_module_config_persistence(self):
        """ Make sure we use in-memory persistence """
        return {'persistence': 'default'}

    def test_drop_old(self):
        """ Tests that old values are dropped """
        result = self._blk.record_values([Signal({
            'group': 'A',
            'value': 5
        })], 'A')
        # Should return a list of one, since we called with one signal
        self.assertEqual(len(result), 1)
        expected = [4, 5, 6, 7, 8]
        # We don't want values from three days ago,
        # make sure we include the value we just added too
        self._assert_signal_meets_expected(result[0], expected, 5)

        # Now make sure the group got saved properly
        self.assertEqual(
            self._blk._get_current_values('A').count_items,
            len(expected) + 1)

        # Let's do another one, make sure it adds to the same group
        result = self._blk.record_values([Signal({
            'group': 'A',
            'value': 15
        })], 'A')
        self.assertEqual(len(result), 1)
        expected = [4, 5, 6, 7, 8, 5]
        self._assert_signal_meets_expected(result[0], expected, 15)
        self.assertEqual(
            self._blk._get_current_values('A').count_items,
            len(expected) + 1)

    def test_multiple_groups(self):
        """ Test that we keep different bands for different groups """
        a_result = self._blk.record_values([Signal({
            'group': 'A',
            'value': 5
        })], 'A')
        b_result = self._blk.record_values([Signal({
            'group': 'B',
            'value': 7
        })], 'B')

        self.assertEqual(len(a_result), 1)
        self.assertEqual(len(b_result), 1)
        a_expected = [4, 5, 6, 7, 8]
        b_expected = [1, 2, 3, 8, 9]

        self._assert_signal_meets_expected(a_result[0], a_expected, 5)
        self._assert_signal_meets_expected(b_result[0], b_expected, 7)

        # Did we update and save both groups?
        self.assertEqual(
            self._blk._get_current_values('A').count_items,
            len(a_expected) + 1)
        self.assertEqual(
            self._blk._get_current_values('B').count_items,
            len(b_expected) + 1)

    def test_new_group(self):
        """ Tests that new groups get added properly """
        # Let's try a new group
        c_result = self._blk.record_values([Signal({
            'group': 'C',
            'value': 5
        })], 'C')
        self.assertEqual(len(c_result), 1)

        # Make sure our new group got saved and that it has mean of 0
        cur_values = self._blk._get_current_values('C')
        self.assertEqual(cur_values.count_items, 1)
        self.assertEqual(cur_values.get_mean(), 5)
        self.assertEqual(cur_values.get_range(), 0)
        self.assertEqual(cur_values.last_val, 5)

    def test_multiple_signals(self):
        """ Tests that multiple signals are handled properly """
        result = self._blk.record_values([Signal({
            'group': 'A',
            'value': 5
        }), Signal({
            'group': 'A',
            'value': 6
        })], 'A')
        # Should return a list of two, since we called with two signals
        self.assertEqual(len(result), 2)

        first_expected = [4, 5, 6, 7, 8]
        second_expected = [4, 5, 6, 7, 8, 5]
        self._assert_signal_meets_expected(result[0], first_expected, 5)
        self._assert_signal_meets_expected(result[1], second_expected, 6)

        # Now make sure the group got saved properly
        self.assertEqual(
            self._blk._get_current_values('A').count_items,
            len(second_expected) + 1)

    def test_bad_values(self):
        """ Tests that bad values are ignored """
        result = self._blk.record_values([Signal({
            'group': 'A',
            'value': 5
        }), Signal({
            'group': 'A',
            'not_a_value': 10
        })], 'A')
        # Should return a list of one, since we called with one valid signal
        self.assertEqual(len(result), 1)

        # Don't expect to include the not_a_value
        expected = [4, 5, 6, 7, 8]
        self._assert_signal_meets_expected(result[0], expected, 5)

        # Now make sure the group got saved properly
        self.assertEqual(
            self._blk._get_current_values('A').count_items,
            len(expected) + 1)

    def test_signal_values(self):
        """ Make sure a signal gets the right band data values """
        bd = BandData()
        # Simulate 5 old values
        [bd.register_value(i) for i in range(5)]
        # Mean should be: 2.0
        # Range should be: 0.88652

        sig = Signal({'old': 'value'})
        sig_out = self._blk._enrich_signal(sig, bd, 10)

        # Make sure the old stuff stuck around
        self.assertEqual(sig_out.old, 'value')

        # Make sure all of the right band data got saved
        self.assertAlmostEqual(sig_out.band_data.value, 10)
        self.assertAlmostEqual(sig_out.band_data.mean, 2.0)
        self.assertAlmostEqual(sig_out.band_data.deviation, 0.8865, 3)
        self.assertAlmostEqual(
            sig_out.band_data.deviations, (10 - 2.0) / 0.8865, 3)


    def _assert_signal_meets_expected(self, signal, values_to_expect, value):
        """ Make sure that a signal's data matches what we thought we'd get """
        self.assertEqual(signal.band_data.value, value)
        self.assertAlmostEqual(
            signal.band_data.mean,
            mean(values_to_expect))

    def test_signals_notified(self):
        """ Test that the signals returned by record_values get notified """
        out_signals = [Signal({'sig': 1}), Signal({'sig': 2})]
        self._blk.record_values = MagicMock(return_value=out_signals)
        # Simulate something going into the block, doesn't matter what, the
        # recording of values is mocked
        self._blk.process_signals([Signal()])
        # Make sure we the block notified what record values returned
        self.assertEqual(self._signals_notified, out_signals)

    def signals_notified(self, signals, output_id='default'):
        self._signals_notified.extend(signals)
