#!/usr/bin/env python
from inspect import getargspec, getmembers
from unittest import TestCase, main
import logging

from collections import MutableSequence, Mapping, Container, OrderedDict, namedtuple


# mapper will be invoked with the a value of type "origin" and the reference object,
#  and must always return a value of type "destination" (or a compatible/child type? what about long/int)?
#TypeMapping = namedtuple("TypeMapping", ["origin", "destination", "mapper"])

# later, we could generalize via sponsor-selector, where type-based mappings are just one of the possible
# mapping criterias? is there a way we can handle the fact that there could be multiple mappers
# interested?
class Mapping(object):
    def interest_level(self, source, reference):
        """
        Args:
            source: source object
            reference: reference object

        Returns (int): interest level. 0 means not interested; if > 0, the most interested should win.
        """
        raise NotImplementedError("must be implemented")

    def map(self, source, reference):
        """

        Args:
            source: source object
            reference: reference object

        Returns: an item of the same (or compatible) type as the reference object, result of the mapping.
        """
        raise NotImplementedError("must be implemented")


class TypeMapping(Mapping):
    def __init__(self, origin_type, destination_type, mapper_func):
        self._origin_type = origin_type
        self._destination_type = destination_type
        self._mapper_func = mapper_func

    def interest_level(self, source, reference):
        if type(source) == self._origin_type and type(reference) == self._destination_type:
            return 100
        # TODO: verify if we can really to that for arbitrary classes, or we might have issues.
        elif type(source) == self._origin_type and issubclass(type(reference), self._destination_type):
            return 50
        return 0

    def map(self, source, reference):
        return self._mapper_func(source, reference)

class MapperRegistry(object):
    type_based_mappings = [
        TypeMapping(int, int, lambda v, r: v),
        TypeMapping(int, long, lambda v, r: long(v)),
        TypeMapping(long, int, lambda v, r: int(v)),
        TypeMapping(int, str, lambda v, r: "{:d}".format(v)),
        TypeMapping(str, int, lambda v, r: int(v)),
        TypeMapping(long, str, lambda v, r: "{:d}".format(v)),
        TypeMapping(str, str, lambda v, r: v),
        TypeMapping(list, list, lambda v, r: [mapobj(x, r[0]) for x in v]),
        TypeMapping(dict, dict, lambda v, r: dict([(mapobj(x, r.keys()[0]), mapobj(y, r.values()[0])) for x, y in v.iteritems()])),
        TypeMapping(dict, object, lambda v, r: mapdict(v, r))
    ]

    def get_best_mapping(self, source, reference):
        mapping_and_levels = ((mapping, mapping.interest_level(source, reference)) for mapping in self.type_based_mappings)
        mapping_and_levels = [(mapping, level) for mapping, level in mapping_and_levels if level > 0]
        if not mapping_and_levels:
            raise ValueError("Could not map value '{source}' through reference object '{reference}'".format(**locals()))
        mapping_and_levels.sort(key=lambda x: x[1])
        return mapping_and_levels[-1][0]

# supported in source -> dest
# maybe we should do a "maptype" by default? it's useful for immutability as well,
# and we can use a "predefined" order, then resorting to abc afterwards.

# iterable -> list, set
# iterator -> list, set
# sequence -> list     -> EXCLUDING STRING

# must check for container types and recurse on them.
# currently: we assume that the source and dest type must be equal,
# and that they accept the "right" kind of arguments when constructing.
# this is recursive. might have some issues if the mapped object is large.

logger = logging.getLogger("mapobj")
def mapobj(source, dest, mapper_registry=MapperRegistry()):
    """
    Args:
        source:
        dest:

    Returns:
    """
    mapping = mapper_registry.get_best_mapping(source, dest)
    return mapping.map(source, dest)

class BindException(Exception):
    pass

