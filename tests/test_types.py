#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
import enum

import pytest
from support import InstanceTestCase

from minizinc import Instance, default_driver
from minizinc.result import Status
from minizinc.types import AnonEnum, ConstrEnum


class TestEnum(InstanceTestCase):
    code = """
    enum DAY = {Mo, Tu, We, Th, Fr, Sa, Su};
    var DAY: d;
    """

    def test_value(self):
        self.instance.add_string("constraint d == Mo;")
        result = self.instance.solve()
        assert isinstance(result["d"], str)
        assert result["d"] == "Mo"

    def test_cmp_in_instance(self):
        self.instance.add_string("var DAY: d2;")
        self.instance.add_string("constraint d < d2;")
        result = self.instance.solve()
        assert isinstance(result["d"], str)
        assert isinstance(result["d2"], str)
        # TODO: assert result["d"] < result["d2"]

    def test_cmp_between_instances(self):
        append = "constraint d == Mo;"
        self.instance.add_string(append)
        result = self.instance.solve()

        inst = Instance(self.solver)
        inst.add_string(self.code + append)
        result2 = inst.solve()
        assert isinstance(result["d"], str)
        assert isinstance(result2["d"], str)
        assert result["d"] == result2["d"]

        inst = Instance(self.solver)
        inst.add_string(
            """
            enum DAY = {Mo, Tu, We, Th, Fr};
            var DAY: d;
            """
            + append
        )
        result2 = inst.solve()
        assert result["d"] == result2["d"]

    def test_assign(self):
        self.instance = Instance(self.solver)
        self.instance.add_string(
            """
            enum TT;
            var TT: t1;
            """
        )
        TT = enum.Enum("TT", ["one"])
        self.instance["TT"] = TT
        result = self.instance.solve()

        assert isinstance(result["t1"], TT)
        assert result["t1"] is TT.one

    def test_collections(self):
        self.instance = Instance(self.solver)
        self.instance.add_string(
            """
            enum TT;
            array[int] of var TT: arr_t;
            var set of TT: set_t;
            """
        )
        TT = enum.Enum("TT", ["one", "two", "three"])
        self.instance["TT"] = TT
        self.instance["arr_t"] = [TT(3), TT(2), TT(1)]
        self.instance["set_t"] = {TT(2), TT(1)}
        result = self.instance.solve()

        assert result["arr_t"] == [TT(3), TT(2), TT(1)]
        assert result["set_t"] == {TT(1), TT(2)}

    def test_intenum_collections(self):
        self.instance = Instance(self.solver)
        self.instance.add_string(
            """
            enum TT;
            % array[int] of var TT: arr_t;
            var set of TT: set_t;
            """
        )
        TT = enum.IntEnum("TT", ["one", "two", "three"])
        self.instance["TT"] = TT
        # TODO:  self.instance["arr_t"] = [TT(3), TT(2), TT(1)]
        self.instance["set_t"] = {TT(2), TT(1)}
        result = self.instance.solve()

        # TODO: assert result["arr_t"] == [TT(3), TT(2), TT(1)]
        assert result["set_t"] == {TT(1), TT(2)}

    def test_constructor_enum(self):
        self.instance = Instance(self.solver)
        self.instance.add_string(
            """
            enum T = X(1..3);
            var T: x;
            constraint x > X(1) /\\ x < X(3); % TODO: Remove for MiniZinc 2.7+
            """
        )
        # TODO: Remove for MiniZinc 2.7+
        # self.instance["x"] = ConstrEnum("X", 2)
        result = self.instance.solve()
        assert isinstance(result["x"], ConstrEnum)
        assert result["x"] == ConstrEnum("X", 2)
        assert str(result["x"]) == "X(2)"

    def test_anon_enum(self):
        self.instance = Instance(self.solver)
        self.instance.add_string(
            """
            enum T = _(1..5);
            var T: x;
            """
        )
        self.instance["x"] = AnonEnum("T", 3)
        result = self.instance.solve()
        assert isinstance(result["x"], AnonEnum)
        assert result["x"].value == 3
        assert str(result["x"]) == "to_enum(T,3)"

    def test_non_ascii(self):
        self.instance = Instance(self.solver)
        self.instance.add_string(
            """
            include "strictly_increasing.mzn";
            enum TT;
            array[1..3] of var TT: x;
            constraint strictly_increasing(x);
            """
        )
        TT = enum.Enum("TT", ["this one", "🍻", "∑"])
        self.instance["TT"] = TT
        result = self.instance.solve()
        assert result["x"] == [TT(1), TT(2), TT(3)]


class TestSets(InstanceTestCase):
    def test_sets(self):
        self.instance.add_string(
            """
            var set of 0..10: s;
            set of int: s1;
            constraint s1 = s;
            """
        )

        self.instance["s1"] = range(1, 4)
        result = self.instance.solve()
        assert isinstance(result["s"], set)
        assert result["s"] == set(range(1, 4))


class TestString(InstanceTestCase):
    code = """
    array[int] of string: names;
    var index_set(names): x;
    string: name ::output_only ::add_to_output = names[fix(x)];
    """

    def test_string(self):
        names = ["Guido", "Peter"]
        self.instance["names"] = names

        result = self.instance.solve()
        assert result.solution.name in names


