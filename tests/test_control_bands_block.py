from collections import defaultdict
from unittest.mock import MagicMock
from time import time
from datetime import timedelta
from statistics import mean, stdev
from ..control_bands_block import ControlBands
from nio.common.signal.base import Signal
from nio.util.support.block_test_case import NIOBlockTestCase


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
                (three_days_ago, [1, 2, 3]),
                (two_days_ago, [4, 5]),
                (one_day_ago, [6, 7, 8])
            ],
            'B': [
                (two_days_ago, [1, 2, 3]),
                (one_day_ago, [8, 9])
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
        expected = [4, 5, 6, 7, 8, 5]
        # We don't want values from three days ago,
        # make sure we include the value we just added too
        self._assert_signal_meets_expected(result[0], expected, 5)

        # Now make sure the group got saved properly
        self.assertEqual(self._blk._get_current_values('A'), expected)

        # Let's do another one, make sure it adds to the same group
        result = self._blk.record_values([Signal({
            'group': 'A',
            'value': 15
        })], 'A')
        self.assertEqual(len(result), 1)
        expected = [4, 5, 6, 7, 8, 5, 15]
        self._assert_signal_meets_expected(result[0], expected, 15)
        self.assertEqual(self._blk._get_current_values('A'), expected)

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
        a_expected = [4, 5, 6, 7, 8, 5]
        b_expected = [1, 2, 3, 8, 9, 7]

        self._assert_signal_meets_expected(a_result[0], a_expected, 5)
        self._assert_signal_meets_expected(b_result[0], b_expected, 7)

        # Did we update and save both groups?
        self.assertEqual(self._blk._get_current_values('A'), a_expected)
        self.assertEqual(self._blk._get_current_values('B'), b_expected)

    def test_new_group(self):
        """ Tests that new groups get added properly """
        # Let's try a new group
        c_result = self._blk.record_values([Signal({
            'group': 'C',
            'value': 5
        })], 'C')
        self.assertEqual(len(c_result), 1)
        self._assert_signal_meets_expected(c_result[0], [5], 5)

        # Make sure our new group got saved
        self.assertEqual(self._blk._get_current_values('C'), [5])

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

        first_expected = [4, 5, 6, 7, 8, 5]
        second_expected = [4, 5, 6, 7, 8, 5, 6]
        self._assert_signal_meets_expected(result[0], first_expected, 5)
        self._assert_signal_meets_expected(result[1], second_expected, 6)

        # Now make sure the group got saved properly
        self.assertEqual(self._blk._get_current_values('A'), second_expected)

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
        expected = [4, 5, 6, 7, 8, 5]
        self._assert_signal_meets_expected(result[0], expected, 5)

        # Now make sure the group got saved properly
        self.assertEqual(self._blk._get_current_values('A'), expected)

    def _assert_signal_meets_expected(self, signal, values_to_expect, value):
        self.assertEqual(signal.band_data.value, value)
        self.assertAlmostEqual(
            signal.band_data.mean,
            mean(values_to_expect))
        if len(values_to_expect) > 1:
            self.assertAlmostEqual(
                signal.band_data.stdev,
                stdev(values_to_expect))
            self.assertAlmostEqual(
                signal.band_data.stdevs,
                (value - mean(values_to_expect)) / stdev(values_to_expect))
        else:
            # Lists of length one will have standard deviation and number of
            # standard deviations fixed at 0
            self.assertEqual(signal.band_data.stdev, 0)
            self.assertEqual(signal.band_data.stdevs, 0)

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
