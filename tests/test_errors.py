# coding: spec

from cloudcity.errors import CloudCityError

from unittest import TestCase

describe TestCase, "CloudCityError":
    it "creates a message that combines desc on the class, args and kwargs":
        error = CloudCityError("The rainbow disappeared", a=1, b=2)
        self.assertEqual(str(error), '"The rainbow disappeared"\ta=1\tb=2')

    it "Works without kwargs":
        error = CloudCityError("Could not find a pot of gold")
        self.assertEqual(str(error), '"Could not find a pot of gold"')

    it "Works without a message":
        error = CloudCityError(leprechaun=3, trees=4)
        self.assertEqual(str(error), 'leprechaun=3\ttrees=4')

    it "works with subclasses of CloudCityError":
        class OtherError(CloudCityError):
            desc = "Bad things happen!"
        error = OtherError(6, d=7, e=8)
        self.assertEqual(str(error), '"Bad things happen!. 6"\td=7\te=8')

        error = OtherError(e=9, f=10)
        self.assertEqual(str(error), '"Bad things happen!"\te=9\tf=10')

