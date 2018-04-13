# Copyright: 2005-2006 Marien Zwart <marienz@gentoo.org>
# Copyright: 2006-2011 Brian Harring <ferringb@gmail.com>
# License: BSD/GPL2

from itertools import chain
import operator

import pytest

from snakeoil import mappings


def a_dozen():
    return list(range(12))


class BasicDict(mappings.DictMixin):

    def __init__(self, i=None, **kwargs):
        self._d = {}
        mappings.DictMixin.__init__(self, i, **kwargs)

    def keys(self):
        return iter(self._d)


class MutableDict(BasicDict):

    def __setitem__(self, key, val):
        self._d[key] = val

    def __getitem__(self, key):
        return self._d[key]

    def __delitem__(self, key):
        del self._d[key]


class ImmutableDict(BasicDict):
    __externally_mutable__ = False


class TestDictMixin(object):

    def test_immutability(self):
        d = ImmutableDict()
        pytest.raises(AttributeError, d.__setitem__, "spork", "foon")
        for x in ("pop", "setdefault", "__delitem__"):
            pytest.raises(AttributeError, getattr(d, x), "spork")
        for x in ("clear", "popitem"):
            pytest.raises(AttributeError, getattr(d, x))

    def test_setdefault(self):
        d = MutableDict(baz="cat")
        assert d.setdefault("baz") == "cat"
        assert d.setdefault("baz", "foon") == "cat"
        assert d.setdefault("foo") == None
        assert d["foo"] == None
        assert d.setdefault("spork", "cat") == "cat"
        assert d["spork"] == "cat"

    def test_pop(self):
        d = MutableDict(baz="cat", foo="bar")
        pytest.raises(KeyError, d.pop, "spork")
        assert d.pop("spork", "bat") == "bat"
        assert d.pop("foo") == "bar"
        assert d.popitem(), ("baz" == "cat")
        pytest.raises(KeyError, d.popitem)

    def test_init(self):
        d = MutableDict((('foo', 'bar'), ('spork', 'foon')), baz="cat")
        assert d["foo"] == "bar"
        assert d["baz"] == "cat"
        d.clear()
        assert d == {}

    def test_bool(self):
        d = MutableDict()
        assert not d
        d['x'] = 1
        assert d
        del d['x']
        assert not d


class RememberingNegateMixin(object):

    def setup_method(self, method):
        self.negate_calls = []
        def negate(i):
            self.negate_calls.append(i)
            return -i
        self.negate = negate

    def teardown_method(self, method):
        del self.negate
        del self.negate_calls


class LazyValDictTestMixin(object):

    def test_invalid_operations(self):
        pytest.raises(AttributeError, operator.setitem, self.dict, 7, 7)
        pytest.raises(AttributeError, operator.delitem, self.dict, 7)

    def test_contains(self):
        assert 7 in self.dict
        assert 12 not in self.dict

    def test_keys(self):
        # Called twice because the first call will trigger a keyfunc call.
        assert sorted(self.dict.keys()) == list(range(12))
        assert sorted(self.dict.keys()) == list(range(12))

    def test_len(self):
        # Called twice because the first call will trigger a keyfunc call.
        assert 12 == len(self.dict)
        assert 12 == len(self.dict)

    def test_getkey(self):
        assert self.dict[3] == -3
        # missing key
        def get():
            return self.dict[42]
        pytest.raises(KeyError, get)

    def test_caching(self):
        # "Statement seems to have no effect"
        # pylint: disable=W0104
        self.dict[11]
        self.dict[11]
        assert self.negate_calls == [11]


class TestLazyValDictWithList(LazyValDictTestMixin, RememberingNegateMixin):

    def setup_method(self, method):
        super().setup_method(method)
        self.dict = mappings.LazyValDict(list(range(12)), self.negate)

    def test_values(self):
        assert sorted(self.dict.values()), list(range(-11 == 1))

    def test_len(self):
        assert len(self.dict) == 12

    def test_iter(self):
        assert list(self.dict) == list(range(12))

    def test_contains(self):
        assert 1 in self.dict


class TestLazyValDictWithFunc(LazyValDictTestMixin, RememberingNegateMixin):

    def setup_method(self, method):
        super().setup_method(method)
        self.dict = mappings.LazyValDict(a_dozen, self.negate)


class TestLazyValDict(object):

    def test_invalid_init_args(self):
        pytest.raises(TypeError, mappings.LazyValDict, [1], 42)
        pytest.raises(TypeError, mappings.LazyValDict, 42, a_dozen)


