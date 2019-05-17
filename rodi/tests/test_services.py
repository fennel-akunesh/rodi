import pytest
from rodi import (
    Container,
    Services,
    CircularDependencyException,
    OverridingServiceException,
    UnsupportedUnionTypeException,
    MissingTypeException,
    GetServiceContext,
    to_standard_param_name
)
from rodi.tests.examples import (
    ICatsRepository,
    GetCatRequestHandler,
    CatsController,
    IRequestContext,
    RequestContext,
    Cat,
    Foo,
    ServiceSettings,
    InMemoryCatsRepository,
    FooDBContext,
    FooDBCatsRepository,
    IdGetter,
    A,
    B,
    C,
    P,
    Q,
    R,
    W,
    X,
    Y,
    Z,
    UfoOne,
    UfoTwo,
    UfoThree,
    UfoFour,
    Ko,
    Ok,
    PrecedenceOfTypeHintsOverNames,
    Jing,
    Jang,
    ICircle,
    Circle,
    Shape,
    TrickyCircle,
    TypeWithOptional,
    ResolveThisByParameterName,
    IByParamName,
    FooByParamName
)


def arrange_cats_example():
    container = Container()
    container.add_transient(ICatsRepository, FooDBCatsRepository)
    container.add_scoped(IRequestContext, RequestContext)
    container.add_exact_transient(GetCatRequestHandler)
    container.add_exact_transient(CatsController)
    container.add_instance(ServiceSettings('foodb:example;something;'))
    container.add_exact_transient(FooDBContext)
    return container


@pytest.mark.parametrize('value,expected_result', (
    ('CamelCase', 'camel_case'),
    ('HTTPResponse', 'http_response'),
    ('ICatsRepository', 'icats_repository'),
    ('Cat', 'cat'),
    ('UFO', 'ufo'),
))
def test_standard_param_name(value, expected_result):
    snaked = to_standard_param_name(value)
    assert snaked == expected_result


def test_singleton_by_instance():
    container = Container()
    container.add_instance(Cat('Celine'))
    provider = container.build_provider()

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == "Celine"


def test_transient_by_type_without_parameters():
    container = Container()
    container.add_transient(ICatsRepository, InMemoryCatsRepository)
    provider = container.build_provider()
    cats_repo = provider.get(ICatsRepository)

    assert isinstance(cats_repo, InMemoryCatsRepository)
    other_cats_repo = provider.get(ICatsRepository)

    assert isinstance(other_cats_repo, InMemoryCatsRepository)
    assert cats_repo is not other_cats_repo


def test_transient_by_type_with_parameters():
    container = Container()
    container.add_transient(ICatsRepository, FooDBCatsRepository)

    # NB:
    container.add_instance(ServiceSettings('foodb:example;something;'))
    container.add_exact_transient(FooDBContext)
    provider = container.build_provider()

    cats_repo = provider.get(ICatsRepository)

    assert isinstance(cats_repo, FooDBCatsRepository)
    assert isinstance(cats_repo.context, FooDBContext)
    assert isinstance(cats_repo.context.settings, ServiceSettings)
    assert cats_repo.context.connection_string == 'foodb:example;something;'


def test_raises_for_overriding_service():
    container = Container()
    container.add_transient(ICircle, Circle)

    with pytest.raises(OverridingServiceException) as context:
        container.add_singleton(ICircle, Circle)

    assert 'ICircle' in str(context.value)

    with pytest.raises(OverridingServiceException) as context:
        container.add_transient(ICircle, Circle)

    assert 'ICircle' in str(context.value)

    with pytest.raises(OverridingServiceException) as context:
        container.add_scoped(ICircle, Circle)

    assert 'ICircle' in str(context.value)


def test_raises_for_circular_dependency():
    container = Container()
    container.add_transient(ICircle, Circle)

    with pytest.raises(CircularDependencyException) as context:
        container.build_provider()

    assert 'Circle' in str(context.value)


def test_raises_for_circular_dependency_with_dynamic_resolver():
    container = Container()
    container.add_exact_transient(Jing)
    container.add_exact_transient(Jang)

    with pytest.raises(CircularDependencyException):
        container.build_provider()


def test_raises_for_deep_circular_dependency_with_dynamic_resolver():
    container = Container()
    container.add_exact_transient(W)
    container.add_exact_transient(X)
    container.add_exact_transient(Y)
    container.add_exact_transient(Z)

    with pytest.raises(CircularDependencyException):
        container.build_provider()


