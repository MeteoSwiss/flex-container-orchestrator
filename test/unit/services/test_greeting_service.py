from flex_container_orchestrator import CONFIG
from flex_container_orchestrator.services import greeting_service
from flex_container_orchestrator.domain.greeting import Greeting

def test_greeting_service():
    # given
    name = 'World'
    CONFIG.main.app_name = 'the test app'

    # when
    result = greeting_service.get_greeting(name)

    expected = Greeting(message=f'Hello, {name} from the test app!')

    # then
    assert result == expected