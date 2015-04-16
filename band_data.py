# 1.128 is the value d_2 for n = 2
# http://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm
LIMIT_FACTOR = 1.128


class BandData():

    """ A class that contains deviation summary data of a list of values """

    def __init__(self, previous_value=None):
        self.count_items = 0
        self.sum_items = 0
        self.count_ranges = 0
        self.sum_ranges = 0
        self.last_val = previous_value

    def register_value(self, value):
        # We are going to account for this value in the sums regardless
        self.count_items += 1
        self.sum_items += value

        if self.last_val is not None:
            # We have some other data here, use it to build a range!
            self.count_ranges += 1
            self.sum_ranges += abs(self.last_val - value)

        self.last_val = value

    def get_mean(self):
        """ Returns the mean of the items that make up this data """
        if self.count_items == 0:
            return 0
        return self.sum_items / self.count_items

    def get_range(self):
        """ Returns the size of one "range" from the mean """
        if self.count_ranges == 0:
            return 0
        return self.sum_ranges / self.count_ranges / LIMIT_FACTOR

    def __add__(self, other):
        """ When adding multiple band data together, just return the sums """
        # default to the right side's last value
        result = BandData(other.last_val)
        result.count_items = self.count_items + other.count_items
        result.sum_items = self.sum_items + other.sum_items
        result.count_ranges = self.count_ranges + other.count_ranges
        result.sum_ranges = self.sum_ranges + other.sum_ranges
        return result

    def __str__(self):
        return str({
            "items": {
                "sum": self.sum_items,
                "count": self.count_items
            },
            "ranges": {
                "sum": self.sum_ranges,
                "count": self.count_ranges
            },
            "mean": self.get_mean(),
            "range": self.get_range()
        })
