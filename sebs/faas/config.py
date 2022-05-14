from __future__ import annotations

from abc import ABC
from abc import abstractmethod

import uuid

from sebs.cache import Cache
from sebs.utils import has_platform, LoggingBase, LoggingHandlers

"""
    Credentials for FaaS system used to authorize operations on functions
    and other resources.

    The order of credentials initialization:
    1. Load credentials from cache.
    2. If any new vaues are provided in the config, they override cache values.
    3. If nothing is provided, initialize using environmental variables.
    4. If no information is provided, then failure is reported.
"""


class Credentials(ABC, LoggingBase):
    def __init__(self):
        super().__init__()

    """
        Create credentials instance from user config and cached values.
    """

    @staticmethod
    @abstractmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> Credentials:
        pass

    """
        Serialize to JSON for storage in cache.
    """

    @abstractmethod
    def serialize(self) -> dict:
        pass


"""
    Class grouping resources allocated at the FaaS system to execute functions
    and deploy various services. Examples might include IAM roles and API gateways
    for HTTP triggers.

    Storage resources are handled seperately.
"""


class Resources(ABC, LoggingBase):
    def __init__(self):
        super().__init__()

    """
        Create credentials instance from user config and cached values.
    """

    @staticmethod
    @abstractmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> Resources:
        pass

    """
        Serialize to JSON for storage in cache.
    """

    @abstractmethod
    def serialize(self) -> dict:
        pass


"""
    FaaS system config defining cloud region (if necessary), credentials and
    resources allocated.
"""


class Config(ABC, LoggingBase):
    def __init__(self, name: str):
        super().__init__()
        self._resources_id = ""
        self._region = ""
        self._name = name

    @property
    def region(self) -> str:
        return self._region

    @property
    @abstractmethod
    def credentials(self) -> Credentials:
        pass

    @property
    @abstractmethod
    def resources(self) -> Resources:
        pass

    @property
    def resources_id(self) -> str:
        return self._resources_id

    @staticmethod
    @abstractmethod
    def initialize(cfg: Config, dct: dict):
        cfg._region = dct["region"]
        if "resources_id" in dct:
            cfg._resources_id = dct["resources_id"]
        else:
            cfg._resources_id = str(uuid.uuid1())[0:8]
            cfg.logging.info(
                f"Generating unique resource name for " f"the experiments: {cfg._resources_id}"
            )

    @staticmethod
    @abstractmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> Config:
        from sebs.local.config import LocalConfig

        name = config["name"]
        implementations = {"local": LocalConfig.deserialize}
        if has_platform("aws"):
            from sebs.aws.config import AWSConfig

            implementations["aws"] = AWSConfig.deserialize
        if has_platform("azure"):
            from sebs.azure.config import AzureConfig

            implementations["azure"] = AzureConfig.deserialize
        if has_platform("gcp"):
            from sebs.gcp.config import GCPConfig

            implementations["gcp"] = GCPConfig.deserialize
        if has_platform("openwhisk"):
            from sebs.openwhisk.config import OpenWhiskConfig

            implementations["openwhisk"] = OpenWhiskConfig.deserialize
        func = implementations.get(name)
        assert func, "Unknown config type!"
        return func(config[name] if name in config else config, cache, handlers)

    def serialize(self) -> dict:
        return {"name": self._name, "region": self._region, "resources_id": self.resources_id}

    @abstractmethod
    def update_cache(self, cache: Cache):
        cache.update_config(val=self.region, keys=[self._name, "region"])
        cache.update_config(val=self.resources_id, keys=[self._name, "resources_id"])
