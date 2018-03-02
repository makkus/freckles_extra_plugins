from __future__ import absolute_import, division, print_function

import json

import os
import copy
from ansible import constants as C
from ansible.plugins.action import ActionBase
from frkl import frkl
from nsbl.nsbl import ensure_git_repo_format
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

# TODO, use the respective classes for that:
def get_pkg_mgr_sudo(mgr):
    """Simple function to determine whether a given package manager needs sudo rights or not.
    """
    if mgr == 'no_install':
        return False
    elif mgr == 'nix':
        return False
    elif mgr == 'conda':
        return False
    elif mgr == 'git':
        return False
    elif mgr == 'homebrew':
        return False
    elif mgr == 'homebrew_cask':
        return False
    elif mgr == 'pip':
        return False
    elif mgr == 'npm':
        return False
    elif mgr == 'get_url':
        return False
    elif mgr == 'unarchive':
        return False
    elif mgr == 'vagrant_plugin':
        return False
    else:
        return True


class BasePkgMgr(object):
    def __init__(self):
        pass

    def get_name(self):
        return "generic"

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):
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

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):
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

class GetUrlPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "get_url"

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):
        result = {}
        if calculated_package:
            if not isinstance(calculated_package, (list, tuple)):
                calculated_package = [calculated_package]
            for pkg in calculated_package:
                if pkg.startswith("http") or pkg.startswith("ftp"):
                    result[pkg] = {"url": pkg, "name": IGNORE_KEY}
                else:
                    raise Exception("Can only download via http/https or ftp, invalid url: {}".format(pkg))

        else:
            temp = copy.deepcopy(package_vars)
            if "name" in package_vars.keys():
                name = package_vars["name"]
                temp["name"] = IGNORE_KEY

                if "url" not in package_vars.keys():
                    temp["url"] = name

            result[temp["url"]] = temp

        dests = set()
        for pkg, details in result.items():

            dest = details.setdefault("dest", "~/.local/bin")
            mode = details.setdefault("mode", "0775")
            dests.add(os.path.dirname(dest))

        for dest_dir in dests:
            task_msg = "creating folder: {}".format(dest_dir)
            module_args = {"path": dest_dir, "recurse": True, "state": "directory"}

            if parent.nsbl_env:
                output = {"category": "nsbl_item_started", "action": "install",
                          "item": task_msg}
                display.display(json.dumps(output, encoding='utf-8'))

            # TODO: maybe print what's going on to the user?
            run = parent._execute_module(module_name="file", module_args=module_args, task_vars=task_vars, wrap_async=parent._task.async)

            parent.add_run(run, False, False, False, task_msg)

        return result

    def get_supported_vars(self):

        return ["attributes", "backup", "checksum", "client_cert", "client_key", "dest", "force", "force_basic_auth", "group", "headers", "mode", "others", "owner", "selevel", "serole", "setype", "seuser", "sha256sum", "timeout", "tmp_dest", "unsafe_writes", "url", "url_password", "url_username", "use_proxy", "validate_certs"]


class UnarchivePkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "unarchive"

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):

        result = {}
        if calculated_package:
            if not isinstance(calculated_package, (list, tuple)):
                calculated_package = [calculated_package]
            for pkg in calculated_package:
                result[pkg] = {"src": pkg, "name": IGNORE_KEY}

        else:
            temp = copy.deepcopy(package_vars)
            if "name" in package_vars.keys():
                name = package_vars["name"]
                temp["name"] = IGNORE_KEY

            if "src" not in package_vars.keys():
                temp["src"] = name

            result[temp["src"]] = temp

        dests = set()
        for pkg, details in result.items():

            if pkg.startswith("http") or pkg.startswith("ftp") and "remote_src" not in details.keys():
                details["remote_src"] =  True

            dest = details.setdefault("dest", "~/.local/opt/")
            dests.add(dest)

        for dest_dir in dests:
            task_msg = "creating folder: {}".format(dest_dir)
            module_args = {"path": dest_dir, "recurse": True, "state": "directory"}

            if parent.nsbl_env:
                output = {"category": "nsbl_item_started", "action": "install",
                          "item": task_msg}
                display.display(json.dumps(output, encoding='utf-8'))

            # TODO: maybe print what's going on to the user?
            run = parent._execute_module(module_name="file", module_args=module_args, task_vars=task_vars, wrap_async=parent._task.async)

            parent.add_run(run, False, False, False, task_msg)

        return result

    def get_supported_vars(self):

        return ["attributes", "copy", "creates", "decryt", "dest", "exclude", "extra_opts", "group", "keep_newer", "list_files", "mode", "owner", "remote_src", "selevel", "serole", "setype", "seuser", "src", "unsafe_writes", "validate_certs"]

