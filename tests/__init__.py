import aws_ec2_instance_reaper
import doctest
import pkgutil


def load_tests(loader, tests, ignore):
    print([name for _, name, _ in pkgutil.iter_modules(["testpkg"])])

    tests.addTests(doctest.DocTestSuite(aws_ec2_instance_reaper.reaper))
    return tests
