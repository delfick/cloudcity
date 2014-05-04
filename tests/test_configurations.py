# coding: spec

from cloudcity.errors import BadOptionFormat, BadConfigResolver, InvalidConfigFile, FailedConfigPickup
from cloudcity.configurations import MergedOptionStringFormatter, ConfigReader, ConfigurationFinder
from option_merge import MergedOptions

from tests.helpers import a_temp_file, setup_directory, a_temp_dir

from noseOfYeti.tokeniser.support import noy_sup_setUp
from unittest import TestCase

from textwrap import dedent
import json
import yaml
import mock
import re
import os

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

describe TestCase,"ConfigurationFinder":
    before_each:
        self.folders = mock.Mock(name="folders")
        self.config_reader = mock.Mock(name="config_reader")
        self.config_reader_kls = mock.Mock(name="config_reader_kls")
        self.config_reader_kls.return_value = self.config_reader
        self.finder = ConfigurationFinder(self.folders, self.config_reader_kls)

    it "inits seen, _found, folders and config_reader":
        finder = ConfigurationFinder(self.folders, self.config_reader_kls)
        self.assertIs(finder.folders, self.folders)
        self.assertIs(finder.config_reader, self.config_reader)
        self.assertEqual(finder.seen, {})
        self.assertEqual(finder._found, {})
        finder._found[1].append(2)
        self.assertEqual(finder._found, {1:[2]})

    it "has a method for adding to found":
        key = mock.Mock(name="key")
        value1 = mock.Mock(name="value1")
        value2 = mock.Mock(name="value2")

        self.assertEqual(self.finder._found, {})
        self.finder.add(key, value1)
        self.assertEqual(self.finder._found, {key: [value1]})

        self.finder.add(key, value2)
        self.assertEqual(self.finder._found, {key: [value1, value2]})

    it "has a method for resetting":
        finder = ConfigurationFinder(self.folders, self.config_reader_kls)
        finder.seen = mock.Mock(name="seen")
        finder._found = mock.Mock(name="_found")
        finder.reset()
        self.assertEqual(finder.seen, {})
        self.assertEqual(finder._found, {})

    it "has a property for found that calls pick_up_configs":
        found = mock.Mock(name="_found")
        called = []
        pick_up_configs = mock.Mock(name="pick_up_configs")
        pick_up_configs.side_effect = lambda: called.append(1)
        with mock.patch.object(self.finder, "pick_up_configs", pick_up_configs):
            self.assertEqual(self.finder.found, {})
            pick_up_configs.assert_called_once()
            self.assertEqual(called, [1])

            self.assertEqual(self.finder.found, {})
            pick_up_configs.assert_called_once()
            self.assertEqual(called, [1, 1])

            self.finder._found = found
            self.assertIs(self.finder.found, found)

        self.assertEqual(called, [1, 1])

    describe "Making options":
        it "merges everything in found":
            found = {"one": [{"two": "three"}, {"four": "five"}], "six": [{"seven": "eight"}, {"seven": "nine"}]}
            self.finder._found = found
            options = self.finder.make_options()
            self.assertEqual(sorted(options.as_flat()), sorted([("one.two", "three"), ("one.four", "five"), ("six.seven", "nine")]))

        it "inits global if it isn't there":
            found = {"one": [{"two": "three"}, {"four": "five"}], "six": [{"seven": "eight"}, {"seven": "nine"}]}
            self.finder._found = found
            options = self.finder.make_options()
            self.assertEqual(sorted(options.as_flat()), sorted([("one.two", "three"), ("one.four", "five"), ("six.seven", "nine")]))
            self.assertEqual(options["global"], {})

    describe "Picking up the configs":
        before_each:
            self.config_files = {
                  1: (True, {"a": {"aa": 11}})
                , 2: (False, None)
                , 3: (True, {"b": {"bb": 22}})
                , 4: (True, {"c": {"cc": 33}, "d": {"dd": 44}})
                }

            sorted_files = []
            for name, (is_config, dct) in self.config_files.items():
                alias = "cf{0}".format(name)
                mck = mock.Mock(name=alias)
                mck.dct = dct
                mck.is_config = is_config
                sorted_files.append(mck)
                setattr(self, alias, mck)

            self.sorted_files = mock.Mock(name="sorted_files")
            self.sorted_files.return_value = sorted_files

            def is_config(config_file):
                return config_file.is_config
            self.config_reader.is_config.side_effect = is_config

            def as_dct(config_file):
                return config_file.dct
            self.config_reader.as_dict.side_effect = as_dct

        it "uses config_reader to add dictionaries from config files":
            add = mock.Mock(name="add")

            with mock.patch.multiple(self.finder, sorted_files=self.sorted_files, add=add):
                self.finder.pick_up_configs()

            self.config_reader.is_config.assert_has_calls([mock.call(self.cf1), mock.call(self.cf2), mock.call(self.cf3), mock.call(self.cf4)], any_order=False)
            self.config_reader.as_dict.assert_has_calls([  mock.call(self.cf1),                      mock.call(self.cf3), mock.call(self.cf4)], any_order=False)
            add.assert_has_calls([mock.call("a", {"aa": 11}), mock.call("b", {"bb": 22}), mock.call("c", {"cc": 33}), mock.call("d", {"dd": 44})])

        it "complains about all the configs that failed":
            add = mock.Mock(name="add")
            error1 = InvalidConfigFile("error1")
            error2 = InvalidConfigFile("error2")

            def as_dct(config_file):
                if config_file is self.cf1:
                    raise error1
                elif config_file is self.cf4:
                    raise error2
                else:
                    return config_file.dct
            self.config_reader.as_dict.side_effect = as_dct

            with self.assertRaisesRegexp(FailedConfigPickup, re.escape('"Failed to pickup configs"\terrors={0}'.format(dict([(self.cf1, error1), (self.cf4, error2)])))):
                with mock.patch.multiple(self.finder, sorted_files=self.sorted_files, add=add):
                    self.finder.pick_up_configs()

            self.config_reader.is_config.assert_has_calls([mock.call(self.cf1), mock.call(self.cf2), mock.call(self.cf3), mock.call(self.cf4)], any_order=False)
            self.config_reader.as_dict.assert_has_calls([  mock.call(self.cf1),                      mock.call(self.cf3), mock.call(self.cf4)], any_order=False)
            add.assert_has_calls([mock.call("b", {"bb": 22})])

    describe "Getting all the files in sorted order":
        before_each:
            self.hierarchy = {
                  "a":
                  { "f":
                    { "a": [('1', None), ('2', None)]
                    , "z": [('20', None), ('90', None)]
                    }
                  , "g": [('70', None)]
                  }
                , "c":
                  { "a": None
                  , "b": [('b', None), {'a': {'c': [('d', None)]}}]
                  }
                , "d":
                  { "a": {'a': {'a': {'a': [('1', None)]}}}
                  }
                }

            self.expected_order = [
                  "a.f.a.1"
                , "a.f.a.2"
                , "a.f.z.20"
                , "a.f.z.90"
                , "a.g.70"
                , "c.b.a.c.d"
                , "c.b.b"
                , "d.a.a.a.a.1"
                ]

        def resolve(self, path, record):
            """Resolve the file path into the record"""
            if isinstance(path, basestring):
                path = path.split('.')
            if len(path) is 1:
                return os.path.abspath(os.path.realpath(record[path[0]]))
            else:
                first, rest = path[0], path[1:]
                return self.resolve(rest, record[first])

        it "gets all files in sorted order by file and directory":
            with setup_directory(self.hierarchy) as (root, record):
                finder = ConfigurationFinder([root])
                found = list(finder.sorted_files())
                expected = [self.resolve(exp, record) for exp in self.expected_order]
                self.assertEqual(found, expected)

        it "doesn't repeat files":
            with setup_directory(self.hierarchy) as (root, record):
                os.symlink(record['a']['g']['/folder/'], os.path.join(record['a']['f']['z']['/folder/'], 'h'))
                finder = ConfigurationFinder([root, record["a"]["f"]["/folder/"]])
                found = list(finder.sorted_files())
                expected = [self.resolve(exp, record) for exp in self.expected_order]
                self.assertEqual(found, expected)

        it "deals with symlinks":
            other_hierarchy = {
                  "t":
                  { "s": [('0', None), ('7', None)]
                  , "j": [('50', None), ('60', None)]
                  }
                }

            other_expected = [
                  'b.t.j.50'
                , 'b.t.j.60'
                , 'b.t.s.0'
                , 'b.t.s.7'
                ]

            with setup_directory(other_hierarchy) as (other_root, other_record):
                with setup_directory(self.hierarchy) as (root, record):
                    os.symlink(other_root, os.path.join(record['/folder/'], 'b'))
                    record['b'] = other_record

                    finder = ConfigurationFinder([root])
                    found = list(finder.sorted_files())
                    for index, item in enumerate(self.expected_order):
                        if not item.startswith('a'):
                            break
                    expected_order = self.expected_order[:index] + other_expected + self.expected_order[index:]
                    expected = [self.resolve(exp, record) for exp in expected_order]
                    self.assertEqual(found, expected)

