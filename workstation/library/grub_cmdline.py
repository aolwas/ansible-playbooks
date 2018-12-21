#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017 Objectif-Libre

import datetime
import os
import re
import subprocess
import shutil
import datetime

DOCUMENTATION = """
---
module: grub_cmdline
short_description: modify GRUB_CMDLINE_LINUX in grub2 configuration
description:
 - This module allows the manipulation of the grub2 configuration
options:
  state:
    required: false
    choices: [ present, absent ]
    default: "present"
    aliases: []
    description:
      - Whether the setting should be added/modified or removed

  option:
    required: true
    aliases: []
    description:
      - option to add/update/remove

  value:
    required: false
    aliases: []
    description:
      - option value.
"""

class GrubModifier(object):

    def __init__(self, module):
        self._params = module.params

    def _options_tolist(self, options):
        t = re.findall(r'([^\s]*=\$\([^\(]*\)|\$\([^\(]*\)|[^\s]*)', options)
        r = []
        allow_multi = [ 'rd.lvm.lv' ]
        for v in t:
            if v != '':
                if v.find('$(') >= 0 and v.find('$(') < v.find("="):
                    akey = v
                    aval = ""
                else:
                    akey = v.partition("=")[0]
                    aval = v.partition("=")[2]
            
                replaced = False
                if akey not in allow_multi and akey[:1] != '$':
                    for i, el in enumerate(r):
                        if el[0] == akey and el[0]:
                            r[i] = (akey, aval)
                            replaced = True
                if replaced is not True:
                    r.append((akey, aval))
        return r

    def _options_tostring(self, options):
        t = []
        for key, val in options:
            if val == '' or val is None:
                t.append(key)
            else:
                t.append('%s=%s' % (key, val))
        t = ' '.join(t)
        return t


    def _del_option(self, options):
        t = self._options_tolist(options)
        t = [ (key, val) for key, val in t if key != self._params["option"] ]
        return self._options_tostring(t)

    def _set_option(self, options):
        t = self._options_tolist(options)
        replaced = False
        for i, el in enumerate(t):
            if el[0] == self._params["option"]:
                t[i] = (el[0], self._params["value"])
                replaced = True
        if replaced is not True:
            t.append((self._params["option"], self._params["value"]))
        return self._options_tostring(t)

    def _refresh_menu(self):
        p = subprocess.Popen(["grub-mkconfig", "-o", "/boot/grub/grub.cfg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err != 0:
            return True
        else:
            return False

    def _backup_config(self):
        try:
            shutil.copy("/etc/default/grub", "/etc/default/grub.%s" % datetime.datetime.now().strftime("%y%m%d%H%M"))
            return True
        except:
            return False

    def _save_config(self, contents):
        try: 
            with open("/etc/default/grub", "w") as f:
                f.write(contents)
            return True
        except:
            return False

    def run(self):
        if not (os.path.isdir("/etc/default") and os.path.isfile("/etc/default/grub")):
            return ( 1, False, "/etc/default/grub was not found")

        changed = False
        newfile = ""
        oldfile = ""
        with open("/etc/default/grub", "r") as f:
            oldfile = f.read()
        
        for line in oldfile.splitlines():
            if re.compile(r'^\s*GRUB_CMDLINE_LINUX=').search(line) is not None:
                t = line.partition("=")[2].strip()
                if t[:1] == '"' and t[-1:] == '"':
                    t = t[1:-1]
                if self._params["state"] == "present":
                    t = self._set_option(t)
                else:
                    t = self._del_option(t)
                line = re.sub(r'(\s*GRUB_CMDLINE_LINUX=).*$', r'\1"%s"' % t, line)
            newfile = newfile + line + "\n"
        if newfile != oldfile:
            if self._backup_config() is not True:
                return ( 1, False, "/etc/default/grub could not be backed up.")
            if self._save_config(newfile) is not True:
                return ( 1, False, "/etc/default/grub could not be saved" )
            changed=True
            if self._refresh_menu() is not True:
                return ( 1, changed, "/boot/grub2/grub.cfg could not be refreshed")

        return ( 0, changed, "")

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state     = dict(default = 'present', choices = ['present', 'absent'], type = 'str'),
            option    = dict(required = True, default = None, type = 'str'),
            value     = dict(default = None, type = 'str'),
        ),
        supports_check_mode = False
    )

    grub = GrubModifier(module)

    rc = None
    out = ''
    err  = ''
    result = {}
    result['state'] = module.params["state"]
    changed = False
    msg = ""

    result['option'] = module.params["option"]
    (rc, changed, msg) = grub.run()
    if rc != 0:
        module.fail_json(option=module.params["option"], msg=msg, rc=rc)

    module.exit_json(changed=changed, msg=msg, **result)

# import module snippets
from ansible.module_utils.basic import *
main()