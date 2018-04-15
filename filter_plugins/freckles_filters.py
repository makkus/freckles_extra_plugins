import copy
import re
from collections import OrderedDict
import os
import yaml
from ansible import errors
from frkl import frkl
from nsbl.nsbl import ensure_git_repo_format
from six import string_types
from freckles.freckles_defaults import DEFAULT_PROFILE_VAR_FORMAT, DEFAULT_VAR_FORMAT, DEFAULT_PACKAGE_FORMAT
from freckles.utils import render_dict


class FilterModule(object):

    def filters(self):
        return {
            'assemble_package_list': self.assemble_package_list,
            'relative_path': self.relative_path,
            'file_list_filter': self.file_list_filter,
            'expand_user_remote': self.expand_user_remote
        }

    def expand_user_remote(self, path, user_home):

        if path.startswith("~"):
            result = os.path.join(user_home, path[2:])
        elif path.startswith("/"):
            result = path
        else:
            result = os.path.join(user_home, path)

        return result

    def file_list_filter(self, list_of_files, filter_regex):

        r = re.compile(filter_regex)
        result = filter(r.match, list_of_files)
        return result

    def relative_path(self, list_of_files, path):

        return [os.path.relpath(f, path) for f in list_of_files]

    def assemble_package_list(self, vars_dict, packages_vars_name="install", default_pkg_mgr="auto"):

        packages = vars_dict.get(packages_vars_name, [])
        if not packages:
            return []

        parent_vars = copy.deepcopy(vars_dict)
        parent_vars.pop(packages_vars_name, None)

        if "pkg_mgr" not in parent_vars.keys():
            parent_vars["pkg_mgr"] = default_pkg_mgr
        pkg_config = {"vars": parent_vars, "packages": packages}

        chain = [frkl.FrklProcessor(DEFAULT_PACKAGE_FORMAT)]
        frkl_obj = frkl.Frkl(pkg_config, chain)
        pkgs = frkl_obj.process()

        return pkgs
