# -*- coding: utf-8 -*-
import datetime as dt
import delorean
# import holidays
# from pandas import bdate_range
from common.fargable import FargAble
# from types import MethodType
# from dateutil.relativedelta import relativedelta as reldelta


DEL_LY_KEYS = [
    'year',
    'month',
    'week',
    'day',
    'hour',
    'minute',
    'second'
]

DELOREAN_FREQ = {
    'YEARLY': 0,
    'MONTHLY': 1,
    'WEEKLY': 2,
    'DAILY': 3,
    'HOURLY': 4,
    'MINUTELY': 5,
    'SECONDLY': 6,
    'dates': delorean.dates,
    'exceptions': delorean.exceptions,
    'interface': delorean.interface
}

TIMEZONE_COUNTRY = {
    timezone: countrycode
    for countrycode in delorean.dates.pytz.country_timezones
    for timezone in delorean.dates.pytz.country_timezones[countrycode]
}


# def get_business_day(src_dt, direction, num_shifts=1):
#     shift_func_name = "{}_day".format(direction)
#     src_del = NewDelorean(src_dt)
#     ccode = TIMEZONE_COUNTRY.get(src_del.timezone.zone, 'US')
#     for i in range(num_shifts):  # pylint: disable=unused-variable
#         first_shift = False
#         while not all([src_del.is_workday(country=ccode), first_shift]):
#             src_del = getattr(
#                 src_del, shift_func_name)(1)
#             if not first_shift:
#                 first_shift = True
#     return src_del.datetime


def iso_delcap(dt_string, dayfirst=None, yearfirst=None):
    return delorean.interface.capture(
        dt_string, dayfirst=dayfirst, yearfirst=yearfirst)


def possible_timezones(tz_offset, common_only=True):
    favored_tz_names = set([
        'Pacific/Midway', 'Europe/Paris', 'Europe/Athens', 'Europe/Moscow',
        'Asia/Dubai', 'Asia/Karachi', 'Antarctica/Vostok', 'Asia/Bangkok',
        'Asia/Hong_Kong', 'Asia/Tokyo', 'Australia/Sydney', 'Pacific/Auckland'
    ])
    # pick one of the timezone collections
    timezones = (
        delorean.dates.pytz.common_timezones
        if common_only else delorean.dates.pytz.all_timezones)
    # convert the float hours offset to a timedelta
    offset_days, offset_seconds = 0, int(tz_offset * 3600)
    if offset_seconds < 0:
        offset_days = -1
        offset_seconds += 24 * 3600
    desired_delta = delorean.dates.timedelta(offset_days, offset_seconds)
    # Loop through the timezones and find any with matching offsets
    null_delta = delorean.dates.timedelta(0, 0)
    results = []
    for tz_name in timezones:
        tz = delorean.dates.pytz.timezone(tz_name)
        non_dst_offset = getattr(tz, '_transition_info', [[null_delta]])[-1]
        if desired_delta == non_dst_offset[0]:
            results.append(tz_name)
    preferred_name = set(results) & favored_tz_names
    if preferred_name:
        results.append(preferred_name.pop())
    return results


def likely_tz(tz_offset):
    try:
        result = possible_timezones(tz_offset)[-1]
    except Exception:
        result = None
    return result


class UseDefaultValue(Exception):
    """Use the default value for the variable being initialized!"""


