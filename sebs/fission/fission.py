import logging
import os
import shutil
import subprocess
import docker
import json
from time import sleep
from typing import Dict, Tuple, List
from sebs.faas.storage import PersistentStorage
from sebs.cache import Cache
from sebs.config import SeBSConfig
from sebs.faas.function import Function
from sebs.faas.system import System
from sebs.fission.fissionFunction import FissionFunction
from sebs.benchmark import Benchmark
from sebs.fission.config import FissionConfig
from sebs.fission.minio import Minio
from tools.fission_preparation import check_if_minikube_installed, run_minikube, check_if_k8s_installed, \
    check_if_helm_installed, stop_minikube


class Fission(System):
    language_image: str
    language_builder: str
    storage: Minio
    httpTriggerName: str
    functionName: str
    packageName: str
    envName: str
    shouldCallBuilder: bool = False
    _config: FissionConfig

    def __init__(
        self,
        sebs_config: SeBSConfig,
        config: FissionConfig,
        cache_client: Cache,
        docker_client: docker.client,
    ):
        super().__init__(sebs_config, cache_client, docker_client)
        self._added_functions: List[str] = []
        self._config = config

    @staticmethod
    def name():
        return "fission"

    @property
    def config(self) -> FissionConfig:
        return self._config

    @staticmethod
    def add_port_forwarding(port=5051):
        podName = (
            subprocess.run(
                f"kubectl --namespace fission get pod -l svc=router -o name".split(),
                stdout=subprocess.PIPE,
            )
            .stdout.decode("utf-8")
            .rstrip()
        )
        subprocess.Popen(
            f"kubectl --namespace fission port-forward {podName} {port}:8888".split(),
            stderr=subprocess.DEVNULL,
        )

    def shutdown(self) -> None:
        if self.config.shouldShutdown:
            if hasattr(self, "httpTriggerName"):
                subprocess.run(
                    f"fission httptrigger delete --name {self.httpTriggerName}".split()
                )
            if hasattr(self, "functionName"):
                subprocess.run(f"fission fn delete --name {self.functionName}".split())
            if hasattr(self, "packageName"):
                subprocess.run(f"fission package delete --name {self.packageName}".split())
            if hasattr(self, "envName"):
                subprocess.run(f"fission env delete --name {self.envName}".split())
            subprocess.run(f"minikube stop".split())
        self.storage.storage_container.kill()
        logging.info("Minio stopped")
<<<<<<< HEAD
        stop_minikube()

=======
        
