"""Greeting FastAPI router"""
from http import HTTPStatus
import logging

from fastapi import APIRouter

from flex_container_orchestrator.services import greeting_service
from flex_container_orchestrator.domain.greeting import Greeting

router = APIRouter()
_LOGGER = logging.getLogger(__name__)


@router.get('/greeting/{name}', status_code=HTTPStatus.OK)
def get_greeting(name: str) -> Greeting:
    return greeting_service.get_greeting(name)
