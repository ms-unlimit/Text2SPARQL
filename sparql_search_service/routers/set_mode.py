import json
from pydantic import BaseModel
from fastapi import APIRouter, Response
from sparql_utils import initializer


class SetMode(BaseModel):
	mode: dict

router = APIRouter()

@router.post('/mode')
def set_mode(request: SetMode):

	try:
		initializer.update_mode(request.mode)
		result, status_code = "success", 200

	except:
		result, status_code = "failed", 401

	return Response(
		content=json.dumps(result),
		status_code=status_code,
		media_type="application/json")