class MyDelorean(delorean.Delorean):

    @property
    def time(self):
        return self._dt.time()

    # @property
    # def is_workday(self):
    #     ccode = TIMEZONE_COUNTRY.get(self.timezone.zone, 'US')
    #     return self.is_spec_workday(country=ccode)

    # def is_spec_workday(self, country='US', prov=None, state=None):
    #     if country == 'CA' and not prov:
    #         # temp. fix until patched issue#152 in holidays is released live
    #         prov = ' '
    #     return self.workday_workhorse(
    #         country=country, prov=prov, state=state)

    # def workday_workhorse(self, **kwargs):
    #     holiday_kwargs = {
    #         key: value for key, value in kwargs.items() if value}
    #     relevant_holidays = holidays.CountryHoliday(**holiday_kwargs)
    #     is_weekend_or_holiday = (
    #         (not bool(len(bdate_range(self.datetime, self.datetime))))
    #         or
    #         (bool(self.date in relevant_holidays)))
    #     return not is_weekend_or_holiday

    def isoformat(self, *args, **kwargs):
        return self.datetime.isoformat(*args, **kwargs)

    def local_naive(self):
        return self.datetime.replace(tzinfo=None)

    def start(self, timezone=None, **kwargs):
        DeloreanClass = self.__class__
        # start = delparse(self)
        if 'freq' not in kwargs:
            raise Exception("Please provide a frequency argument (freq=)")
        if 'stop' not in kwargs and 'count' not in kwargs:
            raise Exception("A stop datetime or a count is required!")
        elif 'count' not in kwargs:
            kwargs['stop'] = DeloreanClass(kwargs['stop']).local_naive()
        if timezone:
            if hasattr(timezone, 'zone'):
                timezone = timezone.zone
            referant = self.shift(timezone)
        else:
            referant = self.__class__(self)
        timezone = referant.timezone.zone
        for stop in delorean.stops(start=referant.local_naive(),
                                   timezone=timezone, **kwargs):
            yield DeloreanClass(stop.datetime)

    def stop(self, timezone=None, **kwargs):
        DeloreanClass = self.__class__
        if 'freq' not in kwargs:
            raise Exception("Please provide a frequency argument (freq=)")
        if 'start' not in kwargs and 'count' not in kwargs:
            raise Exception("A start datetime or a count is required!")
        if 'start' not in kwargs:
            start = (getattr(self, 'last_{}'.format(
                DEL_LY_KEYS[kwargs.get('freq')]))(
                    kwargs.get('count')))  # .replace(tzinfo=None)
        else:
            start = DeloreanClass(kwargs['start'])
            kwargs['stop'] = self
            del kwargs['start']
        return start.start(timezone=timezone, **kwargs)

    # pylint: disable=arguments-differ
    def _shift_date(self, direction, unit, *args, **kwargs):
        """
        Shift datetime in `direction` in _VALID_SHIFT_DIRECTIONS and by some
        unit in _VALID_SHIFTS and shift that amount by some multiple,
        defined by by args[0] if it exists

        If given a value indicating that DST changes should be respected, or
        no value, the function will make an absolute shift of the number of
        units in the specified direction and return the resulting datetime,
        which may include a DST-change-induced offset.

        If instructed to ignore DST changes, the function will apply the shift
        to the initial datetime, and return a new object initialized from the
        shifted naive datetime in the same timezone.

        That is, shifting from "2019-01-01 09:00:00" in EST by 120 days will,
        by default, return "2019-05-01 10:00:00", reflecting that the ending
        datetime expressed in UTC is the correct duration after the starting
        datetime expressed in UTC.  If instructed to not respect DST changes,
        the resulting datetime would be "2019-05-01 09:00:00" which is the same
        'local time' on the future date specified, but would not actually be
        10,368,000 seconds (120 days) after the initial starting date.
        """
        my_dt = self._dt

        nameddays = [
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday']
        args_list = list(args)
        try:  # Set up the number of shifts we need to do. (Default = 1)
            try:  # check for kwargs first
                num_shifts = int(kwargs['num_shifts'])
            except KeyError:  # no keyword argument for this
                # Note, if a kwarg for this was passed but it's not able to be
                # coerced to an integer, we want that exception to be raised.
                try:  # check args
                    arg_num_shifts = args_list.pop(0)
                    num_shifts = int(arg_num_shifts)
                except ValueError:
                    # we popped the value but it's not coercable to int
                    # put it back on the front of the args list, because we're
                    # to be clever here about adaptable argument structure.
                    args_list = [arg_num_shifts] + args_list
                    raise UseDefaultValue("no help for it, I s'pose...")
                except IndexError:
                    # No args available, use default
                    raise UseDefaultValue("no help for it, I s'pose...")
        except UseDefaultValue:
            num_shifts = 1

        try:  # Set up respect for DST shifts. (Default = True)
            # if unspecified, this Delorean-derived class will assume that
            # any date/time adjustments should reflect DST changes, so
            # calling delorean_obj.next_week(2) one week before DST changes
            # will return a result with a time component reflecting the
            # one-hour offset.  March 3rd, 2018, at 13:00:00 would update
            # to March March 17th, 2018, at 14:00:00 after a .next_week(2)
            # In effect, this forces the system to deal with all times in
            # UTC, and only render them in other timezones.
            # ...
            # There are caveats to this method, of course, but there are
            # other issues with failing to do this, it's a trade-off.
            try:  # check for kwargs first
                respect_dst = bool(
                    kwargs.get('rdst', kwargs['respect_dst']))
            except KeyError:  # no keyword argument for this
                # Note, if a kwarg for this was passed but it's not able to be
                # coerced to a boolean, we want that exception to be raised.
                # Not sure how that'd happen, but account for it anyway.
                try:
                    arg_respect_dst = args_list.pop(0)
                    respect_dst = bool(arg_respect_dst)
                except (IndexError, ValueError):
                    # no args available, or unable to coerce the arg to a bool,
                    # use default value.
                    raise UseDefaultValue("No other options, really...")
        except UseDefaultValue:
            respect_dst = True

        unitfill = unit
        # if unitfill.lower() in ['workday', 'businessday']:
        #     shift_func = get_business_day
        # else:
        if unitfill in nameddays:
            unitfill = 'namedday'

        shift_func = getattr(delorean.dates, 'move_datetime_%s' % unitfill)

        if unitfill != unit:  # shifting to target by named day
            for n in range(num_shifts):  # pylint: disable=unused-variable
                my_dt = shift_func(my_dt, direction, unit)
        else:
            my_dt = shift_func(my_dt, direction, num_shifts)

        if respect_dst:  # Include the DST-change-induced shift
            result = self.__class__(datetime=my_dt).shift(self.timezone.zone)
        else:
            result = self.__class__(
                datetime=my_dt.replace(tzinfo=None), timezone=self.timezone)

        return result

    def __json_encode__(self):
        # should return primitive, serializable types
        # like dict, list, int, string, float...
        return self.isoformat()

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self._VALID_SHIFT_UNITS = tuple(
    #         set(self._VALID_SHIFT_UNITS) | set(['workday', 'businessday']))


class NewDelorean(FargAble, MyDelorean):
    YEARLY = 0
    MONTHLY = 1
    WEEKLY = 2
    DAILY = 3
    HOURLY = 4
    MINUTELY = 5
    SECONDLY = 6
    dates = delorean.dates
    exceptions = delorean.exceptions
    interface = delorean.interface
    _oargs = ('datetime',
              'timezone',
              'date_thing',
              'astz',
              'dayfirst',
              'yearfirst')

    def offset(self, tz_offset=0, **kwargs):  # pylint: disable=unused-argument
        return self.__class__(self).shift(possible_timezones(tz_offset)[-1])

    def parse(self, dt_string, timezone=None, dayfirst=None, yearfirst=None):
        this_dt = iso_delcap(dt_string, dayfirst=dayfirst, yearfirst=yearfirst)

        if timezone:
            this_dt = this_dt.replace(tzinfo=None)
        elif this_dt.tzinfo is None:
            # assuming datetime object passed in is UTC
            this_dt = this_dt.replace(tzinfo=delorean.dates.pytz.utc)
        elif isinstance(this_dt.tzinfo, delorean.interface.tzoffset):
            utcoffset = this_dt.tzinfo.utcoffset(None)
            total_seconds = (
                (utcoffset.microseconds + (
                    utcoffset.seconds + (
                        utcoffset.days * 24 * 3600)) * 10**6) / 10**6)
            tz = delorean.interface.pytz.FixedOffset(total_seconds / 60)
            this_dt = this_dt.replace(tzinfo=tz)
        elif isinstance(this_dt.tzinfo, delorean.interface.tzlocal):
            tz = delorean.interface.get_localzone()
            this_dt = this_dt.replace(tzinfo=tz)
        else:
            this_dt = delorean.interface.pytz.utc.normalize(this_dt)
            # making this_dt naive so we can pass it to Delorean
            this_dt = this_dt.replace(tzinfo=delorean.dates.pytz.utc)
        return this_dt

    def __mid_init__(self, *args, **kwargs):
        fargs = dict(self.fargs)
        obj_kwargs = {"datetime": None}
        astz = argtz = fargs.get('timezone', fargs.get('astz', None))
        date_thing = fargs.get('datetime', fargs.get('date_thing', None))
        if not astz:
            astz = 'utc'
        elif isinstance(astz, (int, float)):
            try:
                astz = possible_timezones(astz)[-1]
            except Exception:
                astz = 'utc'
        try:
            if isinstance(date_thing, delorean.Delorean):
                if argtz:
                    obj_kwargs['datetime'] = date_thing.datetime.replace(
                        tzinfo=None)
                    obj_kwargs['timezone'] = argtz
                else:
                    obj_kwargs['datetime'] = date_thing.datetime
            elif date_thing is None or (hasattr(date_thing, 'lower') and
                                        date_thing.lower().startswith("now")):
                if argtz:
                    obj_kwargs['timezone'] = argtz
            else:
                raise Exception("no special case handling")
        except delorean.exceptions.DeloreanInvalidTimezone:
            raise
        except delorean.dates.pytz.exceptions.UnknownTimeZoneError:
            raise
        except AttributeError:
            raise
        except Exception:
            try:
                obj_kwargs['datetime'] = delorean.epoch(date_thing).naive
            except TypeError:  # date_thing is not an int/float/decimal
                try:
                    obj_kwargs['datetime'] = self.parse(
                        date_thing,
                        timezone=astz,
                        dayfirst=fargs['dayfirst'],
                        yearfirst=fargs['yearfirst'])
                except TypeError:  # date_thing is not a valid datetime string
                    try:
                        if hasattr(date_thing, 'tzinfo') and\
                           date_thing.tzinfo and argtz is None:
                            astz = date_thing.tzinfo.zone
                        obj_kwargs['datetime'] = self.parse(
                            date_thing.isoformat(),
                            timezone=astz,
                            dayfirst=fargs['dayfirst'],
                            yearfirst=fargs['yearfirst'])
                    except AttributeError:
                        try:
                            obj_kwargs['datetime'] = dt.datetime(
                                *date_thing)
                        except TypeError:
                            obj_kwargs['datetime'] = dt.datetime(
                                **date_thing)
        if not obj_kwargs.get('timezone'):
            obj_kwargs['timezone'] = astz
        self.oargs = ['timezone']
        self.rargs = ['datetime']
        del self.request['kwargs']
        del self.request['args']
        self.request['kwargs'] = obj_kwargs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for attr, val in DELOREAN_FREQ.items():
            setattr(self, attr, val)

    def __repr__(self):
        return f"New{super().__repr__()}"