def test_does_not_raise_for_deep_circular_dependency_with_one_factory():
    container = Container()
    container.add_exact_transient(W)
    container.add_exact_transient(X)
    container.add_exact_transient(Y)

    def z_factory(_) -> Z:
        return Z(None)

    container.add_transient_by_factory(z_factory)

    provider = container.build_provider()

    w = provider.get(W)

    assert isinstance(w, W)
    assert isinstance(w.x, X)
    assert isinstance(w.x.y, Y)
    assert isinstance(w.x.y.z, Z)
    assert w.x.y.z.w is None


def test_circular_dependency_is_supported_by_factory():
    def get_jang(_) -> Jang:
        return Jang(None)

    container = Container()
    container.add_exact_transient(Jing)
    container.add_transient_by_factory(get_jang)

    provider = container.build_provider()

    jing = provider.get(Jing)
    assert jing is not None
    assert isinstance(jing.jang, Jang)
    assert jing.jang.jing is None


def test_add_instance_allows_for_circular_classes():
    container = Container()
    container.add_instance(Circle(Circle(None)))

    # NB: in this example, Shape requires a Circle
    container.add_exact_transient(Shape)
    provider = container.build_provider()

    circle = provider.get(Circle)
    assert isinstance(circle, Circle)

    shape = provider.get(Shape)

    assert isinstance(shape, Shape)
    assert shape.circle is circle


def test_add_instance_with_declared_type():
    container = Container()
    container.add_instance(Circle(Circle(None)), declared_class=ICircle)
    provider = container.build_provider()

    icircle = provider.get(ICircle)
    assert isinstance(icircle, Circle)


def test_raises_for_optional_parameter():
    container = Container()
    container.add_exact_transient(Foo)
    container.add_exact_transient(TypeWithOptional)

    with pytest.raises(UnsupportedUnionTypeException) as context:
        container.build_provider()

    assert 'foo' in str(context.value)


def test_raises_for_nested_circular_dependency():
    container = Container()
    container.add_transient(ICircle, Circle)
    container.add_exact_transient(TrickyCircle)

    with pytest.raises(CircularDependencyException) as context:
        container.build_provider()

    assert 'Circle' in str(context.value)


def test_interdependencies():
    container = Container()
    container.add_exact_transient(A)
    container.add_exact_transient(B)
    container.add_exact_transient(C)
    container.add_exact_transient(IdGetter)
    provider = container.build_provider()

    c = provider.get(C)

    assert isinstance(c, C)
    assert isinstance(c.a, A)
    assert isinstance(c.b, B)
    assert isinstance(c.b.a, A)


def test_transient_service():
    container = Container()
    container.add_transient(ICatsRepository, InMemoryCatsRepository)
    provider = container.build_provider()

    cats_repo = provider.get(ICatsRepository)
    assert isinstance(cats_repo, InMemoryCatsRepository)

    other_cats_repo = provider.get(ICatsRepository)
    assert cats_repo is not other_cats_repo


def test_singleton_services():
    container = Container()
    container.add_exact_singleton(IdGetter)
    provider = container.build_provider()

    with GetServiceContext() as context:
        a = provider.get(IdGetter, context)
        b = provider.get(IdGetter, context)
        c = provider.get(IdGetter, context)
    d = provider.get(IdGetter)

    assert a is b
    assert a is c
    assert b is c
    assert d is a


def test_transient_services():
    container = Container()
    container.add_exact_transient(IdGetter)
    provider = container.build_provider()

    with GetServiceContext() as context:
        a = provider.get(IdGetter, context)
        b = provider.get(IdGetter, context)
        c = provider.get(IdGetter, context)
    d = provider.get(IdGetter)

    assert a is not b
    assert a is not c
    assert b is not c
    assert d is not a
    assert d is not b
    assert d is not c


def test_scoped_services():
    container = Container()
    container.add_exact_scoped(IdGetter)
    provider = container.build_provider()

    with GetServiceContext() as context:
        a = provider.get(IdGetter, context)
        b = provider.get(IdGetter, context)
        c = provider.get(IdGetter, context)
    d = provider.get(IdGetter)

    assert a is b
    assert b is c
    assert a is not d
    assert b is not d


