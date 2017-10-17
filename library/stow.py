#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: stow
short_description: Manage links to dotfiles
'''

from distutils.spawn import find_executable

import os
from ansible.module_utils.basic import AnsibleModule

try:
    set
except NameError:
    from sets import Set as set

IGNORE_STRING = "freckle"

POTENTIAL_STOW_PATHS = [
    os.path.expanduser("~/.local/opt/conda/bin"),
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.freckles/opt/conda/bin"),
    os.path.expanduser("~/miniconda3/bin"),
    os.path.expanduser("~/anaconda/bin")
]


def get_stow_bin(module):
    stow_bin = find_executable('stow')
    if not stow_bin:
        for path in POTENTIAL_STOW_PATHS:
            if os.path.isfile(os.path.join(path, 'stow')):
                stow_bin = os.path.join(path, 'stow')

    if not stow_bin:
        module.fail_json(msg="Could not find stow executable.")

    return stow_bin


def stow(module, stow_version):
    params = module.params

    # state = params['state']
    name = params['name']
    source_dir = os.path.expanduser(params['source_dir'])
    target_dir = os.path.expanduser(params['target_dir'])
    delete_conflicts = params['delete_conflicts']
    unstow = params['unstow']

    if stow_version.startswith("1") or stow_version.startswith("2.0"):
        ignore_parameter = ""
    else:
        ignore_parameter = "--ignore={}".format(IGNORE_STRING)

    if unstow:
        cmd = "{} -v 2 {} -d {} -t {} -D {}".format(get_stow_bin(module), ignore_parameter, source_dir, target_dir, name)
    else:
        cmd = "{} -v 2 {} -d {} -t {} -S {}".format(get_stow_bin(module), ignore_parameter, source_dir, target_dir, name)

    rc, stdout, stderr = module.run_command(cmd, check_rc=False)

    if unstow:
        if rc == 0:
            changed = False
            if "UNLINK" in stderr:
                changed = True
            module.exit_json(changed=changed, stderr=stderr)
        else:
            module.fail_json(msg="failed to unstow ( {} ) {}: {}".format(cmd, name, stderr))
    else:
        if rc == 0:
            changed = False
            if "LINK" in stderr:
                changed = True
            module.exit_json(changed=changed, stderr=stderr)
        else:
            if not delete_conflicts:
                module.fail_json(msg="failed to stow ( {} ) {}: {}".format(cmd, name, stderr))
            else:
                conflict_files = set()
                for line in stderr.split("\n"):
                    conflict_file = None
                    if not "neither a link nor a directory" in line:
                        continue
                    conflict_file = line.split()[-1]
                    conflict_files.add(conflict_file)

                for conflict_file in conflict_files:

                    cf_path = os.path.join(target_dir, conflict_file)
                    if os.path.exists(cf_path) and os.path.isfile(cf_path):
                        os.remove(cf_path)

                rc, stdout, stderr = module.run_command(cmd, check_rc=False)
                if rc == 0:
                    changed = False
                    if "LINK" in stderr:
                        changed = True

                    module.exit_json(changed=changed, stderr=stderr,
                                     msg="Deleted existing files: {}".format(list(conflict_files)))
                else:
                    module.fail_json(msg="failed to stow ( {} ) {}: {}".format(cmd, name, stderr))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # state=dict(default='present', choices=['present', 'absent']),
            name=dict(required=True),
            source_dir=dict(required=True),
            target_dir=dict(required=True),
            delete_conflicts=dict(required=False, default=False, type='bool'),
            use=dict(default='stow'),
            unstow=dict(required=False, default=False, type='bool')
        )
    )

    cmd = "{} --version".format(get_stow_bin(module))
    rc, stdout, stderr = module.run_command(cmd, check_rc=False)

    if rc == 0:
        stow_version = stdout.split()[-1]
        # module.exit_json(changed=True, version=stow_version)
    else:
        module.fail_json("Can't execute/find 'stow': {}".format(stderr))

    stow(module, stow_version)


if __name__ == '__main__':
    main()
