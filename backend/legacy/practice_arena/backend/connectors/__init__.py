from .aws_conn import AwsConnector
from .azure_conn import AzureConnector


_CONNECTORS = {
    "aws": AwsConnector(),
    "azure": AzureConnector(),
}


def get_connector(provider):
    return _CONNECTORS.get(provider)
