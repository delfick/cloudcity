from setuptools import setup, find_packages

setup(
      name = "cloudcity"
    , version = "0.1"
    , packages = ['cloudcity'] + ['cloudcity.%s' % pkg for pkg in find_packages('cloudcity')]
    , include_package_data = True

    , install_requires =
      [ 'option_merge>=0.3'
      , 'pyYaml'
      ]

    , extras_require =
      { "tests":
        [ "noseOfYeti>=1.4.9"
        , "nose"
        , "mock"
        ]
      }

    , entry_points =
      { 'console_scripts' :
        [ 'cloudcity = cloudcity.executor:main'
        ]
      }

    # metadata for upload to PyPI
    , url = "http://cloudcity.readthedocs.org"
    , author = "Stephen Moore"
    , author_email = "stephen@delfick.com"
    , description = "Layer on top of cloudformation for stringing together dependent stacks"
    , license = "WTFPL"
    , keywords = "cloudformation amazon stack dependencies"
    )
