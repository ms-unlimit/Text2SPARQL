import json
from pydantic import BaseModel
from fastapi import APIRouter, Response
from sparql_utils import initializer


class GetQuery(BaseModel):
	query_text: str

router = APIRouter()

@router.post('/query')
def get_query(request: GetQuery):

	result = initializer.query_handler.runQuery(query_text=request.query_text)
	status_code = 200 if len(result['answer']) >= 0  else 501

	return Response(
		content=json.dumps(result),
		status_code=status_code,
		media_type="application/json")
