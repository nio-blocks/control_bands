from collections import defaultdict
from time import time as _time
from statistics import mean, stdev
from nio.util.attribute_dict import AttributeDict
from nio.common.block.base import Block
from nio.common.discovery import Discoverable, DiscoverableType
from nio.metadata.properties import TimeDeltaProperty, ExpressionProperty
from nio.metadata.properties.version import VersionProperty
from nio.modules.threading import Lock
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
    version = VersionProperty("0.1.0")

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

            values = self._get_current_values(group)
            new_values = []

            for sig in signals:
                try:
                    value, signal = self._get_signal_value(
                        sig, values + new_values)

                    self._logger.debug("Signal {}".format(signal))

                    new_values.append(value)
                    sigs_out.append(signal)

                    self._logger.debug("Values now are {}".format(new_values))
                except:
                    self._logger.exception(
                        "Unable to determine value for signal {}".format(sig))

            # Archive the new values
            if new_values:
                self._band_values[group].append((ctime, new_values))

        return sigs_out

    def _get_signal_value(self, signal, values):
        """ Returns a tuple of the value and the output signal.

        Params:
            signal: The existing signal
            values: Any previously set values

        Returns:
            out (value, signal):
                value contains the value of this signal
                signal contains an enhanced signal with band data

        Raises:
            Exception if there is a problem determining the value
        """
        value = self.value_expr(signal)
        values.append(value)

        # TODO: Make this more efficient for large batches of signals
        _new_mean = mean(values)
        if len(values) > 1:
            # Deviation requires more than one value
            _new_stdev = stdev(values, _new_mean)
            _new_stdevs = (value - _new_mean) / _new_stdev
        else:
            # If we don't have enough values, use a 0 as the stdev
            _new_stdev = 0
            _new_stdevs = 0

        # TODO: Make it return old and new means/stdevs ???
        band_data = AttributeDict({
            'value': value,
            'mean': _new_mean,
            'stdev': _new_stdev,
            'stdevs': _new_stdevs
        })
        setattr(signal, 'band_data', band_data)

        return value, signal

    def _get_current_values(self, group):
        """ Returns a single list of values for a group """
        vals = []
        for data in self._band_values[group]:
            vals.extend(data[1])
        return vals

    def trim_old_values(self, group, ctime):
        """ Remove any "old" saved values for a given group """
        group_values = self._band_values[group]
        self._logger.debug("Trimming old values - had {} items".format(
            len(group_values)))
        group_values[:] = [
            data for data in group_values
            if data[0] > ctime - self.band_interval.total_seconds()]
        self._logger.debug("Now has {} items".format(len(group_values)))
