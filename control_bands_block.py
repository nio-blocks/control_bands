from collections import defaultdict
from time import time as _time
from nio.util.attribute_dict import AttributeDict
from nio.common.block.base import Block
from nio.common.discovery import Discoverable, DiscoverableType
from nio.metadata.properties import TimeDeltaProperty, ExpressionProperty
from nio.metadata.properties.version import VersionProperty
from nio.modules.threading import Lock
from .band_data import BandData
from .mixins.group_by.group_by_block import GroupBy
from .mixins.persistence.persistence import Persistence


@Discoverable(DiscoverableType.block)
class ControlBands(GroupBy, Persistence, Block):

    band_interval = TimeDeltaProperty(
        default={"days": 1}, title="Band Interval")
    value_expr = ExpressionProperty(
        default="{{$value}}",
        title="Value",
        attr_default=AttributeError)
    version = VersionProperty("0.2.0")

    def __init__(self):
        super().__init__()
        self._band_values = defaultdict(list)
        self._signals_lock = Lock()

    def process_signals(self, signals, input_id='default'):
        sigs_out = self.for_each_group(self.record_values, signals)

        if sigs_out:
            self.notify_signals(sigs_out)

    def persisted_values(self):
        """ Overridden from persistence mixin """
        return {'band_values': '_band_values'}

    def record_values(self, signals, group):
        """ Save the time and the list of signals for each group.

        This will return signals with the mean/std dev included on them """
        sigs_out = []

        with self._signals_lock:
            ctime = _time()
            # First get rid of the old values
            self.trim_old_values(group, ctime)

            prev_values = self._get_current_values(group)
            self._logger.debug(
                "Previous values for group: {}".format(prev_values))
            # Start off a new band data using the latest value from the
            # previous band data objects
            new_values = BandData(prev_values.last_val)

            for sig in signals:
                try:
                    # the value must be a floating point value
                    value = float(self.value_expr(sig))

                    # Add the moving range data to the signal and add it to
                    # the list of signals to notify
                    sigs_out.append(self._enrich_signal(
                        sig, prev_values + new_values, value))

                    # Now account for the latest value in the moving range data
                    new_values.register_value(value)
                except:
                    self._logger.exception(
                        "Unable to determine value for signal {}".format(sig))

            # Archive the new values
            if new_values.count_items:
                self._band_values[group].append((ctime, new_values))

        return sigs_out

    def _enrich_signal(self, signal, band_data, value):
        """ Add relevant band data to the signal.

        Args:
            signal: The signal that we should add data to
            band_data (BandData): A single BandData object containing the
                current moving range information
            value: The value this signal contributed to the band data. This is
                used to determine how many deviations from the mean it is.

        Returns:
            The signal with updated data
        """
        range_mean = band_data.get_mean()
        range_deviation = band_data.get_range()
        if range_deviation != 0:
            deviations = (value - range_mean) / range_deviation
        else:
            deviations = 0

        band_data = AttributeDict({
            'value': value,
            'mean': range_mean,
            'deviation': range_deviation,
            'deviations': deviations
        })
        setattr(signal, 'band_data', band_data)

        return signal

    def _get_current_values(self, group):
        """ Returns a single BandData object for a group.

        This will make use of the __add__ function in the BandData class to
        sum together all of the current data points in the group. The result
        will be a single BandData object with all of the previously saved
        points accounted for. """
        cur_values = self._band_values[group]
        if len(cur_values) > 1:
            # Sum every BandData (after the first), using the first one as
            # the starting point
            return sum([data[1] for data in cur_values[1:]], cur_values[0][1])
        elif len(cur_values) == 1:
            return cur_values[0][1]
        else:
            return BandData()

    def trim_old_values(self, group, ctime):
        """ Remove any "old" saved values for a given group """
        group_values = self._band_values[group]
        self._logger.debug("Trimming old values - had {} items".format(
            len(group_values)))
        group_values[:] = [
            data for data in group_values
            if data[0] > ctime - self.band_interval.total_seconds()]
        self._logger.debug("Now has {} items".format(len(group_values)))
