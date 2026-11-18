import time,uuid,logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class RequestTrace(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        rid=uuid.uuid4().hex[:12];start=time.time()
        response=await call_next(request);response.headers['X-Request-ID']=rid
        logging.info('%s %s %s %.3fs',rid,request.method,request.url.path,time.time()-start)
        return response
class Recovery(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        try:return await call_next(request)
        except Exception:
            logging.exception('Unhandled request')
            return JSONResponse({'detail':'操作失败，数据未提交；请检查输入后重试'},status_code=500)