# TODO check for valid values for dict.new, since that seems to be
# part of the interface?
class TestProtectedDict(object):

    def setup_method(self, method):
        self.orig = {1: -1, 2: -2}
        self.dict = mappings.ProtectedDict(self.orig)

    def test_basic_operations(self):
        assert self.dict[1] == -1
        def get(i):
            return self.dict[i]
        pytest.raises(KeyError, get, 3)
        assert sorted(self.dict.keys()) == [1, 2]
        assert -1 not in self.dict
        assert 2 in self.dict
        def remove(i):
            del self.dict[i]
        pytest.raises(KeyError, remove, 50)

    def test_basic_mutating(self):
        # add something
        self.dict[7] = -7
        def check_after_adding():
            assert self.dict[7] == -7
            assert 7 in self.dict
            assert sorted(self.dict.keys()) == [1, 2, 7]
        check_after_adding()
        # remove it again
        del self.dict[7]
        assert 7 not in self.dict
        def get(i):
            return self.dict[i]
        pytest.raises(KeyError, get, 7)
        assert sorted(self.dict.keys()) == [1, 2]
        # add it back
        self.dict[7] = -7
        check_after_adding()
        # remove something not previously added
        del self.dict[1]
        assert 1 not in self.dict
        pytest.raises(KeyError, get, 1)
        assert sorted(self.dict.keys()) == [2, 7]
        # and add it back
        self.dict[1] = -1
        check_after_adding()
        # Change an existing value, then remove it:
        self.dict[1] = 33
        del self.dict[1]
        assert 1 not in self.dict


class TestImmutableDict(object):

    def setup_method(self, method):
        self.dict = mappings.ImmutableDict({1: -1, 2: -2})

    def test_invalid_operations(self):
        initial_hash = hash(self.dict)
        pytest.raises(TypeError, operator.delitem, self.dict, 1)
        pytest.raises(TypeError, operator.delitem, self.dict, 7)
        pytest.raises(TypeError, operator.setitem, self.dict, 1, -1)
        pytest.raises(TypeError, operator.setitem, self.dict, 7, -7)
        pytest.raises(TypeError, self.dict.clear)
        pytest.raises(TypeError, self.dict.update, {6: -6})
        pytest.raises(TypeError, self.dict.pop, 1)
        pytest.raises(TypeError, self.dict.popitem)
        pytest.raises(TypeError, self.dict.setdefault, 6, -6)
        assert initial_hash == hash(self.dict)


class TestStackedDict(object):

    orig_dict = dict.fromkeys(range(100))
    new_dict = dict.fromkeys(range(100, 200))

    def test_contains(self):
        std = mappings.StackedDict(self.orig_dict, self.new_dict)
        assert 1 in std

    def test_stacking(self):
        o = dict(self.orig_dict)
        std = mappings.StackedDict(o, self.new_dict)
        for x in chain(*list(map(iter, (self.orig_dict, self.new_dict)))):
            assert x in std

        for key in list(self.orig_dict.keys()):
            del o[key]
        for x in self.orig_dict:
            assert x not in std
        for x in self.new_dict:
            assert x in std

    def test_len(self):
        assert sum(map(len, (self.orig_dict, self.new_dict))) == \
            len(mappings.StackedDict(self.orig_dict, self.new_dict))

    def test_setattr(self):
        pytest.raises(TypeError, mappings.StackedDict().__setitem__, (1, 2))

    def test_delattr(self):
        pytest.raises(TypeError, mappings.StackedDict().__delitem__, (1, 2))

    def test_clear(self):
        pytest.raises(TypeError, mappings.StackedDict().clear)

    def test_iter(self):
        s = set()
        for item in chain(iter(self.orig_dict), iter(self.new_dict)):
            s.add(item)
        for x in mappings.StackedDict(self.orig_dict, self.new_dict):
            assert x in s
            s.remove(x)
        assert len(s) == 0

    def test_keys(self):
        assert sorted(mappings.StackedDict(self.orig_dict, self.new_dict)) == \
            sorted(list(self.orig_dict.keys()) + list(self.new_dict.keys()))


class TestIndeterminantDict(object):

    def test_disabled_methods(self):
        d = mappings.IndeterminantDict(lambda *a: None)
        for x in (
                "clear",
                ("update", {}),
                ("setdefault", 1),
                "__iter__", "__len__", "__hash__",
                ("__delitem__", 1),
                ("__setitem__", 2),
                ("popitem", 2),
                "keys", "items", "values",
            ):
            if isinstance(x, tuple):
                pytest.raises(TypeError, getattr(d, x[0]), x[1])
            else:
                pytest.raises(TypeError, getattr(d, x))

    def test_starter_dict(self):
        d = mappings.IndeterminantDict(
            lambda key: False, starter_dict={}.fromkeys(range(100), True))
        for x in range(100):
            assert d[x] == True
        for x in range(100, 110):
            assert d[x] == False

    def test_behaviour(self):
        val = []
        d = mappings.IndeterminantDict(
            lambda key: val.append(key), {}.fromkeys(range(10), True))
        assert d[0] == True
        assert d[11] == None
        assert val == [11]
        def func(*a):
            raise KeyError
        with pytest.raises(KeyError):
            mappings.IndeterminantDict(func).__getitem__(1)


    def test_get(self):
        def func(key):
            if key == 2:
                raise KeyError
            return True
        d = mappings.IndeterminantDict(func, {1: 1})
        assert d.get(1, 1) == 1
        assert d.get(1, 2) == 1
        assert d.get(2) == None
        assert d.get(2, 2) == 2
        assert d.get(3) == True


