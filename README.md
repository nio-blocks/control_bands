ControlBands
============
The ControlBands block creates 'Moving Range' charts for different numeric values. This block will maintain 'bands' for a period of time and for different groups of signals. A band is a moving range calculation that updates dynamically with incoming signals. The block also outputs the mean, count, and sum of the signals inside the **band interval**, and is useful for determining if signal values are outliers.

Properties
----------
- **backup_interval**: An interval of time that specifies how often persisted data is saved.
- **band_interval**: The time range of signals used to calculate the band data.
- **group_by**: The signal attribute on the incoming signal whose values will be used to define groups on the outgoing signal.
- **load_from_persistence**: If `True`, the block’s state will be saved when the block is stopped, and reloaded once the block is restarted.
- **value_expr**: The incoming signal attribute that will be used for band data calculations.

Inputs
------
- **default**: Any list of signals with numeric values.

Outputs
-------
- **default**: Signal containing band data, value, mean, deviation, and deviations.

Commands
--------
- **groups**: Returns a list of the block’s current signal groupings.

Dependencies
------------
None

Output Description
------------------
-   **band_data**: A dictionary with data about the control bands for the signal's group
  - **value**: The value of the signal
  - **mean**: The mean of the band, exclusive of the signal's value.
  - **deviation**: The size of the band, exclusive of the signal's value. Equal to 0 if there is only one value in the band. This is equal to the mean of the moving ranges.
  - **deviations**: How many band sizes this signal's value is from the mean. Equal to 0 if there is only one value in the band.

