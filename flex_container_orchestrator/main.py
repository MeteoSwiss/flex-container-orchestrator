"""" Define application """
import os

from mchpy.web import fastapi_app
from flex_container_orchestrator.routers import greeting_router

_SERVICE_NAMESPACE = 'flex-container-orchestrator'
_URL_PREFIX = f'/{_SERVICE_NAMESPACE}/api/v1'

# Create the application instance
app = fastapi_app.create(
    title='flex-container-orchestrator',
    description='Service listening to Aviso and launching Flexpart-IFS',
    contact={
        'name': 'Nina Burgdorfer',
        'email': 'nina.burgdorfer@meteoswiss.ch',
    },
    version=os.getenv('VERSION') or '1.0.0',
    base_path=f'/{_SERVICE_NAMESPACE}',
    docs_url=f'/{_SERVICE_NAMESPACE}/swagger-ui.html',
    openapi_url=f'/{_SERVICE_NAMESPACE}/openapi.json',
    redoc_url=None,
)

# include routers
app.include_router(greeting_router.router, prefix=_URL_PREFIX)

# If we're running in standalone mode, run the application
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)
