from __future__ import absolute_import, division, print_function

import json

import os
import copy
from ansible import constants as C
from ansible.plugins.action import ActionBase
from frkl import frkl
from nsbl.nsbl import ensure_git_repo_format, get_pkg_mgr_sudo
from requests.structures import CaseInsensitiveDict

__metaclass__ = type

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()

boolean = C.mk_boolean

IGNORE_KEY = "IGNORE_THIS_KEY"
VARS_KEY = "vars"


class BasePkgMgr(object):
    def __init__(self):
        pass

    def get_name(self):
        return "generic"

    def prepare(self, package_vars, calculated_package, task_vars, result):
        """Returns all vars the package needs."""

        result = {}
        if calculated_package:
            if not isinstance(calculated_package, (list, tuple)):
                calculated_package = [calculated_package]
            for pkg in calculated_package:
                result[pkg] = {"name": pkg}
        else:
            temp = package_vars["name"]
            result[temp] = {"name": temp}

        return result

    def get_supported_vars(self):
        """Returns all vars that are supported by this pkg mgr module and should be forwarded.

        Returns None if unknown, in which case all direct descendents of the install task in question are forwarded.
        """

        return None


class GitPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "git"

    def prepare(self, package_vars, calculated_package, task_vars, result):
        if calculated_package:
            calculated_package = ensure_git_repo_format(calculated_package)
            # we can be sure pkg_name is now a dict
            return {calculated_package["repo"]: calculated_package}
        else:
            if "repo" in package_vars.keys():
                temp = ensure_git_repo_format(package_vars["repo"], package_vars.get("dest", None))
            else:
                temp = ensure_git_repo_format(package_vars["name"], package_vars.get("dest", None))

            return {temp["repo"]: temp}

    def get_supported_vars(self):

        return ["accept_hostkey", "archive", "bare", "clone", "depth", "dest", "executable", "force", "key_file",
                "recursive", "reference", "refspec", "repo", "ssh_opts", "track_submodules", "umask", "update",
                "verify_commit", "version"]


class AptPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "apt"

    def prepare(self, package_vars, calculated_package, task_vars, result):
        result = {}
        if calculated_package:
            if not isinstance(calculated_package, (list, tuple)):
                calculated_package = [calculated_package]
            for pkg in calculated_package:
                if pkg.endswith(".deb"):
                    result[pkg] = {"deb": pkg, "name": IGNORE_KEY, "update_cache": IGNORE_KEY, "package": IGNORE_KEY}
                else:
                    result[pkg] = {"name": pkg, "deb": IGNORE_KEY}
        else:
            temp = package_vars["name"]
            if temp.endswith(".deb"):
                result[temp] = {"deb": temp, "name": IGNORE_KEY, "update_cache": IGNORE_KEY, "package": IGNORE_KEY}
            else:
                result[temp] = {"name": temp, "deb": IGNORE_KEY}

        return result

    def get_supported_vars(self):

        return ["name", "state", "allow_unauthenticated", "autoclean", "autoremove", "cache_valid_time", "deb",
                "default_release", "dpkg_options", "force", "install_recommends", "only_upgrades", "purge",
                "update_cache", "upgrade"]


class YumPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "yum"

    def get_supported_vars(self):
        return ["name", "state", "conf_file", "disable_gpg_check", "disablerepo", "enablerepo", "exclude",
                "installroot", "skip_broken", "update_cache", "validate_certs"]


class NixPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "nix"

    def get_supported_vars(self):
        return ["name", "state"]


class NpmPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "npm"

    def get_supported_vars(self):
        return ["executable", "global", "ignore_scripts", "name", "path", "production", "registry", "state", "version"]

    # probably better not to mess with default vars, otherwise:
    # def prepare(self, package_vars, calculated_package, task_vars, result):

    #     name = package_vars["name"]

    #     valid_vars = copy.deepcopy(package_vars)
    #     for k in package_vars.keys():
    #         if k not in self.get_supported_vars():
    #             valid_vars.pop(k)

    #     if not "global" in valid_vars.keys():
    #         valid_vars["global"] = True

    #     return {name: valid_vars}


class PipPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "pip"

    def prepare(self, package_vars, calculated_package, task_vars, result):

        result_v = {}

        if calculated_package:
            if not isinstance(calculated_package, (list, tuple)):
                calculated_package = [calculated_package]
            for pkg in calculated_package:
                if pkg.endswith(".txt"):
                    result_v[pkg] = {"requirements": pkg, "name": IGNORE_KEY}
                else:
                    result_v[pkg] = {"name": pkg, "requirements": IGNORE_KEY}
        else:
            temp = package_vars["name"]
            if temp.endswith(".txt"):
                result_v[temp] = {"requirements": temp, "name": IGNORE_KEY}
            else:
                result_v[temp] = {"name": temp, "requirements": IGNORE_KEY}

        return result_v

    def get_supported_vars(self):

        return ["chdir", "editable", "executable", "extra_args", "name", "requirements", "state", "umask", "version",
                "virtualenv", "virtualenv_command", "virtualenv_python", "virtualenv_site_packages"]


class CondaPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "conda"

    def prepare(self, package_vars, calculated_package, task_vars, result):

        result = {}
        if calculated_package:
            if not isinstance(calculated_package, (list, tuple)):
                calculated_package = [calculated_package]
            for pkg in calculated_package:
                result[pkg] = {"name": pkg}
        else:
            temp = package_vars["name"]
            result[temp] = {"name": temp}

        return result

    def get_supported_vars(self):

        return ['conda_environment', 'upgrade', 'conda_channels', 'state', 'name']


class VagrantPluginPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "vagrant_plugin"

    def get_supported_vars(self):
        return ['name', 'update', 'plugin_source', 'version']


SUPPORTED_PKG_MGRS = {
    'generic': BasePkgMgr,
    'git': GitPkgMgr,
    'apt': AptPkgMgr,
    'conda': CondaPkgMgr,
    'nix': NixPkgMgr,
    'yum': YumPkgMgr,
    'pip': PipPkgMgr,
    'npm': NpmPkgMgr,
    'vagrant_plugin': VagrantPluginPkgMgr
}

DEFAULT_PKG_MGR_VARS = ["name", "state"]
USE_TOP_LEVEL_AS_PKG_NAME = False


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        ''' handler for template operations '''

        self.nsbl_env = os.environ.get("NSBL_ENVIRONMENT", False) == "true"

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        format = {"child_marker": "packages",
                  "default_leaf": "vars",
                  "default_leaf_key": "name",
                  "key_move_map": {'*': "vars"}}
        chain = [frkl.FrklProcessor(format)]

        frkl_obj = frkl.Frkl(self._task.args.get("packages", []), chain)

        package = frkl_obj.process()
        if len(package) == 0:
            raise Exception("No packages provided for package: {}".format(self._task.args))
        if len(package) != 1:
            raise Exception("For some reason more than one package provided, this shouldn't happen: {}".format(package))

        package = package[0]

        if "pkg_mgr" not in package[VARS_KEY].keys():
            pkg_mgr = self._task.args.get('pkg_mgr', 'auto')
        else:
            pkg_mgr = package[VARS_KEY]["pkg_mgr"]

        if pkg_mgr == 'auto':
            try:
                if self._task.delegate_to:
                    pkg_mgr = self._templar.template(
                        "{{hostvars['%s']['ansible_facts']['ansible_pkg_mgr']}}" % self._task.delegate_to)
                else:
                    pkg_mgr = self._templar.template('{{ansible_facts["ansible_pkg_mgr"]}}')
            except Exception as e:
                pass  # could not get it from template!

        auto = pkg_mgr == 'auto'

        facts = self._execute_module(module_name='setup', module_args=dict(gather_subset='!all'), task_vars=task_vars)

        if "ansible_facts" not in facts.keys():
