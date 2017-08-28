ControlBands
============
Create 'Moving Range' charts for different numeric values.  This block will maintain 'bands' for a period of time and for different groups of signals. A band is basically a moving range calculation that updates dynamically. This block is useful for determining if a signal is an outlier from normal operation.  For an explanation on the mathematics of the moving range calculation, see http://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm

Properties
----------
- **backup_interval**: How often to save persisted data.
- **band_interval**: How far back data should be pulled from to populate band data.
- **group_by**: Signal attribute to define groupings of incoming signals.
- **load_from_persistence**: If true, the block’s state will be saved at a block stoppage and reloaded upon restart.
- **value_expr**: How to get the value out of the signal.

Inputs
------
- **default**: Any list of signals with numeric values.

Outputs
-------
- **default**: Signal containing band data, value, mean, deviation, and deviations.  See below for descriptions.

Commands
--------
- **groups**: Return a list of the block’s current signal groupings.

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