def test_resolution_by_parameter_name():
    container = Container()
    container.add_transient(ICatsRepository, InMemoryCatsRepository)
    container.add_exact_transient(ResolveThisByParameterName)

    provider = container.build_provider()
    resolved = provider.get(ResolveThisByParameterName)

    assert resolved is not None

    assert isinstance(resolved, ResolveThisByParameterName)
    assert isinstance(resolved.cats_repository, InMemoryCatsRepository)


def test_resolve_singleton_by_parameter_name():
    container = Container()
    container.add_transient(IByParamName, FooByParamName)

    singleton = Foo()
    container.add_instance(singleton)

    provider = container.build_provider()
    resolved = provider.get(IByParamName)

    assert resolved is not None

    assert isinstance(resolved, FooByParamName)
    assert resolved.foo is singleton


def test_service_collection_contains():
    container = Container()
    container.add_exact_transient(Foo)

    assert Foo in container
    assert Cat not in container


def test_service_provider_contains():
    container = Container()
    container.add_exact_transient(IdGetter)

    provider = container.build_provider()

    assert Foo not in provider
    assert IdGetter in provider


def test_exact_alias():
    container = arrange_cats_example()

    class UsingAlias:

        def __init__(self, example):
            self.cats_controller = example

    container.add_exact_transient(UsingAlias)

    # arrange an exact alias for UsingAlias class init parameter:
    container.set_alias('example', CatsController)

    provider = container.build_provider()
    u = provider.get(UsingAlias)

    assert isinstance(u, UsingAlias)
    assert isinstance(u.cats_controller, CatsController)
    assert isinstance(u.cats_controller.cat_request_handler, GetCatRequestHandler)


def test_additional_alias():
    container = arrange_cats_example()

    class UsingAlias:

        def __init__(self, example, settings):
            self.cats_controller = example
            self.settings = settings

    class AnotherUsingAlias:

        def __init__(self, cats_controller, service_settings):
            self.cats_controller = cats_controller
            self.settings = service_settings

    container.add_exact_transient(UsingAlias)
    container.add_exact_transient(AnotherUsingAlias)

    # arrange an exact alias for UsingAlias class init parameter:
    container.add_alias('example', CatsController)
    container.add_alias('settings', ServiceSettings)

    provider = container.build_provider()
    u = provider.get(UsingAlias)

    assert isinstance(u, UsingAlias)
    assert isinstance(u.settings, ServiceSettings)
    assert isinstance(u.cats_controller, CatsController)
    assert isinstance(u.cats_controller.cat_request_handler, GetCatRequestHandler)

    u = provider.get(AnotherUsingAlias)

    assert isinstance(u, AnotherUsingAlias)
    assert isinstance(u.settings, ServiceSettings)
    assert isinstance(u.cats_controller, CatsController)
    assert isinstance(u.cats_controller.cat_request_handler, GetCatRequestHandler)


def test_get_service_by_name_or_alias():
    container = arrange_cats_example()
    container.add_alias('k', CatsController)

    provider = container.build_provider()

    for name in {'CatsController', 'cats_controller', 'k'}:
        service = provider.get(name)

        assert isinstance(service, CatsController)
        assert isinstance(service.cat_request_handler, GetCatRequestHandler)
        assert isinstance(service.cat_request_handler.repo, FooDBCatsRepository)


def test_missing_service_returns_none():
    container = Container()
    provider = container.build_provider()
    service = provider.get('not_existing')
    assert service is None


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_by_factory_type_annotation(method_name):
    container = Container()

    def factory(_) -> Cat:
        return Cat('Celine')

    method = getattr(container, method_name)

    method(factory)

    provider = container.build_provider()

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == 'Celine'

    if method_name == 'add_singleton_by_factory':
        cat_2 = provider.get(Cat)
        assert cat_2 is cat

    if method_name == 'add_transient_by_factory':
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat

    if method_name == 'add_scoped_by_factory':
        with GetServiceContext() as context:
            cat_2 = provider.get(Cat, context)
            assert cat_2 is not cat

            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_add_singleton_by_factory_given_type(method_name):
    container = Container()

    def factory(a):
        return Cat('Celine')

    method = getattr(container, method_name)

    method(factory, Cat)

    provider = container.build_provider()

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == 'Celine'

    if method_name == 'add_singleton_by_factory':
        cat_2 = provider.get(Cat)
        assert cat_2 is cat

    if method_name == 'add_transient_by_factory':
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat
        assert provider.get(Cat) is not cat

    if method_name == 'add_scoped_by_factory':
        with GetServiceContext() as context:
            cat_2 = provider.get(Cat, context)
            assert cat_2 is not cat

            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2
            assert provider.get(Cat, context) is cat_2


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_add_singleton_by_factory_raises_for_missing_type(method_name):
    container = Container()

    def factory(_):
        return Cat('Celine')

    method = getattr(container, method_name)

    with pytest.raises(MissingTypeException):
        method(factory)