class AptPkgMgr(BasePkgMgr):
    def __init__(self):
        pass

    def get_name(self):
        return "apt"

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):
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

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):

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

    def prepare(self, package_vars, calculated_package, task_vars, result, parent):

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
    'vagrant_plugin': VagrantPluginPkgMgr,
    'get_url': GetUrlPkgMgr,
    'unarchive': UnarchivePkgMgr
}

DEFAULT_PKG_MGR_VARS = ["name", "state"]
USE_TOP_LEVEL_AS_PKG_NAME = False


class ActionModule(ActionBase):


    def add_run(self, run, pkg_id=False, pkg_vars=False, pkg_mgr=False, task_msg="executing unspecified task"):

            # print("ignore: {}".format(run))
            self.runs.append(run)

            if "failed" in run.keys():
                run_failed = run["failed"]
            else:
                run_failed = False

            if run_failed:
                if pkg_id:
                    self.failed.append(pkg_id)
                self.overall_failed = True

            if "changed" in run.keys():
                changed = run["changed"]
            else:
                changed = False

            if "msg" in run.keys():
                run_msg = run['msg']
                self.msgs.append(run_msg)
            else:
                run_msg = None

            if "module_stderr" in run.keys():
                run_module_stderr = run['module_stderr']
            else:
                run_module_stderr = None

            if changed:
                self.overall_changed = True
                if pkg_id:
                    self.installed.append(pkg_id)
            elif not run_failed:
                if pkg_id:
                    self.skipped.append(pkg_id)

            if self.nsbl_env:
                if pkg_id:
                    output = {"item": "{} (using: {})".format(pkg_id, pkg_mgr)}
                else:
                    output = {"item": task_msg}

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


    def run(self, tmp=None, task_vars=None):
        ''' handler for template operations '''

        self.nsbl_env = os.environ.get("NSBL_ENVIRONMENT", False) == "true"

        self.runs = []
        self.msgs = []
        self.overall_changed = False
        self.overall_failed = False

        self.installed = []
        self.skipped = []
        self.failed = []

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
            if pkg_mgr == 'homebrew' and os_family == "Darwin":
                if calculated_package_platform.startswith("cask:"):
                    pkg_mgr = 'homebrew_cask'
                    calculated_package = calculated_package_platform[5:]
                else:
                    calculated_package = calculated_package_platform
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

        all_pkg_vars = pkg_mgr_obj.prepare(package[VARS_KEY], calculated_package, task_vars, result, parent=self)

        for pkg_id, pkg_vars in all_pkg_vars.items():

            if package[VARS_KEY].get("no_install", False):
                skipped.append(pkg_id)
                run = {"changed": False, "skipped": True,
                       "msg": "Package '{}' tagged with 'no_install', ignoring".format(pkg_id)}
                add_run(run, pkg_id, pkg_vars)
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

            filtered_pkg_vars = {}
            if keys:
                for key in keys:
                    if key in pkg_vars.keys():
                        filtered_pkg_vars[key] = pkg_vars[key]


            new_module_args.update(filtered_pkg_vars)
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

            self.add_run(run, pkg_id=pkg_id, pkg_vars=pkg_vars, pkg_mgr=pkg_mgr)

        if len(self.runs) == 1:
            return self.runs[0]
        else:
            msg = "Installed: {}, Skipped: {}, Failed: {}".format(self.installed, self.skipped, self.failed)
            runs_result = {"changed": self.overall_changed, "msg": msg, "failed": self.overall_failed, "runs": self.runs}
            return runs_result
