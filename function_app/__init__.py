import azure.functions as func
from .HttpExample import HttpExample
from .GmailAuth import GmailAuth

def main(req: func.HttpRequest) -> func.HttpResponse:
    route = req.route_params.get('route')
    if route == 'GmailAuth':
        return GmailAuth(req)
    elif route == 'HttpExample':
        return HttpExample(req)
    else:
        return func.HttpResponse("Route not found", status_code=404)