def test_singleton_by_provider():
    container = Container()
    container.add_exact_singleton(P)
    container.add_exact_transient(R)

    provider = container.build_provider()

    p = provider.get(P)
    r = provider.get(R)

    assert p is not None
    assert r is not None
    assert r.p is p


def test_singleton_by_provider_both_singletons():
    container = Container()
    container.add_exact_singleton(P)
    container.add_exact_singleton(R)

    provider = container.build_provider()

    p = provider.get(P)
    r = provider.get(R)

    assert p is not None
    assert r is not None
    assert r.p is p

    r_2 = provider.get(R)
    assert r_2 is r


def test_type_hints_precedence():
    container = Container()
    container.add_exact_transient(PrecedenceOfTypeHintsOverNames)
    container.add_exact_transient(Foo)
    container.add_exact_transient(Q)
    container.add_exact_transient(P)
    container.add_exact_transient(Ko)
    container.add_exact_transient(Ok)

    provider = container.build_provider()

    service = provider.get(PrecedenceOfTypeHintsOverNames)

    assert isinstance(service, PrecedenceOfTypeHintsOverNames)
    assert isinstance(service.q, Q)
    assert isinstance(service.p, P)


def test_proper_handling_of_inheritance():
    container = Container()
    container.add_exact_transient(UfoOne)
    container.add_exact_transient(UfoTwo)
    container.add_exact_transient(UfoThree)
    container.add_exact_transient(UfoFour)
    container.add_exact_transient(Foo)

    provider = container.build_provider()

    ufo_one = provider.get(UfoOne)
    ufo_two = provider.get(UfoTwo)
    ufo_three = provider.get(UfoThree)
    ufo_four = provider.get(UfoFour)

    assert isinstance(ufo_one, UfoOne)
    assert isinstance(ufo_two, UfoTwo)
    assert isinstance(ufo_three, UfoThree)
    assert isinstance(ufo_four, UfoFour)


