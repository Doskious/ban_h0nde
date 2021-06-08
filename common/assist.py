# -*- coding: utf-8 -*-
import inspect
import itertools
import functools
import json
import logging
import re
import unidecode
from frozendict import frozendict
from common.constants import UUID_REGEX_EXPR
from common.exceptions import force_text


DIT_GRP = re.compile(r'^(\.?[\w\.]+?)\.(\w+?)$')
UUID_RE = re.compile(UUID_REGEX_EXPR)


def reduce(apply_this, iterable, initializer=None):
    iter_thing = iter(iterable)
    if initializer is None:
        try:
            initializer = next(iter_thing)
        except StopIteration:
            raise TypeError(
                "Unable to reduce() empty sequence with no initial value.")
    result = initializer
    for term in iter_thing:
        result = apply_this(result, term)
    return result


class general_function_handler:
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, obj_type=None):
        return self.__class__(self.func.__get__(obj, obj_type))

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except Exception as e:
            logging.warning('Exception in %s', (self.func))
            template = "An exception of type {0} occured. Arguments:\n{1!r}"
            message = template.format(
                type(e).__name__, getattr(e, 'args', None))
            logging.exception(message)


def general_function_handler_wrapper(return_val=None):
    class wrapped_function_handler(object):
        def __init__(self, func, return_val=return_val):
            self.func = func
            self.return_val = return_val
        def __get__(self, obj, obj_type=None):
            return self.__class__(self.func.__get__(obj, obj_type))
        def __call__(self, *args, **kwargs):
            try:
                return_val = self.func(*args, **kwargs)
            except Exception as e:
                logging.warning('Exception in %s', (self.func))
                template = "An exception of type {0} occured. Arguments:\n{1!r}"
                message = template.format(
                    type(e).__name__, getattr(e, 'args', None))
                logging.exception(message)
                try:
                    return_val = self.return_val(e)
                except:  # pylint: disable=bare-except
                    return_val = self.return_val
            finally:
                return return_val  # pylint: disable=lost-exception
    def func_wrapper(func):
        @wrapped_function_handler
        def wrapped_func(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped_func
    return func_wrapper


# === Helper for Non-default Field retrieval ======= #

def test_subclass(thing, class_args):
    """Test function that attempts to validate `thing` is a subclass of
    `class_args`, but will return False if `thing` is not a class definition
    rather than raising a `TypeError` the way `issubclass()` will."""
    try:
        return issubclass(thing, class_args)
    except TypeError:
        return False


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except:  # pylint: disable=bare-except
        return False


def default_kwargs(**defaultKwargs):
    def actual_decorator(fn):
        @functools.wraps(fn)
        def g(*args, **kwargs):
            defaultKwargs.update(kwargs)
            return fn(*args, **defaultKwargs)
        return g
    return actual_decorator


def getor(gettable, key, default=None):
    """
    THIS IS A VERY DANGEROUS FUNCTION!!!
    """
    result = default
    try:
        if isinstance(gettable, (tuple, list)):
            for listobj in gettable:
                result = getor(listobj, key, default)
                if result != default:
                    break
        else:
            result = gettable.get(key, default)
    except Exception:
        try:
            result = getattr(gettable, key, default)
        except:  # pylint: disable=bare-except
            pass
    finally:
        # unless default is None and result is falsey but not None, return
        # (result or default), otherwise don't overwrite the falsey result
        if not all((not result, result is not None, default is None)):
            result = result or default
    return result


def hasattrs(obj, attr_list):
    return all([hasattr(obj, attr) for attr in attr_list])


def exists(it):
    return it is not None


def single_true(iterable):
    i = iter(iterable)
    return any(i) and not any(i)


def grouped(iterable, n):
    return zip(*[iter(iterable)]*n)


def recurse_getattr(obj, attr_list, default=None, call_result=True):
    result = default
    nested_obj = obj
    try:
        attr_list = coercelist(attr_list)
        for nested_attr in attr_list:
            if isinstance(nested_attr, (list, tuple)):
                nested_obj = multi_getattr(nested_obj, nested_attr)
            else:
                nested_obj = getor(nested_obj, nested_attr)
        result = nested_obj or default
    except AttributeError:
        if result is None:
            raise
    if callable(result) and call_result:
        result = result()
    return result


def classname(obj, with_module=True):
    for_dotting = [recurse_getattr(obj, ['__class__', '__name__'])]
    if with_module:
        try:
            for_dotting.append(
                recurse_getattr(obj, ['__class__', '__module__']))
            for_dotting.reverse()
        except Exception:
            pass
    return ".".join(for_dotting)


def multi_getattr(obj, attr_list, default=None, call_result=True):
    result = default
    processing_result = None
    attr_list = coercelist(attr_list)
    attr_list.reverse()
    while attr_list and not processing_result:
        try:
            thing = coercelist(attr_list.pop())
            processing_result = recurse_getattr(obj, thing)
        except AttributeError:
            continue
    result = processing_result or result
    if result is None:
        raise AttributeError()
    elif callable(result) and call_result:
        result = result()
    else:
        pass
    return result


@default_kwargs(idrill=True)
def getdrill(*args, **kwargs):
    idrill = kwargs.pop('idrill')
    func_getattr = recurse_getattr
    if not idrill:
        func_getattr = multi_getattr
    return func_getattr(*args, **kwargs)


def dotparse_drillarg(drillarg, sep="."):
    return list(drillarg.split(sep))


def simple_recurse_attr(result, attr_list, *args, **kwargs):
    attr_list.reverse()
    default_set = bool(args) or 'default' in kwargs
    default = (
        None if not default_set
        else kwargs['default'] if 'default' in kwargs
        else args[0])
    try:
        while attr_list:
            next_attr = attr_list.pop()  # last element of list, hence reverse
            if default_set:
                getargs = (result, next_attr, default)
            else:
                getargs = (result, next_attr)
            result = getattr(*getargs)
        return result
    except Exception as e:
        if default_set:
            try:
                return args[0]
            except IndexError:
                return kwargs['default']
        raise e


def dotparse_getattr(obj, dotparse_string, *args, **kwargs):
    """Return the value obtained from the recursively evaluated, dot-separated
    attribute chain `dotparse_string`, starting from `obj`

    Arguments:
        obj {any} -- Object from which the attribute evaluation starts
        dotparse_string {str} -- Dot-separated string of attributes
        *default {any} -- optional return value if exceptions arise

    Returns:
        various -- value that was obtained, or the default value
    """
    return simple_recurse_attr(
        obj, dotparse_drillarg(dotparse_string), *args, **kwargs)


def oname(obj, with_module=True):
    try:
        result = getdrill(
            obj, ['__qualname__', '__name__'],
            lambda: classname(obj, with_module=with_module),
            idrill=False)
    except Exception:
        result = "UnhandledException"
    return result


class kwargset:

    @classmethod
    def is_copy(cls, term, *args, **kwargs):  # pylint: disable=unused-argument
        return isinstance(term, cls)

    def __init__(self, **kwargs):
        base_attrs = []
        for key, value in kwargs.items():
            setattr(self, key, value)
            base_attrs.append(key)
        self.__base_attrs__ = base_attrs

    def _base_as_dict(self):
        return {
            key: getattr(self, key, None)
            for key in self.__base_attrs__}

    @property
    def mapping(self):
        return self._base_as_dict()

    def items(self):
        return self._base_as_dict().items()

    def iteritems(self):
        try:
            return self._base_as_dict().iteritems()
        except AttributeError:
            return self._base_as_dict().items()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __iter__(self):
        return self._base_as_dict().__iter__()

    def __repr__(self):
        return self._base_as_dict().__repr__()

    def __getitem__(self, key):
        """Enables retrieving attrs in a dict-y way (i.e. obj['key'])"""
        try:
            return getattr(self, key)
        except AttributeError:
            pass
        raise KeyError(key)


def resolve_complex_structure(its_complicated, into=None, **kwargs):
    try:
        key_terms = set([
            term_list[-1] for term_list, data in its_complicated])
    except IndexError:
        if len(its_complicated) != 1:
            raise
        term, data = its_complicated[0]
        if term:
            raise
        return data
    layer_dict = {}
    for key in key_terms:
        substructure = [
            (term_list[:-1], data)
            for term_list, data in its_complicated
            if term_list[-1] == key]
        layer_dict[key] = resolve_complex_structure(substructure)
    layer_dict.update(kwargs)
    if into is None:
        # Restricting this operation to this case ensures that if this
        # function is called with a different into-argument, the resulting
        # object will always have some value for the top-level attributes
        # specified at the end of each term list...
        empty_keys = set()
        for key, value in layer_dict.items():
            if value is None:
                empty_keys.add(key)
        for key in empty_keys:
            del layer_dict[key]
        if not layer_dict:
            return None
        into = kwargset
    return into(**layer_dict)


def wrapset(isiter, *args, **kwargs):  # pylint: disable=unused-argument
    try:
        if not isinstance(isiter, str):
            raise AssertionError
        result = set(isiter)
    except (TypeError, AssertionError):
        result = set([isiter])
    except Exception:
        result = set([])
    finally:
        return result  # pylint: disable=lost-exception


def hyphen_range_gen(s):
    """ yield each integer from a complex range string like "1-9,12, 15-20,23"

    >>> list(hyphen_range('1-9,12, 15-20,23'))
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 16, 17, 18, 19, 20, 23]

    >>> list(hyphen_range('1-9,12, 15-20,2-3-4'))
    Traceback (most recent call last):
        ...
    ValueError: format error in 2-3-4
    """
    for x in s.split(','):
        elem = x.split('-')
        if len(elem) == 1:  # a number
            yield int(elem[0])
        elif len(elem) == 2:  # a range inclusive
            start, end = map(int, elem)
            for i in range(start, end + 1):
                yield i
        else:  # more than one hyphen
            raise ValueError('format error in %s' % x)


def hyphen_range(s):
    return list(hyphen_range_gen(s))


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def first_and_last(iterable):
    start = end = next(iterable)
    for end in iterable:
        pass
    return start, end


def notlambda(v):
    return v


def do_nothing(*args, **kwargs):  # pylint: disable=unused-argument
    pass


def predicate(lhs, rhs, cutoff):
    return lhs - cutoff <= rhs <= lhs + cutoff


def adjacent_key(cutoff=1, key=notlambda, this_predicate=predicate):

    class K(object):
        __slots__ = ['obj']

        def __init__(self, obj):
            self.obj = obj

        def __eq__(self, other):
            ret = this_predicate(key(self.obj), key(other.obj), cutoff)
            if ret:
                self.obj = other.obj
            return ret

    return K


def runs(iterable, *args, **kwargs):
    # pylint: disable=unused-variable
    for k, g in itertools.groupby(iterable, adjacent_key(*args, **kwargs)):
        yield first_and_last(g)


def coercelist(subject, iter_dict='keys', wrap_strings=True):
    if isinstance(subject, str):
        if wrap_strings and isinstance(wrap_strings, str):
            result = subject.split(wrap_strings)
        elif wrap_strings:
            result = [subject]
        else:
            result = list(subject)
    elif not hasattr(subject, '__iter__'):
        result = [subject]
    elif isinstance(subject, dict):
        result = getattr(subject, iter_dict, 'keys')()
    else:
        result = list(subject)
    return result


def coercedict(to_dict, default=None, domap=True):
    if not isinstance(to_dict, (list, tuple, dict, frozendict)):
        results = {to_dict: default}
    elif (isinstance(to_dict, (tuple, list)) and
          isinstance(default, (tuple, list)) and
          len(to_dict) == len(default) and domap is True):
        results = {
            td: default[i]
            for i, td in enumerate(to_dict) if td}
    elif (isinstance(to_dict, (tuple, list)) and
          isinstance(default, dict) and
          ((set(to_dict) - set([None])) & set(default.keys())) and
          domap is True):
        results = {
            td: default.get(td, None)
            for td in to_dict if td}
    elif isinstance(to_dict, (tuple, list)):
        results = {
            td: default
            for td in to_dict if td}
    else:  # dict
        results = dict(to_dict)
    return results


def oara_argkwarg(opt_args, *args, **kwargs):
    req_args = kwargs.get('req_args', None)
    if req_args:
        required = coercelist(req_args)
    else:
        required = []
    if 'req_args' in kwargs:
        del kwargs['req_args']
    if opt_args:
        opt_defaults = kwargs.get('opt_defaults', None)
        optional = coercelist(opt_args)
        oargs = coercedict(opt_args, opt_defaults)
    else:
        optional = []
        oargs = {}
    if 'opt_defaults' in kwargs:
        del kwargs['opt_defaults']
    ordered_arguments = list(required)
    ordered_arguments.extend(optional)
    fargs = {oarg: None for oarg in ordered_arguments}
    fargs.update(oargs)  # establishes default argument values
    oarg_is_kwarg = [oarg for oarg in ordered_arguments if oarg in kwargs]
    for oarg in oarg_is_kwarg:
        del ordered_arguments[ordered_arguments.index(oarg)]
    for i, j in enumerate(args):
        if i < len(ordered_arguments):
            fargs[ordered_arguments[i]] = j
    for key, val in fargs.items():
        try:
            if key in kwargs:
                fargs[key] = val(kwargs[key])
                del kwargs[key]
            else:
                fargs[key] = val()
        except Exception:
            pass
    fargs.update(kwargs)
    margs = [f for f, val in fargs.items()
             if val is None and f in required and f not in kwargs]
    if margs:
        cframe = inspect.currentframe()
        calledby = inspect.getframeinfo(cframe.f_back).function
        raise TypeError("{} expected {} arguments, got {}".format(
            calledby, len(required), len(required) - len(margs)))
    return fargs


@general_function_handler_wrapper(return_val=force_text)
def test_callable(CallableObj, value, explode=False):
    if explode:
        # The test should not return True for empty explodable values if the
        # CallableObj provided is not configured to handle being called without
        # arguments.  Similarly, the test should not return True for values
        # that are not explodable.
        try:
            return bool(CallableObj(**value))
        except TypeError:
            try:
                return bool(CallableObj(*value))
            except TypeError:
                pass
        if not value:
            return "Unable to explode empty value."
        return "Unable to explode value: {}".format(value)
    result = CallableObj(value)  # pylint: disable=unused-variable
    return True


def is_uuid(farg, **kwargs):  # pylint: disable=unused-argument
    test_result = test_callable(UUID_RE.match, farg)
    return (
        test_result is True and bool(UUID_RE.match(farg)) or test_result)


def slugify(text, trim_trailing=False):
    '''
    convert unicode text ("XQUR%%&_egU uětn991")
    to a slug ("xqur-_egu-uetn991")
    '''
    if not isinstance(text, str):
        text = str(text)
    text = unidecode.unidecode(text).lower()
    result = re.sub(r'\W+', '-', text)
    if trim_trailing:
        result = re.sub(r"-$", "", result)
    return result


def slugify_csv(csv_text, trim_trailing=False):
    '''
    convert comma-sep unicode text ("XQUR%%&_egU, uětn991")
    to comma-sep slug ("xqur-_egu,uetn991")
    '''
    if not isinstance(csv_text, str):
        csv_text = str(csv_text)
    csv_text = unidecode.unidecode(csv_text).lower()
    csv_text = re.sub(r"\s*,\s*", ",", csv_text)
    result = re.sub(r"[^\w,]+", "-", csv_text)
    if trim_trailing:
        result = re.sub(r"-$", "", result)
    return result


def iter_slugify(text_iter, trim_trailing=False):
    for make_slug in text_iter:
        try:
            text_iter[make_slug] = slugify(text_iter[make_slug])
        except Exception:
            make_slug = slugify(make_slug, trim_trailing)
    return text_iter


def iter_slugify_csv(csv_iter, trim_trailing=False):
    new_list = []
    for make_slug in csv_iter:
        try:
            csv_iter[make_slug] = slugify_csv(csv_iter[make_slug])
        except Exception:
            new_list.append(slugify_csv(make_slug, trim_trailing))
    if new_list:
        csv_iter = new_list
    return csv_iter


def regexp_list(list_of_patterns):
    return [re.compile(pattern) for pattern in list_of_patterns]
