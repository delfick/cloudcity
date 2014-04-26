# coding: spec

from cloudcity.errors import BadOptionFormat, BadConfigResolver, InvalidConfigFile
from cloudcity.configurations import MergedOptionStringFormatter, ConfigReader
from option_merge import MergedOptions

from tests.helpers import a_temp_file

from noseOfYeti.tokeniser.support import noy_sup_setUp
from unittest import TestCase

from textwrap import dedent
import json
import yaml
import mock
import re

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

describe TestCase, "ConfigReader":
    before_each:
        self.reader = ConfigReader()

    it "setup default resolvers":
        self.assertEqual(self.reader.resolvers, {"json": self.reader.read_json, "yaml": self.reader.read_yaml})

    describe "Registering a resolver":
        it "overrides that extension in resolvers":
            resolver = lambda val: 2
            self.reader.register("lolz", resolver)
            self.assertIs(self.reader.resolvers['lolz'], resolver)

        it "complains if the resolver is not a callable":
            for not_callable in (0, 1, None, True, False, [], [1], {}, {1:1}, type("thing", (object, ), {})()):
                with self.assertRaisesRegexp(BadConfigResolver, re.escape("not_callable={0}".format(not_callable))):
                    self.reader.register("hmmm", not_callable)

        it "doesn't complain if the resolver is callable":
            lambdad = lambda val: 1
            kls = type("stuff", (object, ), {'meth': lambdad})
            method = kls.meth
            def function(val):
                return 5
            mocked = mock.Mock(name="mock")
            for callableable in (lambdad, kls, method, function, mocked):
                self.reader.register("a_callable", callableable)

    describe "Determining if a file is a config":
        it "is a config if it has a matched_extension":
            config_file = mock.Mock(name="config_file")
            matched_extension = mock.Mock(name="matched_extension")
            matched_extension.return_value = "json"
            with mock.patch.object(self.reader, "matched_extension", matched_extension):
                assert self.reader.is_config(config_file)

        it "is not a config if it has no matched_extension":
            config_file = mock.Mock(name="config_file")
            matched_extension = mock.Mock(name="matched_extension")
            matched_extension.return_value = None
            with mock.patch.object(self.reader, "matched_extension", matched_extension):
                assert not self.reader.is_config(config_file)

    describe "Finding a matched extension":
        it "returns the first matched extension from resolvers":
            config_file = "a_file.json.yaml"
            self.assertEqual(self.reader.matched_extension(config_file), "yaml")

            config_file = "a_file.json"
            self.assertEqual(self.reader.matched_extension(config_file), "json")

            self.reader.resolvers["tar.gz"] = True
            config_file = "a_file.tar.gz"
            self.assertEqual(self.reader.matched_extension(config_file), "tar.gz")

        it "returns None if there is no matched extension":
            assert "blah" not in self.reader.resolvers
            config_file = "a_file.blah"
            self.assertIs(self.reader.matched_extension(config_file), None)

            assert "tar.gz" not in self.reader.resolvers
            config_file = "a_file.tar.gz"
            self.assertIs(self.reader.matched_extension(config_file), None)

    describe "Returning config_file as a dictionary":
        it "complains if the config file has no matched extension":
            assert "blah" not in self.reader.resolvers
            with self.assertRaisesRegexp(InvalidConfigFile, '"Invalid config file. Unrecognised filetype"\tconfig_file=somewhere.blah'):
                self.reader.as_dict("somewhere.blah")

        it "Uses the resolvers to return a dictionary":
            as_dict = mock.Mock(name="as_dict")
            self.reader.resolvers["blah"] = lambda config_file: as_dict
            self.assertIs(self.reader.as_dict("somewhere.blah"), as_dict)

    describe "Reading json":
        it "loads it from the file":
            dct = {"a": 1, "b": 2, "c": [1, 2, 3]}
            with a_temp_file(json.dumps(dct)) as filename:
                self.assertEqual(self.reader.read_json(filename), dct)

        it "Doesn't complain if there is no json to read":
            with a_temp_file() as filename:
                self.assertEqual(self.reader.read_json(filename), {})

        it "Complains if the json is invalid":
            invalid_jsons = [
                  ('{', "Expecting object: line 1 column 1 (char 0)")
                , ('[', "Expecting object: line 1 column 1 (char 0)")
                , ("{'a': 1}", "Expecting property name: line 1 column 2 (char 1)")
                , ('{"a": 1, }', "Expecting property name: line 1 column 10 (char 9)")
                , ('{a: 1}', "Expecting property name: line 1 column 2 (char 1)")
                , ('asdf', "No JSON object could be decoded")
                ]

            with a_temp_file() as filename:
                for invalid_json, error in invalid_jsons:
                    with open(filename, 'w') as fle:
                        fle.write(invalid_json)

                    with self.assertRaisesRegexp(InvalidConfigFile, re.escape('"Invalid config file. Failed to read json"\terror={0}\terror_type=ValueError'.format(error))):
                        self.reader.read_json(filename)

    describe "Reading yaml":
        it "loads it from the file":
            dct = {"a": 1, "b": 2, "c": [1, 2, 3]}
            with a_temp_file(yaml.dump(dct)) as filename:
                self.assertEqual(self.reader.read_yaml(filename), dct)

        it "Doesn't complain if there is no yaml to read":
            with a_temp_file() as filename:
                self.assertEqual(self.reader.read_yaml(filename), {})

        it "Complains if the yaml is invalid":
            invalid_yamls = [
                  ("""
                   :
                   """
                  , "expected <block end>, but found ':'"
                  )

                , ("""
                   - 1
                   a: 3
                   """
                  , "expected <block end>, but found '?'"
                  )

                ]

            with a_temp_file() as filename:
                for invalid_yaml, error in invalid_yamls:
                    with open(filename, 'w') as fle:
                        fle.write(dedent(invalid_yaml).lstrip())

                    with self.assertRaisesRegexp(InvalidConfigFile, re.escape('"Invalid config file. Failed to read yaml"\terror={0}\terror_type=ParserError'.format(error))):
                        self.reader.read_yaml(filename)