>>>>>>> fix pr 7 comments
    def get_storage(self, replace_existing: bool = False) -> PersistentStorage:
        self.storage = Minio(self.docker_client)
        return self.storage

    def initialize(self, config: Dict[str, str] = None):
        if config is None:
            config = {}

        check_if_minikube_installed()
        check_if_k8s_installed()
        check_if_helm_installed()
        run_minikube()
        Fission.add_port_forwarding()
        sleep(5)

    def package_code(self, benchmark: Benchmark) -> Tuple[str, int]:

        benchmark.build()

        CONFIG_FILES = {
            "python": [
                "handler.py",
                "requirements.txt",
                ".python_packages",
                "build.sh",
            ],
            "nodejs": ["handler.js", "package.json", "node_modules"],
        }
        directory = benchmark.code_location
        package_config = CONFIG_FILES[benchmark.language_name]
        function_dir = os.path.join(directory, "function")
        os.makedirs(function_dir)
        minioConfig = open("./code/minioConfig.json", "w+")
        minioConfigJson = {
            "access_key": self.storage.access_key,
            "secret_key": self.storage.secret_key,
            "url": self.storage.url,
        }
        minioConfig.write(json.dumps(minioConfigJson))
        minioConfig.close()
        scriptPath = os.path.join(directory, "build.sh")
        self.shouldCallBuilder = True
        f = open(scriptPath, "w+")
        f.write(
            "#!/bin/sh\npip3 install -r ${SRC_PKG}/requirements.txt -t \
${SRC_PKG} && cp -r ${SRC_PKG} ${DEPLOY_PKG}"
        )
        f.close()
        subprocess.run(["chmod", "+x", scriptPath])
        for file in os.listdir(directory):
            if file not in package_config:
                file = os.path.join(directory, file)
                shutil.move(file, function_dir)
        os.chdir(directory)
        subprocess.run(
            "zip -r {}.zip ./".format(benchmark.benchmark).split(),
            stdout=subprocess.DEVNULL,
        )
        benchmark_archive = "{}.zip".format(
            os.path.join(directory, benchmark.benchmark)
        )
        logging.info("Created {} archive".format(benchmark_archive))
        bytes_size = os.path.getsize(benchmark_archive)
        return benchmark_archive, bytes_size

    def update_function(self, name: str, env_name: str, code_path: str):
        self.create_function(name, env_name, code_path)

    def create_env_if_needed(self, name: str, image: str, builder: str):
        self.envName = name
        try:
            fission_env_list = subprocess.run(
                "fission env list ".split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                f"grep {name}".split(),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                input=fission_env_list.stdout,
            )
            logging.info(f"Env {name} already exist")
        except subprocess.CalledProcessError:
            logging.info(f'Creating env for {name} using image "{image}".')
            try:
                subprocess.run(
                    f"fission env create --name {name} --image {image} \
                    --builder {builder}".split(),
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                logging.info(f"Creating env {name} failed. Retrying...")
                sleep(10)
                try:
                    subprocess.run(
                        f"fission env create --name {name} --image {image} \
                        --builder {builder}".split(),
                        check=True,
                        stdout=subprocess.DEVNULL,
                    )
                except subprocess.CalledProcessError:
                    self.storage.storage_container.kill()
                    logging.info("Minio stopped")
                    self.initialize()
                    self.create_env_if_needed(name, image, builder)

    def create_function(self, name: str, env_name: str, path: str):
        packageName = f"{name}-package"
        self.createPackage(packageName, path, env_name)
        self.createFunction(packageName, name)

    def createPackage(self, packageName: str, path: str, envName: str) -> None:
        logging.info(f"Deploying fission package...")
        self.packageName = packageName
        try:
            packages = subprocess.run(
                "fission package list".split(), stdout=subprocess.PIPE, check=True
            )
            subprocess.run(
                f"grep {packageName}".split(), check=True, input=packages.stdout, stdout=subprocess.DEVNULL
            )
            logging.info("Package already exist")
        except subprocess.CalledProcessError:
            process = f"fission package create --sourcearchive {path} \
            --name {packageName} --env {envName} --buildcmd ./build.sh"
            subprocess.run(process.split(), check=True)
            logging.info("Waiting for package build...")
            while True:
                try:
                    packageStatus = subprocess.run(
                        f"fission package info --name {packageName}".split(),
                        stdout=subprocess.PIPE,
                    )
                    subprocess.run(
                        f"grep succeeded".split(),
                        check=True,
                        input=packageStatus.stdout,
                        stderr=subprocess.DEVNULL,
                    )
                    break
                except subprocess.CalledProcessError:
                    if "failed" in packageStatus.stdout.decode("utf-8"):
                        logging.error("Build package failed")
                        raise Exception("Build package failed")
                    sleep(3)
                    continue
            logging.info("Package ready")

    def deletePackage(self, packageName: str) -> None:
        logging.info(f"Deleting fission package...")
        subprocess.run(f"fission package delete --name {packageName}".split())

    def createFunction(self, packageName: str, name: str) -> None:
        triggerName = f"{name}-trigger"
        self.functionName = name
        self.httpTriggerName = triggerName
        logging.info(f"Deploying fission function...")
        try:
            triggers = subprocess.run(
                f"fission fn list".split(), stdout=subprocess.PIPE, check=True
            )
            subprocess.run(
                f"grep {name}".split(), check=True, input=triggers.stdout, stdout=subprocess.DEVNULL
            )
            logging.info(f"Function {name} already exist")
        except subprocess.CalledProcessError:
            subprocess.run(
                f"fission fn create --name {name} --pkg {packageName} \
                    --entrypoint handler.handler --env {self.envName}".split(),
                check=True,
            )
        try:
            triggers = subprocess.run(
                f"fission httptrigger list".split(), stdout=subprocess.PIPE, check=True
            )
            subprocess.run(
                f"grep {triggerName}".split(), check=True, input=triggers.stdout, stdout=subprocess.DEVNULL
            )
            logging.info(f"Trigger {triggerName} already exist")
        except subprocess.CalledProcessError:
            subprocess.run(
                f"fission httptrigger create --url /benchmark --method POST \
                --name {triggerName} --function {name}".split(),
                check=True,
            )

    def deleteFunction(self, name: str) -> None:
        logging.info(f"Deleting fission function...")
        subprocess.run(f"fission fn delete --name {name}".split())

    def get_function(self, code_package: Benchmark) -> Function:
        self.language_image = self.system_config.benchmark_base_images(self.name(), code_package.language_name)["env"]
        self.language_builder = self.system_config.benchmark_base_images(self.name(), code_package.language_name)["builder"]
        path, size = self.package_code(code_package)
        benchmark = code_package.benchmark.replace(".", "-")
        language = code_package.language_name
        language_runtime = code_package.language_version
        timeout = code_package.benchmark_config.timeout
        memory = code_package.benchmark_config.memory
        if code_package.is_cached and code_package.is_cached_valid:
            func_name = code_package.cached_config["name"]
            code_location = os.path.join(
                code_package._cache_client.cache_dir,
                code_package._cached_config["code"],
            )
            logging.info(
                "Using cached function {fname} in {loc}".format(
                    fname=func_name, loc=code_location
                )
            )
            self.create_env_if_needed(
                language,
                self.language_image,
                self.language_builder,
            )
            self.update_function(func_name, code_package.language_name, path)
            return FissionFunction(func_name)
        elif code_package.is_cached:
            func_name = code_package.cached_config["name"]
            code_location = code_package.code_location
            self.create_env_if_needed(
                language,
                self.language_image,
                self.language_builder,
            )
            self.update_function(func_name, code_package.language_name, path)
            cached_cfg = code_package.cached_config
            cached_cfg["code_size"] = size
            cached_cfg["timeout"] = timeout
            cached_cfg["memory"] = memory
            cached_cfg["hash"] = code_package.hash
            self.cache_client.update_function(
                self.name(),
                benchmark.replace("-", "."),
                code_package.language_name,
                path,
                cached_cfg,
            )
            code_package.query_cache()
            logging.info(
                "Updating cached function {fname} in {loc}".format(
                    fname=func_name, loc=code_location
                )
            )
            return FissionFunction(func_name)
        else:
            code_location = code_package.benchmark_path
            func_name = "{}-{}-{}".format(benchmark, language, memory)
            self.create_env_if_needed(
                language,
                self.language_image,
                self.language_builder,
            )
            self.create_function(func_name, language, path)
            self.cache_client.add_function(
                deployment=self.name(),
                benchmark=benchmark.replace("-", "."),
                language=language,
                code_package=path,
                language_config={
                    "name": func_name,
                    "code_size": size,
                    "runtime": language_runtime,
                    "memory": memory,
                    "timeout": timeout,
                    "hash": code_package.hash,
                },
                storage_config={
                    "buckets": {
                        "input": self.storage.input_buckets,
                        "output": self.storage.output_buckets,
                    }
                },
            )
            code_package.query_cache()
            return FissionFunction(func_name)