#            import pprint
#            raise Exception(facts)
        # if facts.get("rc", -1000) != 0:
        # if facts["failed"]:
            # msg = facts.get("msg", "")
            # module_stderr = facts.get("module_stderr")
            # if module_stderr:
            #     msg = msg + "\n{}".format(module_stderr)
            # module_stdout = facts.get("module_stdout")
            # if module_stdout:
            #     msg = msg + "\n{}".format(module_stdout)
            # result['failed'] = True
            # result['msg'] = msg
            return facts

        if auto:
            pkg_mgr = facts['ansible_facts'].get('ansible_pkg_mgr', None)
        os_family = facts['ansible_facts'].get('ansible_os_family', None)
        distribution = facts['ansible_facts'].get('ansible_distribution', None)
        distribution_major_version = facts['ansible_facts'].get('ansible_distribution_major_version', None)
        distribution_version = facts['ansible_facts'].get('ansible_distribution_version', None)
        distribution_release = facts['ansible_facts'].get('ansible_distribution_release', None)
        # figure out actual package name
        if distribution_version:
            full_version_string = "{}-{}".format(distribution, distribution_version).lower()
        else:
            full_version_string = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        if distribution_release:
            full_release_string = "{}-{}".format(distribution, distribution_release).lower()
        else:
            full_release_string = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        if distribution_major_version:
            distribution_major_string = "{}-{}".format(distribution, distribution_major_version).lower()
        else:
            distribution_major_string = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        distribution_string = distribution.lower()
        os_string = os_family.lower()

        if pkg_mgr == 'unknown' and os_family == "Darwin":
            pkg_mgr = "homebrew"

        if pkg_mgr in ['auto', 'unknown']:
            result['failed'] = True
            result['msg'] = 'Could not detect which package manager to use. Try gathering facts or setting the "use" option.'
            return result

        if pkg_mgr not in self._shared_loader_obj.module_loader:
            result['failed'] = True
            result['msg'] = "Could not find an ansible module for package manager '{}'.".format(pkg_mgr)
            return result

        # calculate package name, just in case
        pkg_dict = CaseInsensitiveDict(package[VARS_KEY].get("pkgs"))
        if pkg_mgr.lower() in (name.lower() for name in pkg_dict.keys()):
            calculated_package_pkg_mgr = pkg_dict[pkg_mgr.lower()]
        elif 'other' in (name.lower() for name in pkg_dict.keys()):
            calculated_package_pkg_mgr = pkg_dict['other']
        else:
            calculated_package_pkg_mgr = None

        if full_version_string in (name.lower() for name in pkg_dict.keys()):
            calculated_package_platform = pkg_dict[full_version_string]
        elif full_release_string in (name.lower() for name in pkg_dict.keys()):
            calculated_package_platform = pkg_dict[full_release_string]
        elif distribution_major_string in (name.lower() for name in pkg_dict.keys()):
            calculated_package_platform = pkg_dict[distribution_major_string]
        elif distribution_string in (name.lower() for name in pkg_dict.keys()):
            calculated_package_platform = pkg_dict[distribution_string]
        elif os_string in (name.lower() for name in pkg_dict.keys()):
            calculated_package_platform = pkg_dict[os_string]
        elif 'other' in (name.lower() for name in pkg_dict.keys()):
            calculated_package_platform = pkg_dict['other']
        else:
            calculated_package_platform = None

            # if calculated_package_platform in ['ignore', 'omit'] or calculated_package_pkg_mgr in ['ignore', 'omit']:
            # result['msg'] = "Ignoring package {}".format(package[VARS_KEY]["name"])
            # result['skipped'] = True
            # return result

        if not auto or not calculated_package_platform:
            calculated_package = calculated_package_pkg_mgr
        elif (calculated_package_platform == "ignore" or calculated_package_platform == "omit") and calculated_package_pkg_mgr:
            calculated_package = calculated_package_pkg_mgr
        else:
            calculated_package = calculated_package_platform

        if calculated_package in ['ignore', 'omit']:
            result['msg'] = "Ignoring package {}".format(package[VARS_KEY]["name"])
            result['skipped'] = True
            return result

        if "become" in package[VARS_KEY].keys():
            become = package[VARS_KEY]["become"]
        else:
            become = get_pkg_mgr_sudo(pkg_mgr)

        module_result = self.execute_package_module(package, calculated_package, auto, pkg_mgr, become, task_vars, result)

        if module_result:
            result.update(module_result)

        return result

    def execute_package_module(self, package, calculated_package, auto, pkg_mgr, become, task_vars, result):

        pkg_mgr_obj = SUPPORTED_PKG_MGRS.get(pkg_mgr, BasePkgMgr)()

        all_pkg_vars = pkg_mgr_obj.prepare(package[VARS_KEY], calculated_package, task_vars, result)

        msgs = []
        overall_changed = False
        overall_failed = False

        installed = []
        skipped = []
        failed = []

        runs = []
        for pkg_id, pkg_vars in all_pkg_vars.items():

            if package[VARS_KEY].get("no_install", False):
                skipped.append(pkg_id)
                run = {"changed": False, "skipped": True,
                       "msg": "Package '{}' tagged with 'no_install', ignoring".format(pkg_id)}
                runs.append(run)
                continue

            # display.display("nsbl: installing {}".format(pkg_id))

            new_module_args = {}
            keys = pkg_mgr_obj.get_supported_vars()

            if not keys:
                keys = DEFAULT_PKG_MGR_VARS

            for key in keys:
                if key in package[VARS_KEY].keys():
                    new_module_args[key] = package[VARS_KEY][key]
                else:
                    if key in self._task.args.keys():
                        new_module_args[key] = self._task.args[key]

            new_module_args.update(pkg_vars)
            # removing all ignore keys
            new_module_args = {k: v for k, v in new_module_args.items() if v != IGNORE_KEY}

            display.vvvv("Running %s" % pkg_mgr)
            display.vvvv("Args: {}".format(new_module_args))
            if self.nsbl_env:
                output = {"category": "nsbl_item_started", "action": "install",
                          "item": "{} (using: {})".format(pkg_id, pkg_mgr)}
                display.display(json.dumps(output, encoding='utf-8'))

            self._play_context.become = become

            run = self._execute_module(module_name=pkg_mgr, module_args=new_module_args, task_vars=task_vars,
                                       wrap_async=self._task.async)

            # print("ignore: {}".format(run))
            runs.append(run)

            if "failed" in run.keys():
                run_failed = run["failed"]
            else:
                run_failed = False

            if run_failed:
                failed.append(pkg_id)
                overall_failed = True

            if "changed" in run.keys():
                changed = run["changed"]
            else:
                changed = False

            if "msg" in run.keys():
                run_msg = run['msg']
                msgs.append(run_msg)
            else:
                run_msg = None

            if "module_stderr" in run.keys():
                run_module_stderr = run['module_stderr']
            else:
                run_module_stderr = None

            if changed:
                overall_changed = True
                installed.append(pkg_id)
            elif not run_failed:
                skipped.append(pkg_id)

            if self.nsbl_env:
                output = {"item": "{} (using: {})".format(pkg_id, pkg_mgr)}
                if run_msg:
                    if run_msg == "MODULE FAILURE" and run_module_stderr:
                        output["msg"] = run_module_stderr
                    else:
                        output["msg"] = run_msg

                    output["action"] = "install"
                if run_failed:
                    output["failed"] = True
                    output["category"] = "nsbl_item_failed"
                else:
                    output["category"] = "nsbl_item_ok"
                    if changed:
                        output["status"] = "changed"
                    else:
                        output["status"] = "ok"

                display.display(json.dumps(output, encoding='utf-8'))

        if len(runs) == 1:
            return runs[0]
        else:
            msg = "Installed: {}, Skipped: {}, Failed: {}".format(installed, skipped, failed)
            runs_result = {"changed": overall_changed, "msg": msg, "failed": overall_failed, "runs": runs}
            return runs_result