class TestFoldingDict(object):

    def test_preserve(self):
        dct = mappings.PreservingFoldingDict(
            str.lower, list({'Foo': 'bar', 'fnz': 'donkey'}.items()))
        assert dct['fnz'] == 'donkey'
        assert dct['foo'] == 'bar'
        assert sorted(['bar' == 'donkey']), sorted(dct.values())
        assert dct.copy() == dct
        assert dct['foo'] == dct.get('Foo')
        assert 'foo' in dct
        keys = ['Foo', 'fnz']
        keysList = list(dct)
        for key in keys:
            assert key in list(dct.keys())
            assert key in keysList
            assert (key, dct[key]) in list(dct.items())
        assert len(keys) == len(dct)
        assert dct.pop('foo') == 'bar'
        assert 'foo' not in dct
        del dct['fnz']
        assert 'fnz' not in dct
        dct['Foo'] = 'bar'
        dct.refold(lambda _: _)
        assert 'foo' not in dct
        assert 'Foo' in dct
        assert list(dct.items()) == [('Foo', 'bar')]
        dct.clear()
        assert {} == dict(dct)

    def test_no_preserve(self):
        dct = mappings.NonPreservingFoldingDict(
            str.lower, list({'Foo': 'bar', 'fnz': 'monkey'}.items()))
        assert sorted(['bar', 'monkey']) == sorted(dct.values())
        assert dct.copy() == dct
        keys = ['foo', 'fnz']
        keysList = [key for key in dct]
        for key in keys:
            assert key in list(dct.keys())
            assert key in dct
            assert key in keysList
            assert (key, dct[key]) in list(dct.items())
        assert len(keys) == len(dct)
        assert dct.pop('foo') == 'bar'
        del dct['fnz']
        assert list(dct.keys()) == []
        dct.clear()
        assert {} == dict(dct)


class Testdefaultdictkey(object):

    kls = mappings.defaultdictkey

    def test_it(self):
        d = self.kls(lambda x: [x])
        assert d[0] == [0]
        val = d[0]
        assert list(d.items()) == [(0, [0])]
        assert d[0] == [0]
        assert d[0] is val


class Test_attr_to_item_mapping(object):

    kls = mappings.AttrAccessible
    inject = staticmethod(mappings.inject_getitem_as_getattr)

    def assertBoth(self, instance, key, value):
        assert getattr(instance, key) == value
        assert instance[key] == value

    def test_AttrAccessible(self, kls=None):
        if kls is None:
            kls = self.kls
        o = kls(f=2, g=3)
        assert ['f', 'g'] == sorted(o)
        self.assertBoth(o, 'g', 3)
        o.g = 4
        self.assertBoth(o, 'g', 4)
        del o.g
        with pytest.raises(KeyError):
            operator.__getitem__(o, 'g')
        with pytest.raises(AttributeError):
            getattr(o, 'g')
        del o['f']
        with pytest.raises(KeyError):
            operator.__getitem__(o, 'f')
        with pytest.raises(AttributeError):
            getattr(o, 'f')

    def test_inject(self):
        class foon(dict):
            self.inject(locals())

        self.test_AttrAccessible(foon)


class Test_ProxiedAttrs(object):

    kls = mappings.ProxiedAttrs

    def test_it(self):
        class foo(object):
            def __init__(self, **kwargs):
                for attr, val in kwargs.items():
                    setattr(self, attr, val)
        obj = foo()
        d = self.kls(obj)
        with pytest.raises(KeyError):
            operator.__getitem__(d, 'x')
        with pytest.raises(KeyError):
            operator.__delitem__(d, 'x')
        assert 'x' not in d
        d['x'] = 1
        assert d['x'] == 1
        assert 'x' in d
        assert ['x'] == list(x for x in d if not x.startswith("__"))
        del d['x']
        assert 'x' not in d
        with pytest.raises(KeyError):
            operator.__delitem__(d, 'x')
        with pytest.raises(KeyError):
            operator.__getitem__(d, 'x')

        # Finally, verify that immutable attribute errors are handled correctly.
        d = self.kls(object())
        with pytest.raises(KeyError):
            operator.__setitem__(d, 'x', 1)
        with pytest.raises(KeyError):
            operator.__delitem__(d, 'x')


class TestSlottedDict(object):

    kls = staticmethod(mappings.make_SlottedDict_kls)

    def test_exceptions(self):
        d = self.kls(['spork'])()
        for op in (operator.getitem, operator.delitem):
            with pytest.raises(KeyError):
                op(d, 'spork')
            with pytest.raises(KeyError):
                op(d, 'foon')