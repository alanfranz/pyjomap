#!/usr/bin/env python
# -*- coding: utf-8 -*-

from inspect import getargspec, getmembers
from copy import deepcopy
import codecs
from collections import Mapping


# mapper will be invoked with the a value of type "origin" and the reference object,
#  and must always return a value of type "destination" (or a compatible/child type? what about long/int)?
# TypeMapping = namedtuple("TypeMapping", ["origin", "destination", "mapper"])

# later, we could generalize via sponsor-selector, where type-based mappings are just one of the possible
# mapping criterias? is there a way we can handle the fact that there could be multiple mappers
# interested?

# TODO: verify that, when collections are used as reference, if more than one item is provided, all must have the same type



class ObjectMapping(object):
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


class TypeMapping(ObjectMapping):
    def __init__(self, origin_type, destination_type, mapper_func, subclass_cast=False):
        self._origin_type = origin_type
        self._destination_type = destination_type
        self._mapper_func = mapper_func
        self._subclass_cast = subclass_cast

    def interest_level(self, source, reference):
        if type(source) == self._origin_type and type(reference) == self._destination_type:
            return 100
        if self._subclass_cast and type(source) == self._origin_type and isinstance(reference, self._destination_type):
            return 50
        return 0

    def map(self, source, reference):
        cast_to_type = type(reference)
        return cast_to_type(self._mapper_func(source, reference))


class ListToTupleMapping(ObjectMapping):
    def __init__(self, mapobj):
        self.mapobj = mapobj

    def interest_level(self, source, reference):
        if type(source) == list and type(reference) == tuple and len(source) == len(reference):
            return 100
        return 0

    def map(self, source, reference):
        return tuple([self.mapobj(x, reference[0]) for x in source])


class MappingToObjectMapping(ObjectMapping):
    def __init__(self, mapobj):
        self.mapobj = mapobj

    def interest_level(self, source, reference):
        # for the reference object, we don't map classic instances, but everything else would be ok.
        if isinstance(source, Mapping) and isinstance(reference, object):
            # we're never the top match. always let better mappers to take precedence over us.
            return 50
        return 0

    def map(self, source, reference):
        """
        :param source:
        :param reference:
        :return:
        :rtype: same class as reference object
        """
        out_properties = {}

        for key, value in source.items():
            try:
                out_properties[key] = self.mapobj(value, getattr(reference, key))
            except TypeError:
                print type(key)
                raise

        return bind(out_properties, type(reference))


class DefaultMapperRegistry(object):
    def __init__(self, conversion_encoding):
        # just check if the codec is valid
        codecs.lookup(conversion_encoding)

        # TODO: we should create a "sametypemapper" which just:
        # a) keeps the object for immutable objects
        # b) copies the object for mutable/unknown types
        # TODO: map tuples to lists and vice-versa
        # TODO: check for other/unknown types which approach could work
        self.type_based_mappings = [
            TypeMapping(int, int, lambda v, r: v, True),
            TypeMapping(int, long, lambda v, r: long(v)),
            TypeMapping(long, int, lambda v, r: int(v)),
            TypeMapping(tuple, tuple, lambda v, r: deepcopy(v)),
            TypeMapping(tuple, list, lambda v, r: [self.mapobj(x, r[0]) for x in v]),
            ListToTupleMapping(self.mapobj),
            TypeMapping(int, str, lambda v, r: "{:d}".format(v)),
            TypeMapping(str, int, lambda v, r: int(v)),
            TypeMapping(long, str, lambda v, r: "{:d}".format(v)),
            TypeMapping(str, str, lambda v, r: v),
            TypeMapping(unicode, str, lambda v, r: v.encode(conversion_encoding)),
            TypeMapping(str, unicode, lambda v, r: v.decode(conversion_encoding)),
            TypeMapping(unicode, unicode, lambda v, r: v),
            TypeMapping(list, list, lambda v, r: [self.mapobj(x, r[0]) for x in v]),
            TypeMapping(dict, dict, lambda v, r: dict(
                [(self.mapobj(x, r.keys()[0]), self.mapobj(y, r.values()[0])) for x, y in v.iteritems()])),
            MappingToObjectMapping(self.mapobj)
        ]

    def get_best_mapping(self, source, reference):
        mapping_and_levels = ((mapping, mapping.interest_level(source, reference)) for mapping in
                              self.type_based_mappings)
        mapping_and_levels = [(mapping, level) for mapping, level in mapping_and_levels if level > 0]
        if not mapping_and_levels:
            source_type = type(source)
            ref_type = type(reference)
            raise ValueError(
                "Could not map value '{source}' ({source_type}) through reference object '{reference}' ({ref_type})".format(
                    **locals()))
        mapping_and_levels.sort(key=lambda x: x[1])
        return mapping_and_levels[-1][0]

    def mapobj(self, source, dest):
        """
        Args:
            source:
            dest:

        Returns:
        """
        mapping = self.get_best_mapping(source, dest)
        return mapping.map(source, dest)


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
    constructor_args = dict((k, v) for (k, v) in d.items() if k in args)
    instance = klass(**constructor_args)

    all_fields = getfields(instance)
    set_args = dict((k, v) for (k, v) in d.items() if k not in args)
    missing_properties = set(all_fields).difference(set_args.keys()).difference(constructor_args.keys())
    if missing_properties:
        raise BindException, "There're {0} properties that cannot be set: {1}".format(len(missing_properties),
                                                                                      " ".join(missing_properties))

    for k, v in set_args.iteritems():
        setattr(instance, k, v)
    return instance


def getfields(o):
    return set([name for name, value in getmembers(o) if not name.startswith("_") and not callable(value)])


def getfieldsandvalues(o):
    return set([(name, value) for name, value in getmembers(o) if not name.startswith("_") and not callable(value)])










