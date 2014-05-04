# coding: spec

from cloudcity.stack_layers import StackLayers
from cloudcity.errors import StackDepCycle

from noseOfYeti.tokeniser.support import noy_sup_setUp, noy_sup_tearDown
from unittest import TestCase
import mock

import nose

describe TestCase, "StackLayer":
    before_each:
        self.stack1 = mock.Mock(name="stack1")
        self.stack2 = mock.Mock(name="stack2")
        self.stack3 = mock.Mock(name="stack3")
        self.stacks = {'stack1': self.stack1, 'stack2': self.stack2, 'stack3': self.stack3}
        self.instance = StackLayers(self.stacks)

    def assertCallsSame(self, mock, expected):
        print "Printing calls as <done> || <expected>"
        print "----"

        call_list = mock.call_args_list
        for did, wanted in map(None, call_list, expected):
            print "     {0} || {1}".format(did, wanted)
            print "--"

        self.assertEqual(len(call_list), len(expected))
        mock.assert_has_calls(expected)

    it "takes a dictionary of stacks":
        stacks = mock.Mock(name="stacks")
        layers = StackLayers(stacks)
        self.assertIs(layers.stacks, stacks)

    describe "Resetting the instance":
        it "resets layered to an empty list":
            self.instance._layered = mock.Mock(name="layered")
            self.instance.reset()
            self.assertEqual(self.instance._layered, [])

        it "resets accounted to an empty dict":
            self.instance.accounted = mock.Mock(name="accounted")
            self.instance.reset()
            self.assertEqual(self.instance.accounted, {})

    describe "Getting layered":
        it "has a property for converting _layered into a list of list of tuples":
            self.instance._layered = [["one"], ["two", "three"], ["four"]]
            self.instance.stacks = {"one": 1, "two": 2, "three": 3, "four": 4}
            self.assertEqual(self.instance.layered, [[("one", 1)], [("two", 2), ("three", 3)], [("four", 4)]])

    describe "Adding layers":
        before_each:
            self.stacks = {}
            for i in range(1, 10):
                name = "stack{0}".format(i)
                obj = mock.Mock(name=name)
                obj.dependencies = []
                setattr(self, name, obj)
                self.stacks[name] = obj
            self.instance = StackLayers(self.stacks)

        def assertLayeredSame(self, layers, expected):
            if not layers.layered:
                layers.add_all_to_layers()
            created = layers.layered

            print "Printing expected and created as each layer on a new line."
            print "    the line starting with || is the expected"
            print "    the line starting with >> is the created"
            print "----"

            for expcted, crted in map(None, expected, created):
                print "    || {0}".format(sorted(expcted) if expcted else None)
                print "    >> {0}".format(sorted(crted) if crted else None)
                print "--"

            error_msg = "Expected created layered to have {0} layers. Only has {1}".format(len(expected), len(created))
            self.assertEqual(len(created), len(expected), error_msg)

            for index, layer in enumerate(created):
                nxt = expected[index]
                self.assertEqual(sorted(layer) if layer else None, sorted(nxt) if nxt else None)

        it "has a method for adding all the stacks":
            add_to_layers = mock.Mock(name="add_to_layers")
            with mock.patch.object(self.instance, "add_to_layers", add_to_layers):
                self.instance.add_all_to_layers()
            self.assertCallsSame(add_to_layers, sorted([mock.call(stack) for stack in self.stacks]))

        it "does nothing if the stack is already in accounted":
            self.assertEqual(self.instance._layered, [])
            self.instance.accounted['stack1'] = True

            self.stack1.dependencies = []
            self.instance.add_to_layers("stack1")
            self.assertEqual(self.instance._layered, [])
            self.assertEqual(self.instance.accounted, {'stack1': True})

        it "adds stack to accounted if not already there":
            self.assertEqual(self.instance._layered, [])
            self.assertEqual(self.instance.accounted, {})

            self.stack1.dependencies = []
            self.instance.add_to_layers("stack1")
            self.assertEqual(self.instance._layered, [["stack1"]])
            self.assertEqual(self.instance.accounted, {'stack1': True})

        it "complains about cyclic dependencies":
            self.stack1.dependencies = ['stack2']
            self.stack2.dependencies = ['stack1']

            with self.assertRaisesRegexp(StackDepCycle, "\"Stack dependency cycle\"\tchain=\['stack1', 'stack2', 'stack1'\]"):
                self.instance.add_to_layers("stack1")

            self.instance.reset()
            with self.assertRaisesRegexp(StackDepCycle, "\"Stack dependency cycle\"\tchain=\['stack2', 'stack1', 'stack2'\]"):
                self.instance.add_to_layers("stack2")

        describe "Dependencies":
            before_each:
                self.fake_add_to_layers = mock.Mock(name="add_to_layers")
                original = self.instance.add_to_layers
                self.fake_add_to_layers.side_effect = lambda *args, **kwargs: original(*args, **kwargs)
                self.patcher = mock.patch.object(self.instance, "add_to_layers", self.fake_add_to_layers)
                self.patcher.start()

            after_each:
                self.patcher.stop()

            describe "Simple dependencies":
                it "adds all stacks to the first layer if they don't have dependencies":
                    self.assertLayeredSame(self.instance, [self.stacks.items()])

                it "adds stack after it's dependency if one is specified":
                    self.stack3.dependencies = ["stack1"]
                    cpy = dict(self.stacks.items())
                    del cpy["stack3"]
                    expected = [cpy.items(), [("stack3", self.stack3)]]
                    self.assertLayeredSame(self.instance, expected)

                it "works with stacks sharing the same dependency":
                    self.stack3.dependencies = ["stack1"]
                    self.stack4.dependencies = ["stack1"]
                    self.stack5.dependencies = ["stack1"]

                    cpy = dict(self.stacks.items())
                    del cpy["stack3"]
                    del cpy["stack4"]
                    del cpy["stack5"]
                    expected = [cpy.items(), [("stack3", self.stack3), ("stack4", self.stack4), ("stack5", self.stack5)]]
                    self.assertLayeredSame(self.instance, expected)

            describe "Complex dependencies":
                it "works with more than one level of dependency":
                    self.stack3.dependencies = ["stack1"]
                    self.stack4.dependencies = ["stack1"]
                    self.stack5.dependencies = ["stack1"]
                    self.stack9.dependencies = ["stack4"]

                    #      9
                    #      |
                    # 3    4    5
                    # \    |    |
                    #  \   |   /
                    #   \  |  /
                    #    --1--         2     6     7     8

                    expected_calls = [
                          mock.call("stack1")
                        , mock.call("stack2")
                        , mock.call("stack3")
                        , mock.call("stack1", ["stack3"])
                        , mock.call("stack4")
                        , mock.call("stack1", ["stack4"])
                        , mock.call("stack5")
                        , mock.call("stack1", ["stack5"])
                        , mock.call("stack6")
                        , mock.call("stack7")
                        , mock.call("stack8")
                        , mock.call("stack9")
                        , mock.call("stack4", ["stack9"])
                        ]

                    expected = [
                          [("stack1", self.stack1), ("stack2", self.stack2), ("stack6", self.stack6), ("stack7", self.stack7), ("stack8", self.stack8)]
                        , [("stack3", self.stack3), ("stack4", self.stack4), ("stack5", self.stack5)]
                        , [("stack9", self.stack9)]
                        ]

                    self.instance.add_all_to_layers()
                    self.assertCallsSame(self.fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(self.instance, expected)

                it "handles more complex dependencies":
                    self.stack1.dependencies = ['stack2']
                    self.stack2.dependencies = ['stack3', 'stack4']
                    self.stack4.dependencies = ['stack5']
                    self.stack6.dependencies = ['stack9']
                    self.stack7.dependencies = ['stack6']
                    self.stack9.dependencies = ['stack4', 'stack8']

                    #                     7
                    #                     |
                    #     1               6
                    #     |               |
                    #     2               9
                    #   /   \          /     \
                    # /       4   ----        |
                    # |       |               |
                    # 3       5               8

                    expected_calls = [
                        mock.call("stack1")
                        , mock.call("stack2", ["stack1"])
                        , mock.call("stack3", ["stack1", "stack2"])
                        , mock.call("stack4", ["stack1", "stack2"])
                        , mock.call("stack5", ["stack1", "stack2", "stack4"])
                        , mock.call("stack2")
                        , mock.call("stack3")
                        , mock.call("stack4")
                        , mock.call("stack5")
                        , mock.call("stack6")
                        , mock.call("stack9", ["stack6"])
                        , mock.call("stack4", ["stack6", "stack9"])
                        , mock.call("stack8", ["stack6", "stack9"])
                        , mock.call("stack7")
                        , mock.call("stack6", ["stack7"])
                        , mock.call("stack8")
                        , mock.call("stack9")
                        ]

                    expected = [
                        [("stack3", self.stack3), ("stack5", self.stack5), ("stack8", self.stack8)]
                        , [("stack4", self.stack4)]
                        , [("stack2", self.stack2), ("stack9", self.stack9)]
                        , [("stack1", self.stack1), ("stack6", self.stack6)]
                        , [("stack7", self.stack7)]
                        ]

                    self.instance.add_all_to_layers()
                    self.assertCallsSame(self.fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(self.instance, expected)