def bind(d, klass):
    """
    try binding names from d to klass constructor, set the others.
    won't work with varargs/kwargs/strange things

    don't use __new__

    can use read-only properties if values set in constructor. but
    at least a readonly property MUST be set (can't leave value out if it's in the constructor)

    currently, EVERYTHING must be set for bind to succeed, even things that are not in the constructor (could change this
    later)


    :rtype : klass
    """
    assert "self" not in d, "can't contain self keyword, it's reserved and can create issues with binding"
    args, varargs, keywords, defaults = getargspec(klass.__init__)
    constructor_args = dict( (k,v) for (k,v) in d.items() if k in args)
    instance = klass(**constructor_args)

    all_fields = getfields(instance)
    set_args = dict( (k,v) for (k,v) in d.items() if k not in args)
    missing_properties = set(all_fields).difference(set_args.keys()).difference(constructor_args.keys())
    if missing_properties:
        raise BindException, "There're {0} properties that cannot be set: {1}".format(len(missing_properties), " ".join(missing_properties))

    for k,v in set_args.iteritems():
        setattr(instance, k, v)
    return instance

def getfields(o):
    return set([name for name, value in getmembers(o) if not name.startswith("_") and not callable(value)])

def getfieldsandvalues(o):
    return set([(name, value) for name, value in getmembers(o) if not name.startswith("_") and not callable(value)])


def mapdict(d, reference):
    """
    :param d:
    :param reference:
    :return:
    :rtype: same class as reference object
    """
    out_properties = {}

    for key, value in d.items():
        out_properties[key] = mapobj(value, getattr(reference, key))

    return bind(out_properties, type(reference))

class MyItem(object):

    def __init__(self, a, b, c=None, d=None, e=None):
        self.a = a
        self._b = b
        self._private = 1
        self.c = c
        self.d = d
        self.e = e

    @property
    def b(self):
        return self._b

    @b.setter
    def b(self, value):
        self._b = value

    def __eq__(self, other):
        return getattr(other, "__dict__", None) is not None and self.__dict__ == other.__dict__

    def __str__(self):
        return "a:{0}   b:{1}   c:{2}  d:{3}".format(self.a, self._b, self.c, self.d)

    def __repr__(self):
        return str(self)

class Other(object):
    def __init__(self, r, s):
        self.r = r
        self.s = s

    def __eq__(self, other):
        return getattr(other, "__dict__", None) is not None and self.__dict__ == other.__dict__

class TestFieldInspection(TestCase):
    def test_fields(self):
        i = MyItem(1, "asd")
        self.assertEquals(set(["a", "b", "c", "d", "e"]), getfields(i))

    def test_bind(self):
        item = bind({"a":7, "b":"asd", "c":[3,4], "d": {}, "e": []}, MyItem)
        expected = MyItem(7, "asd", [3, 4], {}, [])
        self.assertEqual(expected, item)

    def test_bind_fails_if_not_enough_data(self):
        self.assertRaises(BindException, bind, {"a":7, "b":"asd"},  MyItem)


class TestMappingFromDict(TestCase):
    DICT_IN = {
        "a": 5,
        "b": "what",
        "c": [{1: 2}],
        "d": {"1": 1, "2": 2},
        "e": {"r": 5, "s": 6}
    }

    def test_mapping(self):
        reference = MyItem(7, "asd", [{2: 3}], {10: "w", 20: "xxx"}, e=Other(9, 10))
        instance = mapobj(self.DICT_IN, reference)
        expected = MyItem(5, "what", [{1: 2}], {1: "1", 2: "2"}, e=Other(5, 6))
        self.assertEquals(expected, instance)

    def test_string_casting(self):
        reference = MyItem("7", "asd", [{"2": "3"}], {10: "w", 20: "xxx"}, e=Other("a", "b"))
        instance = mapobj(self.DICT_IN, reference)
        expected = MyItem("5", "what", [{"1": "2"}], {1: "1", 2: "2"}, e=Other("5", "6"))
        self.assertEquals(expected, instance)









if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    main()


