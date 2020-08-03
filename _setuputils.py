import os.path
import sys
import sysconfig
from distutils import sysconfig as dist_sysconfig

def get_include_dirs():
    dist_inc_dir = os.path.abspath(dist_sysconfig.get_python_inc())
    sys_inc_dir = os.path.abspath(sysconfig.get_path("include"))
    venv_include_dir = os.path.join(
        sys.prefix, 'include', 'site',
        'python' + sysconfig.get_python_version()
    )
    venv_include_dir = os.path.abspath(venv_include_dir)
    return [dist_inc_dir, sys_inc_dir, venv_include_dir]
