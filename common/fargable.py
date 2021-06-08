# -*- coding: utf-8 -*-
from copy import deepcopy
from frozendict import frozendict

from common.exceptions import force_text, ValidationError
from common.assist import (
    coercelist, coercedict, getor, oara_argkwarg, kwargset)


class FargAble:
    _rargs = tuple()  # required arguments (that is, args w/o defaults)
    _oargs = tuple()  # optional arguments
    __odefs = frozendict({})  # persistent optional argument defaults
    __base_default = None  # default optional argument value

    @property
    def odefs(self):
        working_odefs = {a: self._base_default for a in self.oargs}
        working_odefs.update(self._odefs)
        return working_odefs

    @property
    def ordered_args(self):
        args = []
        args.extend(coercelist(self.rargs))
        args.extend(coercelist(self.oargs))
        return args

    @property
    def fargs(self):  # invoked arguments based on args, kwargs, and defaults
        args = getor(getattr(self, 'request', None), 'args', tuple())
        kwargs = getor(getattr(self, 'request', None), 'kwargs', dict())
        for reserved_kwarg in ['req_args', 'opt_defaults']:
            if kwargs.get(reserved_kwarg, None):
                kwargs['__{}'.format(reserved_kwarg)] = kwargs[reserved_kwarg]
                del kwargs[reserved_kwarg]
        return oara_argkwarg(
            self.oargs, req_args=self.rargs, opt_defaults=self.odefs,
            *args, **kwargs)

    def __mid_init__(self, *args, **kwargs):
        pass

    def __init__(self, *args, **kwargs):
        self.rargs = coercelist(self._rargs)
        self.oargs = coercelist(self._oargs)
        self._odefs = coercedict(self.__odefs)
        self._base_default = deepcopy(self.__base_default)
        self.request = {'args': args, 'kwargs': kwargs}
        try:
            self.__mid_init__(*args, **kwargs)
        except Exception:
            print(self.fargs)
            raise
        # print self.fargs
        super(FargAble, self).__init__(**self.fargs)


class ValFargAble(FargAble):
    _rarg_validation = frozendict({})
    _oarg_validation = frozendict({})

    def __init__(self, *args, **kwargs):
        self.rarg_validation = coercedict(self._rarg_validation)
        self.oarg_validation = coercedict(self._oarg_validation)
        super(ValFargAble, self).__init__(*args, **kwargs)

    @property
    def farg_validation(self):
        fargval = {}
        rargval = deepcopy(self.rarg_validation)
        oargval = deepcopy(self.oarg_validation)
        fargval.update(oargval)
        fargval.update(rargval)
        return fargval

    @property
    def fargs(self):
        # pylint: disable=unused-variable
        if set(self.rargs) <= set(self.rarg_validation.keys()):
            pass
        else:
            debug_one = self.rargs
            debug_two = self.rarg_validation.keys()
            raise ValidationError("Required argument/validation mismatch")
        fargs = super(ValFargAble, self).fargs
        vargs = self.rargs + self.oargs
        for farg_name in vargs:
            # print farg_name
            is_valid = self.farg_validation.get(
                farg_name, (lambda farg, **kwargs: True))
            farg = fargs.get(farg_name, None)
            validation_check = is_valid(farg, **fargs)
            if validation_check is not True:
                # not the same as `if not validation_check` !!
                raise ValidationError(
                    "Argument {} (`{}`) failed validation: {}".format(
                        farg_name, farg, force_text(validation_check)))
        return fargs


class TestFarg(FargAble, kwargset):
    _oargs = tuple(['optional'])
    _rargs = tuple(['test'])

    def __mid_init__(self, *args, **kwargs):
        # print(self.fargs)
        if 'optional' in self.fargs:
            self.oargs = tuple()
            if 'optional' in self.request['kwargs']:
                del self.request['kwargs']['optional']
