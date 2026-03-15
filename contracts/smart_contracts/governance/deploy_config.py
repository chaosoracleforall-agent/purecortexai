import logging

import algokit_utils

logger = logging.getLogger(__name__)


def deploy() -> None:
    from smart_contracts.artifacts.governance.governance_contract_client import (
        GovernanceContractFactory,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")

    logger.info(f"Deploying GovernanceContract from account: {deployer.address}")

    factory = algorand.client.get_typed_app_factory(
        GovernanceContractFactory,
        default_sender=deployer.address,
    )

    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
    )

    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        logger.info(
            f"Successfully deployed GovernanceContract "
            f"(App ID: {app_client.app_id}) at {app_client.app_address}"
        )

        # Fund the contract with ALGO for inner transactions
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer.address,
                receiver=app_client.app_address,
            )
        )
        logger.info("Funded GovernanceContract with 1 ALGO for operations.")
    else:
        logger.info(
            f"GovernanceContract already deployed (App ID: {app_client.app_id})"
        )


if __name__ == "__main__":
    deploy()
