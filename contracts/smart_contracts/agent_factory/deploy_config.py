import logging
import algokit_utils
from algosdk import transaction
from smart_contracts.artifacts.agent_factory.agent_factory_client import (
    AgentFactoryFactory,
)

logger = logging.getLogger(__name__)

def deploy() -> None:
    # Initialize Algorand Client from environment (defaults to LocalNet, can be set to Testnet)
    algorand = algokit_utils.AlgorandClient.from_environment()
    
    # Load deployer account (e.g., from MNEMONIC in .env)
    deployer = algorand.account.from_environment("DEPLOYER")
    
    logger.info(f"Deploying AgentFactory from account: {deployer.address}")

    # Initialize the App Factory
    factory = algorand.client.get_typed_app_factory(
        AgentFactoryFactory, 
        default_sender=deployer.address
    )

    # Deploy the contract
    # We use ReplaceApp to force the new schema (LatestAssetId) onto Testnet
    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.ReplaceApp,
        on_schema_break=algokit_utils.OnSchemaBreak.ReplaceApp,
    )

    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        logger.info(f"Successfully deployed AgentFactory (App ID: {app_client.app_id}) at {app_client.app_address}")
        
        # Funding the contract with some ALGO for inner transactions (minimum 1 ALGO for start)
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer.address,
                receiver=app_client.app_address,
            )
        )
        logger.info("Funded AgentFactory with 1 ALGO for operations.")
    else:
        logger.info(f"AgentFactory already deployed (App ID: {app_client.app_id})")

if __name__ == "__main__":
    deploy()
