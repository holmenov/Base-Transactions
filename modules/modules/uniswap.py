import time

from modules.account import Account
from utils.config import (
    UNISWAP_CONTRACTS, BASE_TOKENS, UNISWAP_FACTORY_ABI, UNISWAP_QUOTER_ABI, UNISWAP_ROUTER_ABI, ZERO_ADDRESS
)
from settings import MainSettings as SETTINGS
from utils.utils import async_sleep
from utils.wrappers import check_gas


class UniSwap(Account):
    def __init__(self, account_id: int, private_key: str, proxy: str | None) -> None:
        super().__init__(account_id, private_key, proxy)
        
        self.uniswap_contract = self.get_contract(UNISWAP_CONTRACTS["router"], UNISWAP_ROUTER_ABI)
    
    async def get_pool(self, from_token: str, to_token: str):
        factory = self.get_contract(UNISWAP_CONTRACTS["factory"], UNISWAP_FACTORY_ABI)

        pool = await factory.functions.getPool(
            self.w3.to_checksum_address(BASE_TOKENS[from_token]),
            self.w3.to_checksum_address(BASE_TOKENS[to_token]),
            500
        ).call()

        return pool

    async def get_min_amount_out(self, from_token: str, to_token: str, amount: int):
        quoter = self.get_contract(UNISWAP_CONTRACTS["quoter"], UNISWAP_QUOTER_ABI)

        quoter_data = await quoter.functions.quoteExactInputSingle((
            self.w3.to_checksum_address(BASE_TOKENS[from_token]),
            self.w3.to_checksum_address(BASE_TOKENS[to_token]),
            amount,
            500,
            0
        )).call()
        
        return int(quoter_data[0] - (quoter_data[0] / 100 * SETTINGS.SLIPPAGE))
    
    async def swap_to_token(self, from_token: str, to_token: str, amount_wei: int):
        tx_data = await self.get_tx_data(value=amount_wei)

        deadline = int(time.time()) + 1000000

        min_amount_out = await self.get_min_amount_out(from_token, to_token, amount_wei)

        transaction_data = self.uniswap_contract.encodeABI(
            fn_name="exactInputSingle",
            args=[(
                self.w3.to_checksum_address(BASE_TOKENS[from_token]),
                self.w3.to_checksum_address(BASE_TOKENS[to_token]),
                500,
                self.address,
                amount_wei,
                min_amount_out,
                0
            )]
        )

        contract_txn = await self.uniswap_contract.functions.multicall(
            deadline, [transaction_data]
        ).build_transaction(tx_data)

        return contract_txn
    
    async def swap_to_eth(self, from_token: str, to_token: str, amount_wei: int):
        await self.approve(amount_wei, BASE_TOKENS[from_token], UNISWAP_CONTRACTS["router"])

        tx_data = await self.get_tx_data()

        deadline = int(time.time()) + 1000000

        min_amount_out = await self.get_min_amount_out(from_token, to_token, amount_wei)

        transaction_data = self.uniswap_contract.encodeABI(
            fn_name="exactInputSingle",
            args=[(
                self.w3.to_checksum_address(BASE_TOKENS[from_token]),
                self.w3.to_checksum_address(BASE_TOKENS[to_token]),
                500,
                "0x0000000000000000000000000000000000000002",
                amount_wei,
                min_amount_out,
                0
            )]
        )

        unwrap_data = self.uniswap_contract.encodeABI(
            fn_name="unwrapWETH9",
            args=[min_amount_out, self.address]
        )

        contract_txn = await self.uniswap_contract.functions.multicall(
            deadline, [transaction_data, unwrap_data]
        ).build_transaction(tx_data)

        return contract_txn

    @check_gas
    async def swap(
        self,
        from_token: str,
        to_token: str,
        min_amount: float,
        max_amount: float,
        decimal: int,
        all_amount: bool,
        min_percent: int,
        max_percent: int,
        swap_reverse: bool
    ):
        self.log_send(f'{from_token} -> {to_token} | Swap on UniSwap.')

        if all_amount:
            amount_wei, _ = await self.get_percent_amount(from_token, min_percent, max_percent)
        else:
            amount_wei, _ = await self.get_random_amount(from_token, min_amount, max_amount, decimal)
        
        pool = await self.get_pool(from_token, to_token)
        
        if pool != ZERO_ADDRESS:
            if from_token == "ETH":
                contract_txn = await self.swap_to_token(from_token, to_token, amount_wei)
            else:
                contract_txn = await self.swap_to_eth(from_token, to_token, amount_wei)

            await self.execute_transaction(contract_txn)
            
            if swap_reverse:
                await async_sleep(5, 15, logs=False)
                await self.swap(to_token, from_token, 0.01, 0.01, decimal, True, 100, 100, False)

        else:
            self.log_send(f'Swap path on UniSwap {from_token} to {to_token} not found!', status='error')