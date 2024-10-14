from http import HTTPStatus


def test_get(test_client):
    # given
    name = 'MeteoSwiss'

    # when
    response = test_client.get(f'/flex-container-orchestrator/api/v1/greeting/{name}')

    # then
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': f'Hello, {name} from flex-container-orchestrator!'}
