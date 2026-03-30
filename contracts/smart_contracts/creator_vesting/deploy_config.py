import logging

import algokit_utils

logger = logging.getLogger(__name__)


def deploy() -> None:
    from smart_contracts.artifacts.creator_vesting.creator_vesting_client import (
        CreatorVestingFactory,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")

    logger.info("Deploying CreatorVesting from account: %s", deployer.address)

    factory = algorand.client.get_typed_app_factory(
        CreatorVestingFactory,
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
            "Successfully deployed CreatorVesting (App ID: %s) at %s",
            app_client.app_id,
            app_client.app_address,
        )
    else:
        logger.info(
            "CreatorVesting already deployed (App ID: %s)",
            app_client.app_id,
        )


if __name__ == "__main__":
    deploy()
