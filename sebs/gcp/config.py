import os
from typing import cast

from sebs.cache import Cache
from sebs.faas.config import Config, Credentials, Resources
from sebs.utils import LoggingHandlers

# FIXME: Replace type hints for static generators after migration to 3.7
# https://stackoverflow.com/questions/33533148/how-do-i-specify-that-the-return-type-of-a-method-is-the-same-as-the-class-itsel

"""
    Credentials for FaaS system used to authorize operations on functions
    and other resources.

    The order of credentials initialization:
    1. Load credentials from cache.
    2. If any new vaues are provided in the config, they override cache values.
    3. If nothing is provided, initialize using environmental variables.
    4. If no information is provided, then failure is reported.
"""


class GCPCredentials(Credentials):
    _gcp_credentials: str

    def __init__(self, gcp_credentials: str):
        self._gcp_credentials = gcp_credentials

    @property
    def gcp_credentials(self) -> str:
        return self._gcp_credentials

    @staticmethod
    def initialize(gcp_credentials: str) -> Credentials:
        return GCPCredentials(gcp_credentials)

    @staticmethod
    def deserialize(
        config: dict, cache: Cache, handlers: LoggingHandlers
    ) -> Credentials:
        cached_config = cache.get_config("gcp")
        ret: GCPCredentials
        if cached_config and "credentials" in cached_config:
            ret = cast(
                GCPCredentials, GCPCredentials.initialize(cached_config["credentials"])
            )
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ret.gcp_credentials
            ret.logging_handlers = handlers
            ret.logging.info("Using cached credentials for GCP")
        else:
            # Check for new config
            if "credentials" in config:
                ret = cast(
                    GCPCredentials, GCPCredentials.initialize(config["credentials"])
                )
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ret.gcp_credentials
            elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                ret = GCPCredentials(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
                cache.update_config(
                    val=ret.gcp_credentials, keys=["gcp", "secrets", "gcp_credentials"]
                )
            else:
                raise RuntimeError("GCP login credentials are missing!")
            ret.logging_handlers = handlers
            ret.logging.info("No cached credentials for GCP found, initialize!")
        return ret

    """
        Serialize to JSON for storage in cache.
    """

    def serialize(self) -> dict:
        out = {"gcp_credentials": self.gcp_credentials}
        return out


"""
    Class grouping resources allocated at the FaaS system to execute functions
    and deploy various services. Examples might include IAM roles and API gateways
    for HTTP triggers.

    Storage resources are handled seperately.
"""


class GCPResources(Resources):
    def __init__(self, project_name: str, region: str):
        self._project_name = project_name
        self._region = region

    @property
    def project_name(self):
        return self._project_name

    @property
    def region(self):
        return self.region

    @staticmethod
    def initialize(dct: dict) -> Resources:
        return GCPResources(
            dct["project_name"] if "project_name" in dct else "",
            dct["region"] if "region" in dct else "",
        )

    """
        Serialize to JSON for storage in cache.
    """

    def serialize(self) -> dict:
        out = {"project_name": self._project_name, "region": self._region}
        return out

    @staticmethod
    def deserialize(
        config: dict, cache: Cache, handlers: LoggingHandlers
    ) -> "Resources":
        cached_config = cache.get_config("gcp")
        ret: GCPResources
        if cached_config and "resources" in cached_config:
            ret = cast(
                GCPResources, GCPResources.initialize(cached_config["resources"])
            )
            ret.logging_handlers = handlers
            ret.logging.info("Using cached resources for AWS")
        else:
            if "resources" in config:
                ret = cast(GCPResources, GCPResources.initialize(config["resources"]))
                ret.logging_handlers = handlers
                ret.logging.info(
                    "No cached resources for GCP found, using user configuration."
                )
            else:
                ret = GCPResources(project_name="", region="")
                ret.logging_handlers = handlers
                ret.logging.info("No resources for GCP found, initialize!")
        return ret


"""
    FaaS system config defining cloud region (if necessary), credentials and
    resources allocated.
"""


class GCPConfig(Config):

    _project_name: str

    def __init__(self, credentials: GCPCredentials, resources: GCPResources):
        self._credentials = credentials
        self._resources = resources

    @property
    def region(self) -> str:
        return self._region

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def credentials(self) -> GCPCredentials:
        return self._credentials

    @property
    def resources(self) -> GCPResources:
        return self._resources

    @staticmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> "Config":
        cached_config = cache.get_config("gcp")
        credentials = cast(
            GCPCredentials, GCPCredentials.deserialize(config, cache, handlers)
        )
        resources = cast(
            GCPResources, GCPResources.deserialize(config, cache, handlers)
        )
        config_obj = GCPConfig(credentials, resources)
        config_obj.logging_handlers = handlers
        if cached_config:
            config_obj.logging.info("Using cached config for GCP")
            GCPConfig.initialize(config_obj, cached_config)
        else:
            config_obj.logging.info("Using user-provided config for GCP")
            GCPConfig.initialize(config_obj, config)
            cache.update_config(val=config_obj.region, keys=["gcp", "region"])
            cache.update_config(
                val=config_obj.project_name, keys=["gcp", "project_name"]
            )

        return config_obj

    @staticmethod
    def initialize(cfg: Config, dct: dict):
        config = cast(GCPConfig, cfg)
        config._project_name = dct["project_name"]
        config._region = dct["region"]

    def serialize(self) -> dict:
        out = {
            "credentials": self._credentials.serialize(),
            "resources": self._resources.serialize(),
        }
        return out
