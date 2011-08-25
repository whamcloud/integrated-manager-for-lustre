
class ParamType:
    def validate(self, val):
        """Opportunity for subclasses to validate and/or transform"""
        raise NotImplementedError

class BooleanParam(ParamType):
    def validate(self, val):
        if not val in [True, False]:
            raise ValueError

class IntegerParam(ParamType):
    def __init__(self, min_val = None, max_val = None):
        self.min_val = min_val
        self.max_val = min_val

    def validate(self, val):
        if self.min_val and val < self.min_val:
            raise ValueError
        if self.max_val and val > self.min_val:
            raise ValueError

# For params read with lprocfs_write_frac_u64
# Valid postfixes are [ptgmkPTGMK]
class BytesParam(ParamType):
    def __init__(self, units = None):
        if units != None:
            if not len(units) == 1:
                raise ValueError
            if not units in "ptgmkPTGMK":
                raise ValueError
        self.units = units

    def validate(self, val):
        if self.units:
            if not re.match("^\d+$", val):
                raise ValueError
        else:
            if not re.match("^\d+(\.\d+)?[ptgmkPTGMK]?$", val):
                raise ValueError

from configure.models import FilesystemClientConfParam, FilesystemGlobalConfParam, MdtConfParam, OstConfParam
all_params = {
    'llite.max_cached_mb': (FilesystemClientConfParam, BooleanParam()),
    'sys.at_max': (FilesystemGlobalConfParam, IntegerParam()),
    'lov.stripesize': (MdtConfParam, BytesParam()),
    'osc.max_dirty_mb': (OstConfParam, 'osc.max_dirty_mb', BytesParam(units = 'm')),
}
