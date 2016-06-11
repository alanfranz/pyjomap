# -*- coding: utf-8 -*-
from unittest import TestCase, main
from genty import genty, genty_dataset
from pyjomap.mymap import DefaultMapperRegistry, BindException, bind, getfields


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


class MyIntSubclass(int):
    pass


@genty
class TestMappingFromDict(TestCase):
    DICT_IN = {
        "a": 5,
        "b": "whatààà",
        "c": [{1: 2}, {1: 2}],
        "d": {"1": 1, "2": 2},
        "e": {"r": 5, "s": 6}
    }

    @genty_dataset(
        basic=(DICT_IN, MyItem(MyIntSubclass(7), "asd", ({2: 3}, {4: 5}), {10: "w", 20: "xxx"}, e=Other(9, 10)),
               MyItem(MyIntSubclass(5), "whatààà", ({1: 2}, {1: 2}), {1: "1", 2: "2"}, e=Other(5, 6))),
        string_casting=(DICT_IN, MyItem("7", u"asd", [{"2": "3"}], {10: "w", 20: "xxx"}, e=Other("a", "b")),
                        MyItem("5", u"whatààà", [{"1": "2"}, {"1": "2"}], {1: "1", 2: "2"}, e=Other("5", "6"))),
    )
    def test_mapping(self, source_value, reference, expected):
        registry = DefaultMapperRegistry(conversion_encoding="utf-8")
        instance = registry.mapobj(source_value, reference)
        self.assertEquals(expected, instance)


class TestFieldInspection(TestCase):
    def test_fields(self):
        i = MyItem(1, "asd")
        self.assertEquals(set(["a", "b", "c", "d", "e"]), getfields(i))

    def test_bind(self):
        item = bind({"a": 7, "b": "asd", "c": [3, 4], "d": {}, "e": []}, MyItem)
        expected = MyItem(7, "asd", [3, 4], {}, [])
        self.assertEqual(expected, item)

    def test_bind_fails_if_not_enough_data(self):
        self.assertRaises(BindException, bind, {"a": 7, "b": "asd"}, MyItem)


if __name__ == '__main__':
    main()
