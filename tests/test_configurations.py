# coding: spec

from cloudcity.configurations import MergedOptionStringFormatter
from cloudcity.errors import BadOptionFormat
from option_merge import MergedOptions

from noseOfYeti.tokeniser.support import noy_sup_setUp
from unittest import TestCase
import mock

describe TestCase, "MergedOptions string formatter":
    before_each:
        self.all_options = MergedOptions.using(
              {"global": {"a":1, "b":2, "c":{"d":3, "e":4}}}
            , {"global": {"a":7, "f":[6, 7, 8]}}
            , {"global": {"a": {"g": {"h" : {"i": 10}}}}}
            )

    it "takes in all_options and config_only":
        all_options = mock.Mock(name="all_options")
        config_only = mock.Mock(name="config_only")
        formatter = MergedOptionStringFormatter(all_options, config_only=config_only)

        self.assertIs(formatter.all_options, all_options)
        self.assertIs(formatter.config_only, config_only)

    it "resolves to options found in all_options":
        formatter = MergedOptionStringFormatter(self.all_options)
        result = formatter.format("{global.b}.t - {global.c.e:02d} - {global.a.g.h.i}")
        self.assertEqual(result, "2.t - 04 - 10")

    it "complains if you format in a whole stack":
        formatter = MergedOptionStringFormatter(self.all_options)
        with self.assertRaisesRegexp(BadOptionFormat, '"Bad option format string. Shouldn\'t format a whole stack into the string"'):
            result = formatter.format("{global}.t")

    it "complains if you format in a dictionary":
        formatter = MergedOptionStringFormatter(self.all_options)
        with self.assertRaisesRegexp(BadOptionFormat, '"Bad option format string. Shouldn\'t format in a dictionary"\tkey=global.a'):
            result = formatter.format("{global.a}.t")

    it "complains if config_only is set and you use a value from a non-config stack":
        self.all_options.update({"other": {"type": "not_a_config", "e": 4}})
        formatter = MergedOptionStringFormatter(self.all_options, config_only=True)
        with self.assertRaisesRegexp(BadOptionFormat, '"Bad option format string. Can only resolve options from \'config\' stacks"\tinvalid_stack_type=not_a_config\toption=other.e'):
            result = formatter.format("{other.e}.t")

    it "does not complain if config_only is set and you use a value from a non-config stack":
        self.all_options.update({"other": {"type": "config", "e": 4}})
        formatter = MergedOptionStringFormatter(self.all_options, config_only=False)
        result = formatter.format("{other.e}.t")
        self.assertEqual(result, "4.t")

