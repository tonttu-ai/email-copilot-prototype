from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

# Setup the client
kv_url = os.environ.get("KEYVAULT_URL")  # Ensure this environment variable is set in your function settings
credential = DefaultAzureCredential()
client = SecretClient(vault_url=kv_url, credential=credential)

# Retrieve secrets
gmail_client_id = client.get_secret("GmailClientId").value
gmail_client_secret = client.get_secret("GmailClientSecret").value
