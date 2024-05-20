import os
import logging
from google_auth_oauthlib.flow import Flow
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import azure.functions as func
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from azure.cosmos import CosmosClient, PartitionKey
import azure.functions as func
import openai

# Environment variables
GOOGLE_AUTH_URI = os.getenv('GOOGLE_AUTH_URI')
GOOGLE_TOKEN_URI = os.getenv('GOOGLE_TOKEN_URI')
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
COSMOS_DB_URI = os.getenv('COSMOS_DB_URI')
COSMOS_DB_KEY = os.getenv('COSMOS_DB_KEY')
COSMOS_DB_NAME = 'EmailDatabase'
COSMOS_DB_CONTAINER = 'Emails'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
KV_URL = os.environ["KEYVAULT_URL"]
openai.api_key = OPENAI_API_KEY

# register the function app
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# initialize the oauth flow
def oauth_flow():
    # Load client ID and secret from Key Vault
    kv_url = KV_URL
    client = SecretClient(vault_url=kv_url, credential=DefaultAzureCredential())
    client_id = client.get_secret("GmailClientId").value
    client_secret = client.get_secret("GmailClientSecret").value

    flow = InstalledAppFlow.from_client_config(
        client_config={
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
                "redirect_uris": ["https://email-copilot-prototype-app.azurewebsites.net/api/GmailAuth"],
            }
        },
        scopes=SCOPES,
        redirect_uri="https://email-copilot-prototype-app.azurewebsites.net/api/GmailAuth"
    )
    credentials = flow.run_local_server(port=0)
    return credentials

# get the emails using the credentials
def get_emails(credentials):
    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(userId='me').execute()
    messages = results.get('messages', [])

    emails = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        emails.append(msg)

    return emails

# store the email content in Cosmos DB
def store_email_content(email_data):
    client = CosmosClient(COSMOS_DB_URI, COSMOS_DB_KEY)
    database = client.create_database_if_not_exists(id=COSMOS_DB_NAME)
    container = database.create_container_if_not_exists(
        id=COSMOS_DB_CONTAINER,
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400
    )
    container.create_item(body=email_data)

# summarize the email content using OpenAI
def summarize_email(email):
    response = openai.Completion.create(
        model="text-davinci-003", # adjust this based on the desired model
        prompt=f"Summarize this email: {email['body']}",
        max_tokens=150 # adjust this based on the desired summary length
    )
    return response.choices[0].text.strip()

# store the summary in Cosmos DB
def store_summary(container, summary):
    container.create_item(body={"id": str(uuid.uuid4()), "summary": summary, "timestamp": datetime.utcnow().isoformat()})


# HTTP trigger function
@app.route(route="HttpExample")
def HttpExample(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This is Sebastian's HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

# GetEmails function
@func.HttpTrigger(name="GetEmails", methods=["get"], route="get-emails")
def get_emails_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    action = req.params.get('action')
    if not action:
        return func.HttpResponse("Please specify an action.", status_code=400)

    if action == "oauth":
        credentials = oauth_flow()
        return func.HttpResponse("OAuth flow completed. You can now retrieve emails.", status_code=200)

    elif action == "get_emails":
        credentials = oauth_flow()  # This should be replaced with secure credential retrieval
        emails = get_emails(credentials)
        for email in emails:
            store_email_content(email)
        return func.HttpResponse(json.dumps(emails), mimetype="application/json")

    return func.HttpResponse("Invalid action.", status_code=400)

# Timer trigger function
# This function summarizes emails every hour
@func.TimerTrigger(name="SummarizeEmails", schedule="0 */1 * * * *")
def timer_trigger_function(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    client = CosmosClient(COSMOS_DB_URI, COSMOS_DB_KEY)
    database = client.get_database_client(COSMOS_DB_NAME)
    container = database.get_container_client(COSMOS_DB_CONTAINER)

    # Define the time period to summarize emails
    time_threshold = datetime.utcnow() - timedelta(hours=1)
    emails = container.query_items(
        query="SELECT * FROM c WHERE c.timestamp >= @time_threshold",
        parameters=[
            {"name": "@time_threshold", "value": time_threshold.isoformat()}
        ],
        enable_cross_partition_query=True
    )

    for email in emails:
        summary = summarize_email(email)
        store_summary(container, summary)


# GmailAuth function
@app.route(route="GmailAuth")  
def GmailAuth(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Gmail OAuth request.')

    # Environment variables
    kv_url = os.environ["KEYVAULT_URL"]
    client = SecretClient(vault_url=kv_url, credential=DefaultAzureCredential())

    # Load client ID and secret from Key Vault
    client_id = client.get_secret("GmailClientId").value
    client_secret = client.get_secret("GmailClientSecret").value

   # Setup the Google OAuth Flow
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["https://email-copilot-prototype-app.azurewebsites.net/api/GmailAuth"],
            }
        },
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
        redirect_uri="https://email-copilot-prototype-app.azurewebsites.net/api/GmailAuth"
    )

    # Check if this is the callback request with auth code
    code = req.params.get('code')
    if code:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        # Store the credentials securely in Key Vault
        client.set_secret("GmailToken", credentials.token)
        client.set_secret("GmailRefreshToken", credentials.refresh_token)

        return func.HttpResponse("Authentication successful", status_code=200)
    else:
        # Generate the authorization URL for the OAuth flow
        auth_url, _ = flow.authorization_url(prompt='consent')
        return func.HttpResponse(f"Redirect to: {auth_url}", status_code=302)