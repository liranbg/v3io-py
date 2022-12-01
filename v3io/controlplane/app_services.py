import typing
import pydantic


class _Base(pydantic.BaseModel):
    class Config:
        # be forward compatible
        extra = "allow"
        orm_mode = True
        use_enum_values = True


class _CredentialsSpec(_Base):
    username: str


class _SystemResources(_Base):
    cpu: typing.Optional[str]
    memory: typing.Optional[str]
    nvidia_gpu: typing.Optional[str]


class _ResourcesSpec(_Base):
    limits: typing.Optional[_SystemResources]
    requests: _SystemResources


class _ScaleToZeroSpec(_Base):
    # TODO: add all fields
    pass


class _PvcSpec(_Base):
    mounts: typing.Dict[str, str]


class _SecurityContextSpec(_Base):
    run_as_user: str
    run_as_group: str
    fs_group: str
    supplemental_groups: typing.List[str]
    run_as_non_root: bool


class _AdvancedSpec(_Base):
    node_selector: typing.Optional[typing.Dict[str, str]]
    priority_class_name: str


class _Url(_Base):
    kind: str
    url: str


class _Meta(_Base):
    labels: typing.Optional[typing.Dict[str, str]]
    # TODO: convert annotations entries to dictionary
    # annotations: typing.Optional[typing.Dict[str, str]]


class _StatusErrorInfo(_Base):
    description: str
    timestamp: str


class _Status(_Base):
    state: str
    urls: typing.Optional[typing.List[_Url]]
    api_urls: typing.Optional[typing.List[_Url]]
    internal_api_urls: typing.Optional[typing.List[_Url]]
    version: str
    last_error: typing.Optional[str]
    display_name: typing.Optional[str]
    error_info: typing.Optional[_StatusErrorInfo]
    # TODO: add all fields


class _HomeContainer(_Base):
    container: str
    prefix: str


class _SSHServerSpec(_Base):
    force_key_regeneration: bool
    # TODO: add all fields


class JupyterSpec(_Base):
    image_name: str

    # optional fileds
    spark_name: typing.Optional[str]
    presto_name: typing.Optional[str]
    framesd: typing.Optional[str]
    home_spec: typing.Optional[_HomeContainer]
    extra_environment_vars: typing.Optional[typing.Dict[str, str]]
    demos_datasets_archive_address: typing.Optional[str]
    docker_registry_name: typing.Optional[str]
    ssh_enabled: typing.Optional[bool]
    ssh_server: typing.Optional[_SSHServerSpec]


class _AppServiceSpecFactory:
    @staticmethod
    def create(app_service_spec) -> str:
        if app_service_spec is JupyterSpec:
            return "jupyter"
        else:
            raise Exception("Unknown app service spec type")


class AppServiceSpec(_Base):
    name: str
    kind: str

    # optional fileds
    owner: typing.Optional[str]
    display_name: typing.Optional[str]
    description: typing.Optional[str]
    credentials: typing.Optional[_CredentialsSpec]
    resources: typing.Optional[_ResourcesSpec]
    target_cpu: typing.Optional[int]
    max_replicas: typing.Optional[int]
    min_replicas: typing.Optional[int]
    enabled: typing.Optional[bool]
    avatar: typing.Optional[str]
    mark_for_restart: typing.Optional[bool]
    mark_as_changed: typing.Optional[bool]
    visible_to_all: typing.Optional[bool]
    scale_to_zero: typing.Optional[_ScaleToZeroSpec]
    pvc: typing.Optional[_PvcSpec]
    desired_state: typing.Optional[str]
    authentication_mode: typing.Optional[str]
    security_context: typing.Optional[_SecurityContextSpec]
    persistency_mode: typing.Optional[str]
    advanced: typing.Optional[_AdvancedSpec]

    # TODO: change alias to be kind value after initialization
    service_spec: typing.Any = pydantic.Field(alias="jupyter")

    def __init__(self, **kwargs):
        if "service_spec" in kwargs:
            kwargs["kind"] = _AppServiceSpecFactory.create(type(kwargs["service_spec"]))
        super().__init__(**kwargs)

    class Config(pydantic.BaseConfig):
        allow_population_by_field_name = True


class AppServiceBase(_Base):
    spec: AppServiceSpec
    meta: typing.Optional[_Meta]
    status: typing.Optional[_Status]
