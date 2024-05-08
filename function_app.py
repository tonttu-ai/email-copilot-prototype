import azure.functions as func
from HttpExample import HttpExample
from GmailAuth import GmailAuth
from blueprint import Blueprint

app = func.FunctionApp() 

app.register_functions(Blueprint) 
app.register_functions(HttpExample)
app.register_functions(GmailAuth)

@app.function_name(name="HttpTrigger1")
@app.route(route="req")
def main(req):
    user = req.params.get("user")
    return f"Hello, {user}!"