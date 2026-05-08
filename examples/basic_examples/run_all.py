# import glob
# import importlib.abc
# import runpy
# from os.path import basename, dirname, isfile, join

# modules = glob.glob(join(dirname(__file__), "*.py"))
# all_files_in_current_directory = [
#     basename(f)[:-3] for f in modules if isfile(f) and not f.endswith("__init__.py")
# ]
# for current_file in all_files_in_current_directory:
#     print("import: ", current_file)
#     # loader =

#     result = runpy._run_module_as_main(current_file)
#     # text = importlib.abc.Loader.exec_module(current_file)
#     print("done")


import glob
import importlib.util
import os
import secrets
import string
import sys
from os.path import basename, dirname, isfile, join

from ethos_penalps.utilities.logger_ethos_penalps import PeNALPSLogger


def lazy_import(name):
    spec = importlib.util.find_spec(name)
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


modules = glob.glob(join(dirname(__file__), "*.py"))

all_files_in_current_directory = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith("__init__.py")]
all_files_in_current_directory.remove("run_all")

for current_file in all_files_in_current_directory:
    PeNALPSLogger.logger.handlers.clear()
    print("import: ", current_file)
    current_module = lazy_import(current_file)
    current_module.define_and_start_simulation()
    # PeNALPSLogger.logger.removeHandler()

    print("done")
