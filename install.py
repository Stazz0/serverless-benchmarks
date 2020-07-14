#!/usr/bin/env python3

import argparse
import os
import subprocess

from tools.fission_preparation import check_if_minikube_installed, check_if_k8s_installed, check_if_helm_installed, \
    check_if_fission_cli_installed, install_fission_cli

parser = argparse.ArgumentParser(description="Install SeBS and dependencies.")
parser.add_argument('--venv', metavar='DIR', type=str, default="python-venv", help='destination of local Python virtual environment')
parser.add_argument('--python-path', metavar='DIR', type=str, default="python3", help='Path to local Python installation.')
for deployment in ["aws", "azure", "gcp", "openwhisk"]:
    parser.add_argument(f"--{deployment}", action="store_const", const=True, dest=deployment)
    parser.add_argument(f"--no-{deployment}", action="store_const", const=False, default=True, dest=deployment)
for deployment in ["local"]:
    parser.add_argument(f"--{deployment}", action="store_const", default=True, const=True, dest=deployment)
    parser.add_argument(f"--no-{deployment}", action="store_const", const=False, dest=deployment)
parser.add_argument("--with-pypapi", action="store_true")
parser.add_argument("--with-fission", action="store_true")
args = parser.parse_args()

<<<<<<< HEAD
def execute(cmd, cwd=None):
=======

def execute(cmd):
>>>>>>> [feature_fission] fission installation through install.py
    ret = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=cwd
    )
    if ret.returncode:
        raise RuntimeError(
            "Running {} failed!\n Output: {}".format(cmd, ret.stdout.decode("utf-8"))
        )
    return ret.stdout.decode("utf-8")

<<<<<<< HEAD
env_dir=args.venv

if not os.path.exists(env_dir):
    print("Creating Python virtualenv at {}".format(env_dir))
    execute(f"{args.python_path} -mvenv {env_dir}")
    execute(". {}/bin/activate && pip install --upgrade pip".format(env_dir))
else:
    print("Using existing Python virtualenv at {}".format(env_dir))

print("Install Python dependencies with pip")
execute(". {}/bin/activate && pip3 install -r requirements.txt --upgrade".format(env_dir))

if args.aws:
    print("Install Python dependencies for AWS")
    execute(". {}/bin/activate && pip3 install -r requirements.aws.txt".format(env_dir))
flag = "TRUE" if args.aws else "FALSE"
execute(f'echo "export SEBS_WITH_AWS={flag}" >> {env_dir}/bin/activate')
execute(f'echo "unset SEBS_WITH_AWS" >> {env_dir}/bin/deactivate')

if args.azure:
    print("Install Python dependencies for Azure")
    execute(". {}/bin/activate && pip3 install -r requirements.azure.txt".format(env_dir))
flag = "TRUE" if args.azure else "FALSE"
execute(f'echo "export SEBS_WITH_AZURE={flag}" >> {env_dir}/bin/activate')
execute(f'echo "unset SEBS_WITH_AZURE" >> {env_dir}/bin/deactivate')

if args.gcp:
    print("Install Python dependencies for GCP")
    execute(". {}/bin/activate && pip3 install -r requirements.gcp.txt".format(env_dir))
flag = "TRUE" if args.gcp else "FALSE"
execute(f'echo "export SEBS_WITH_GCP={flag}" >> {env_dir}/bin/activate')
execute(f'echo "unset SEBS_WITH_GCP" >> {env_dir}/bin/deactivate')

flag = "TRUE" if args.openwhisk else "FALSE"
execute(f'echo "export SEBS_WITH_OPENWHISK={flag}" >> {env_dir}/bin/activate')
execute(f'echo "unset SEBS_WITH_OPENWHISK" >> {env_dir}/bin/deactivate')

if args.local:
    print("Install Python dependencies for local")
    execute(". {}/bin/activate && pip3 install -r requirements.local.txt".format(env_dir))
    print("Initialize Docker image for local storage.")
    execute("docker pull minio/minio:latest")

# One of the installed dependencies causes a downgrade, which in turns breaks static typing.
print("Update typing-extensions (resolving bug with mypy)")
execute(". {}/bin/activate && pip3 install typing-extensions --upgrade".format(env_dir))

print("Download benchmarks data")
try:
    execute("git submodule update --init --recursive")
except RuntimeError as error:
    msg = str(error)
    # we're not in a git repository
    if "not a git repository" in msg:
        data_dir = "benchmarks-data"
        # not empty - already cloned, so only update
        if any(os.scandir(data_dir)):
            execute(f"git pull", cwd=data_dir)
        # clone
        else:
            execute(f"git clone https://github.com/spcl/serverless-benchmarks-data.git {data_dir}")
    else:
        raise error
=======
# env_dir="sebs-virtualenv"
#
# print("Creating Python virtualenv at {}".format(env_dir))
# execute("python3 -mvenv {}".format(env_dir))
#
# print("Install Python dependencies with pip")
# execute(". {}/bin/activate && pip3 install -r requirements.txt".format(env_dir))
#
# print("Configure mypy extensions")
# execute(". {}/bin/activate && mypy_boto3".format(env_dir))
#
# print("Initialize git submodules")
# execute("git submodule update --init --recursive")

>>>>>>> [feature_fission] fission installation through install.py

if args.with_pypapi:
    print("Build and install pypapi")
    cur_dir = os.getcwd()
    os.chdir(os.path.join("third-party", "pypapi"))
    execute("git checkout low_api_overflow")
    execute("pip3 install -r requirements.txt")
    execute("python3 setup.py build")
    execute("python3 pypapi/papi_build.py")
    os.chdir(cur_dir)

<<<<<<< HEAD
=======
if args.with_fission:
    check_if_minikube_installed()
    check_if_k8s_installed()
    check_if_helm_installed()
    try:
        check_if_fission_cli_installed(throws_error=True)
    except subprocess.CalledProcessError:
        install_fission_cli()
        check_if_fission_cli_installed()
>>>>>>> [feature_fission] fission installation through install.py