@pytest.mark.parametrize('method_name', [
    'add_singleton_by_factory',
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_by_factory_with_different_parameters(method_name):

    for option in {0, 1, 2}:
        container = Container()

        if option == 0:
            def factory() -> Cat:
                return Cat('Celine')

        if option == 1:
            def factory(context) -> Cat:
                assert isinstance(context, Services)
                return Cat('Celine')

        if option == 2:
            def factory(context, activating_type) -> Cat:
                assert isinstance(context, Services)
                assert activating_type is Cat
                return Cat('Celine')

        method = getattr(container, method_name)
        method(factory)

        provider = container.build_provider()

        cat = provider.get(Cat)

        assert cat is not None
        assert cat.name == 'Celine'


@pytest.mark.parametrize('method_name', [
    'add_transient_by_factory',
    'add_scoped_by_factory'
])
def test_factory_can_receive_activating_type_as_parameter(method_name):

    class Logger:
        def __init__(self, name):
            self.name = name

    class HelpController:
        def __init__(self, logger: Logger):
            self.logger = logger

    class HomeController:
        def __init__(self, logger: Logger):
            self.logger = logger

    class FooController:
        def __init__(self, foo: Foo, logger: Logger):
            self.foo = foo
            self.logger = logger

    container = Container()
    container.add_exact_transient(Foo)

    def factory(_, activating_type) -> Logger:
        return Logger(activating_type.__module__ + '.' + activating_type.__name__)

    method = getattr(container, method_name)
    method(factory)

    container\
        .add_exact_transient(HelpController)\
        .add_exact_transient(HomeController)\
        .add_exact_transient(FooController)

    provider = container.build_provider()

    help_controller = provider.get(HelpController)

    assert help_controller is not None
    assert help_controller.logger is not None
    assert help_controller.logger.name == 'rodi.tests.test_services.HelpController'

    home_controller = provider.get(HomeController)

    assert home_controller is not None
    assert home_controller.logger is not None
    assert home_controller.logger.name == 'rodi.tests.test_services.HomeController'

    foo_controller = provider.get(FooController)

    assert foo_controller is not None
    assert foo_controller.logger is not None
    assert foo_controller.logger.name == 'rodi.tests.test_services.FooController'


def test_factory_can_receive_activating_type_as_parameter_nested_resolution():
    # NB: this scenario can only work when a class is registered as transient service

    class Logger:
        def __init__(self, name):
            self.name = name

    class HelpRepo:
        def __init__(self, logger: Logger):
            self.logger = logger

    class HelpHandler:
        def __init__(self, help_repo: HelpRepo):
            self.repo = help_repo

    class HelpController:
        def __init__(self, logger: Logger, handler: HelpHandler):
            self.logger = logger
            self.handler = handler

    container = Container()

    def factory(_, activating_type) -> Logger:
        # NB: this scenario is tested for rolog library
        return Logger(activating_type.__module__ + '.' + activating_type.__name__)

    container.add_transient_by_factory(factory)

    for service_type in {HelpRepo, HelpHandler, HelpController}:
        container.add_exact_transient(service_type)

    provider = container.build_provider()

    help_controller = provider.get(HelpController)

    assert help_controller is not None
    assert help_controller.logger is not None
    assert help_controller.logger.name == 'rodi.tests.test_services.HelpController'
    assert help_controller.handler.repo.logger.name == 'rodi.tests.test_services.HelpRepo'


def test_factory_can_receive_activating_type_as_parameter_nested_resolution_many():
    # NB: this scenario can only work when a class is registered as transient service

    class Logger:
        def __init__(self, name):
            self.name = name

    class HelpRepo:
        def __init__(self, db_context: FooDBContext, logger: Logger):
            self.db_context = db_context
            self.logger = logger

    class HelpHandler:
        def __init__(self, help_repo: HelpRepo):
            self.repo = help_repo

    class AnotherPathTwo:
        def __init__(self, logger: Logger):
            self.logger = logger

    class AnotherPath:
        def __init__(self, another_path_2: AnotherPathTwo):
            self.child = another_path_2

    class HelpController:
        def __init__(self, handler: HelpHandler, another_path: AnotherPath, logger: Logger):
            self.logger = logger
            self.handler = handler
            self.other = another_path

    container = Container()

    def factory(_, activating_type) -> Logger:
        # NB: this scenario is tested for rolog library
        return Logger(activating_type.__module__ + '.' + activating_type.__name__)

    container.add_transient_by_factory(factory)

    container.add_instance(ServiceSettings('foo:foo'))

    for service_type in {HelpRepo, HelpHandler, HelpController, AnotherPath, AnotherPathTwo, Foo, FooDBContext}:
        container.add_exact_transient(service_type)

    provider = container.build_provider()

    help_controller = provider.get(HelpController)

    assert help_controller is not None
    assert help_controller.logger is not None
    assert help_controller.logger.name == 'rodi.tests.test_services.HelpController'
    assert help_controller.handler.repo.logger.name == 'rodi.tests.test_services.HelpRepo'
    assert help_controller.other.child.logger.name == 'rodi.tests.test_services.AnotherPathTwo'


def test_service_provider_supports_set_by_class():
    provider = Services()

    singleton_cat = Cat('Celine')

    provider.set(Cat, singleton_cat)

    cat = provider.get(Cat)

    assert cat is not None
    assert cat.name == "Celine"

    cat = provider.get('Cat')

    assert cat is not None
    assert cat.name == "Celine"


def test_service_provider_supports_set_by_name():
    provider = Services()

    singleton_cat = Cat('Celine')

    provider.set('my_cat', singleton_cat)

    cat = provider.get('my_cat')

    assert cat is not None
    assert cat.name == "Celine"


def test_service_provider_supports_set_and_get_item_by_class():
    provider = Services()

    singleton_cat = Cat('Celine')

    provider[Cat] = singleton_cat

    cat = provider[Cat]

    assert cat is not None
    assert cat.name == "Celine"

    cat = provider['Cat']

    assert cat is not None
    assert cat.name == "Celine"


def test_service_provider_supports_set_and_get_item_by_name():
    provider = Services()

    singleton_cat = Cat('Celine')

    provider['my_cat'] = singleton_cat

    cat = provider['my_cat']

    assert cat is not None
    assert cat.name == "Celine"


def test_service_provider_supports_set_simple_values():
    provider = Services()

    provider['one'] = 10
    provider['two'] = 12
    provider['three'] = 16

    assert provider['one'] == 10
    assert provider['two'] == 12
    assert provider['three'] == 16