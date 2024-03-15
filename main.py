import asyncio
from loguru import logger
import questionary
import sys

from utils.launch import run_check_balance, start_tasks
from utils.utils import get_wallets
from utils.modules import *


submenus = {
    'start-menu': [
        questionary.Choice('🚀 Custom Module Routes', 'custom-routes'),
        questionary.Choice('✨ One Selected Module', 'one_selected_module'),
        questionary.Choice('📥 OKX Balance Modules', 'okx-modules'),
        questionary.Choice('💼 Base Balance Checker', 'balance-checker'),
        questionary.Choice('❌ Exit', 'exit'),
    ],
    'one_selected_module': [
        questionary.Choice('● Swap on 1inch', swap_inch),
        questionary.Choice('● Swap on UniSwap', swap_uniswap),
        questionary.Choice('● Deposit on Aave', deposit_aave),
        questionary.Choice('● Wrap ETH', wrap_eth),
        questionary.Choice('● Sending mail via DMail', send_mail),
        questionary.Choice('● Mint NFTs2Me', nfts2me_mint),
        questionary.Choice('● Vote on RubyScore', rubyscore_vote),
        questionary.Choice('● Daily check in on OwlTo', owlto_checkin),
        questionary.Choice('● Increase allowance token', increase_allowance),
        questionary.Choice('● Approve token', approve),
        questionary.Choice('● Transfer token', transfer),
    ],
    'okx_modules': [
        questionary.Choice('● OKX Withdraw', okx_withdraw),
        questionary.Choice('● OKX Top Up', okx_top_up),
    ]
}

def show_submenu(selected_mode):
    submenu = submenus[selected_mode]
    module = questionary.select(
        message='Choose the desired module.',
        choices=submenu,
        qmark='📌 ',
        pointer='➡️ '
    ).ask()

    return module

def main():
    selected_mode = questionary.select(
        message='Select a mode to start the software.',
        choices=submenus['start-menu'],
        qmark='📌 ',
        pointer='➡️ '
    ).ask()
    
    data = get_wallets()
    
    if selected_mode in submenus: selected_mode = show_submenu(selected_mode)
    elif selected_mode == 'balance-checker': asyncio.run(run_check_balance(data))
    elif selected_mode == 'exit': sys.exit()
    else: asyncio.run(start_tasks(data, None))

if __name__ == '__main__':
    logger.add('logs.log')
    main()