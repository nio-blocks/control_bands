# ControlBands

Capture the mean and standard deviation of numeric values.

This block will maintain "bands" for a period of time and for different groups of signals. A band is basically a mean and standard deviation that updates dynamically. This block is useful for determining if a signal is an outlier from normal operation.


Properties
--------------
-   **Band Interval** (timedelta): How far back data should be pulled from to populate band data
-   **Value** (expression): How to get the value out of the signal
-   **group_by**: Expression proprety. The value by which signals are grouped. There is one band per group.


Dependencies
----------------
[GroupBy Mixin](https://github.com/nio-blocks/mixins/tree/master/group_by)

Commands
----------------
None

Input
-------
Any list of signals with numeric values.

Output
---------

-   **band_data**: A dictionary with data about the control bands for the signal's group
  - **value**: The value of the signal
  - **mean**: The mean of the band (inclusive of the signal's value)
  - **stdev**: The standard deviation of the band (inclusive of the signal's value). Equal to 0 if there is only one value in the band.
  - **stdevs**: How many standard devations this signal's value is from the mean. Equal to 0 if there is only one value in the band.
