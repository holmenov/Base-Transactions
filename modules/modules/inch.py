import aiohttp

from modules.account import Account
from settings import MainSettings as SETTINGS
from utils.config import BASE_TOKENS, INCH_CONTRACT
from utils.utils import async_sleep
from utils.wrappers import check_gas


class Inch(Account):
    def __init__(self, account_id: int, private_key: str, proxy: str | None, api_key: str) -> None:
        super().__init__(account_id, private_key, proxy)
        
        self.headers = {"Authorization": f"Bearer {api_key}", "accept": "application/json"}
    
    async def build_tx(self, from_token_addr: str, to_token_addr: str, amount: int):
        url = f"https://api.1inch.dev/swap/v5.2/{await self.w3.eth.chain_id}/swap"
        
        params = {
            "src": self.w3.to_checksum_address(from_token_addr),
            "dst": self.w3.to_checksum_address(to_token_addr),
            "amount": amount,
            "from": self.address,
            "slippage": SETTINGS.SLIPPAGE,
        }
        
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, params=params, headers=self.headers)
            
            transaction_data = await response.json()

            return transaction_data
    
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
        swap_reverse: bool,
    ):
        self.log_send(f'{from_token} -> {to_token} | Swap on 1inch.')

        if all_amount:
            amount_wei, _ = await self.get_percent_amount(from_token, min_percent, max_percent)
        else:
            amount_wei, _ = await self.get_random_amount(from_token, min_amount, max_amount, decimal)
        
        from_token_addr = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE' if from_token == 'ETH' else BASE_TOKENS[from_token]
        to_token_addr = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE' if to_token == 'ETH' else BASE_TOKENS[to_token]
        
        transaction_data = await self.build_tx(from_token_addr, to_token_addr, amount_wei)
        
        if from_token != 'ETH':
            await self.approve(amount_wei, from_token, INCH_CONTRACT['router'])
        
        tx = await self.get_tx_data()
        
        tx.update(
            {
                "to": self.w3.to_checksum_address(transaction_data["tx"]["to"]),
                "data": transaction_data["tx"]["data"],
                "value": int(transaction_data["tx"]["value"]),
            }
        )
        
        await self.execute_transaction(tx)
        
        if swap_reverse:
            await async_sleep(5, 15, logs=False)
            await self.swap(to_token, from_token, 0.01, 0.01, decimal, True, 100, 100, False)
        
        