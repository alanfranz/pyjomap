#!/usr/bin/env python
from inspect import getargspec, getmembers
from unittest import TestCase, main

from collections import MutableSequence, Mapping, Container


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


# supported in source -> dest
# maybe we should do a "maptype" by default? it's useful for immutability as well, 
# and we can use a "predefined" order, then resorting to abc afterwards.

# iterable -> list, set
# iterator -> list, set
# sequence -> list     -> EXCLUDING STRING

# must check for container types and recurse on them.
# currently: we assume that the source and dest type must be equal,
# and that they accept the "right" kind of arguments when constructing.
def mapobj(source, dest):
    source_type = type(source)
    dest_type = type(dest)
    if source_type == dest_type:
        # this should be the "easy part"
        if isinstance(source, MutableSequence):
            # the dest_type must have at least one item, and the sequence
            # must be homogeneous, type-wise. check for those prereqs
            return dest_type([mapobj(x, dest[0]) for x in source])
        elif isinstance(source, Mapping):
            return dest_type([(mapobj(x, dest.keys()[0]), mapobj(y, dest.values()[0])) for x, y in source.iteritems()])
        else:
            # we should copy non-immutable types
            # we should fail when we don't know how to handle a mapping
            return source
    else:
        # arbitrary type-to-type mapping: invoke dest_type constructor. can be terribile for 
        # user-defined type; best thing thing would be to create a "safe" register for type-to-type
        # conversions (take a look at Dozer, or spring messageconverters, etc, for interface ideas)
        return dest_type(source)


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

    def __init__(self, a, b, c=None, d=None):
        self.a = a
        self._b = b
        self._private = 1
        self.c = c
        self.d = d

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


class TestFieldInspection(TestCase):
    def test_fields(self):
        i = MyItem(1, "asd")
        self.assertEquals(set(["a", "b", "c", "d"]), getfields(i))

    def test_bind(self):
        item = bind({"a":7, "b":"asd", "c":[3,4], "d": {}},  MyItem)
        expected = MyItem(7, "asd", [3, 4], {})
        self.assertEqual(expected, item)

    def test_bind_fails_if_not_enough_data(self):
        self.assertRaises(BindException, bind, {"a":7, "b":"asd"},  MyItem)


class TestMappingFromDict(TestCase):
    DICT_IN = {
        "a": 5,
        "b": "what",
        "c": [9, 10, 11],
        "d": {"1": 1, "2": 2}
    }

    def test_mapping(self):
        reference = MyItem(7, "asd", [1, 2, 3], {10: "w", 20: "xxx"})


        instance = mapdict(self.DICT_IN, reference)
        expected = MyItem(5, "what", [9,10,11], {1: "1", 2: "2"})
        self.assertEquals(expected, instance)

    def test_string_casting(self):
        reference = MyItem("7", "asd", ["a", "b"], {10: "w", 20: "xxx"})

        instance = mapdict(self.DICT_IN, reference)
        expected = MyItem("5", "what", ["9", "10", "11"], {1: "1", 2: "2"})
        self.assertEquals(expected, instance)









if __name__ == "__main__":
    main()