class TestTuple(InstanceTestCase):
    @pytest.mark.skipif(
        default_driver is None or default_driver.parsed_version < (2, 7, 0),
        reason="requires MiniZinc 2.7 or higher",
    )
    def test_simple_tuple(self):
        self.instance.add_string(
            """
        var tuple(1..3, bool, 1.0..3.0): x;
        """
        )
        result = self.instance.solve()
        tup = result["x"]
        assert isinstance(tup, list)
        assert len(tup) == 3
        assert isinstance(tup[0], int)
        assert tup[0] in range(1, 4)
        assert isinstance(tup[1], bool)
        assert isinstance(tup[2], float)
        assert 1.0 <= tup[2] and tup[2] <= 3.0

    @pytest.mark.skipif(
        default_driver is None or default_driver.parsed_version < (2, 7, 0),
        reason="requires MiniZinc 2.7 or higher",
    )
    def test_rec_tuple(self):
        self.instance.add_string(
            """
        var tuple(1..3, bool, tuple(2..3, 4..6)): x;
        """
        )
        result = self.instance.solve()
        tup = result["x"]
        assert isinstance(tup, list)
        assert len(tup) == 3
        assert isinstance(tup[0], int)
        assert tup[0] in range(1, 4)
        assert isinstance(tup[1], bool)
        assert isinstance(tup[2], list)
        assert len(tup[2]) == 2
        assert isinstance(tup[2][0], int)
        assert tup[2][0] in range(2, 4)
        assert isinstance(tup[2][1], int)
        assert tup[2][1] in range(4, 7)


class TestRecord(InstanceTestCase):
    @pytest.mark.skipif(
        default_driver is None or default_driver.parsed_version < (2, 7, 0),
        reason="requires MiniZinc 2.7 or higher",
    )
    def test_simple_record(self):
        self.instance.add_string(
            """
        var record(1..3: a, bool: b, 1.0..3.0: c): x;
        """
        )
        result = self.instance.solve()
        rec = result["x"]
        assert isinstance(rec, dict)
        assert len(rec) == 3
        assert isinstance(rec["a"], int)
        assert rec["a"] in range(1, 4)
        assert isinstance(rec["b"], bool)
        assert isinstance(rec["c"], float)
        assert 1.0 <= rec["c"] and rec["c"] <= 3.0

    @pytest.mark.skipif(
        default_driver is None or default_driver.parsed_version < (2, 7, 0),
        reason="requires MiniZinc 2.7 or higher",
    )
    def test_rec_record(self):
        self.instance.add_string(
            """
        var record(1..3: a, bool: b, record(2..3: d, 4..6: e): c): x;
        """
        )
        result = self.instance.solve()
        rec = result["x"]
        assert isinstance(rec, dict)
        assert len(rec) == 3
        assert isinstance(rec["a"], int)
        assert rec["a"] in range(1, 4)
        assert isinstance(rec["b"], bool)
        assert isinstance(rec["c"], dict)
        assert len(rec["c"]) == 2
        assert isinstance(rec["c"]["d"], int)
        assert rec["c"]["d"] in range(2, 4)
        assert isinstance(rec["c"]["e"], int)
        assert rec["c"]["e"] in range(4, 7)


class TestNumPy(InstanceTestCase):
    def test_nparray_bool(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of bool: x;")
        self.instance["x"] = numpy.array([True, False], dtype=numpy.bool_)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_nparray_f32(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of float: x;")
        self.instance["x"] = numpy.array([1, 2, 3], dtype=numpy.float32)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_nparray_f64(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of float: x;")
        self.instance["x"] = numpy.array([1, 2, 3], dtype=numpy.float64)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_nparray_int32(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of int: x;")
        self.instance["x"] = numpy.array([1, 2, 3], dtype=numpy.int32)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_nparray_int64(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of int: x;")
        self.instance["x"] = numpy.array([1, 2, 3], dtype=numpy.int64)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_nparray_uint32(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of int: x;")
        self.instance["x"] = numpy.array([1, 2, 3], dtype=numpy.uint32)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_nparray_uint64(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("array[int] of int: x;")
        self.instance["x"] = numpy.array([1, 2, 3], dtype=numpy.uint64)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_npbool(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("bool: x;")
        self.instance["x"] = numpy.bool_(0)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_npf32(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("float: x;")
        self.instance["x"] = numpy.float32(0)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_npf64(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("float: x;")
        self.instance["x"] = numpy.float64(0)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_npint32(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("int: x;")
        self.instance["x"] = numpy.int32(0)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED

    def test_npint64(self):
        numpy = pytest.importorskip("numpy")
        self.instance.add_string("int: x;")
        self.instance["x"] = numpy.int64(0)
        result = self.instance.solve()
        assert result.status is Status.SATISFIED


class TestAnn(InstanceTestCase):
    def test_ann_atom(self):
        self.instance.add_string("ann: x :: add_to_output = promise_total;")
        result = self.instance.solve()
        assert result.status is Status.SATISFIED
        assert result["x"] == "promise_total"

    def test_ann_call(self):
        self.instance.add_string(
            'ann: x :: add_to_output = expression_name("test");'
        )
        result = self.instance.solve()
        assert result.status is Status.SATISFIED
        assert result["x"] == 'expression_name("test")'
