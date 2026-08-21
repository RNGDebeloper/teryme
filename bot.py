#@(Uchiha_Developer)

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
import sys
from datetime import datetime

from commands import ADMIN_COMMANDS, COMMAND_GROUPS, USER_COMMANDS
from config import API_HASH, APP_ID, ADMINS, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, CHANNEL_ID, PORT

_DESCRIPTIONS = {cmd: desc for _, cmds in COMMAND_GROUPS for cmd, desc, _ in cmds}


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER
        self._invite_link_cache = {}

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        if FORCE_SUB_CHANNEL:
            # Sanity-check only. The actual invite link shown to users is
            # resolved dynamically (and cached) in helper_func, so a bad
            # value here is a warning, not a reason to refuse to start —
            # admins can still fix it live with /set_force_sub.
            try:
                await self.get_chat(FORCE_SUB_CHANNEL)
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning(
                    "Bot can't access the configured FORCE_SUB_CHANNEL yet. Make sure the bot "
                    "is an admin there with 'Invite Users via Link' permission, or fix it via "
                    f"/set_force_sub. Current FORCE_SUB_CHANNEL value: {FORCE_SUB_CHANNEL}"
                )
        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(chat_id = db_channel.id, text = "Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}")
            self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/Uchiha_Developer for support")
            sys.exit()

        await self._register_bot_commands()

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/Uchiha_Developer")
        self.LOGGER(__name__).info(f""" \n\n       
░█████╗░░█████╗░██████╗░███████╗██╗░░██╗██████╗░░█████╗░████████╗███████╗
██╔══██╗██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝╚════██║
██║░░╚═╝██║░░██║██║░░██║█████╗░░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░░░███╔═╝
██║░░██╗██║░░██║██║░░██║██╔══╝░░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░██╔══╝░░
╚█████╔╝╚█████╔╝██████╔╝███████╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░███████╗
░╚════╝░░╚════╝░╚═════╝░╚══════╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░╚══════╝
                                          """)
        self.username = usr_bot_me.username
        #web-response
        web_app = await web_server()
        web_app["bot_username"] = self.username
        app = web.AppRunner(web_app)
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

    async def _register_bot_commands(self) -> None:
        """Populate Telegram's native '/' command menu so every feature is
        discoverable from inside the chat, without leaking admin-only
        commands to regular users."""
        try:
            user_cmds = [BotCommand(cmd, _DESCRIPTIONS.get(cmd, cmd)[:256]) for cmd in USER_COMMANDS]
            await self.set_bot_commands(user_cmds, scope=BotCommandScopeDefault())
        except Exception as e:
            self.LOGGER(__name__).warning(f"Couldn't set default bot commands: {e}")

        admin_cmds = [
            BotCommand(cmd, _DESCRIPTIONS.get(cmd, cmd)[:256]) for cmd in USER_COMMANDS + ADMIN_COMMANDS
        ]
        for admin_id in ADMINS:
            try:
                await self.set_bot_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=admin_id))
            except Exception:
                # Telegram requires the user to have started a chat with the
                # bot before a per-chat command scope can be set — harmless
                # to skip for admins who haven't messaged the bot yet.
                pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")
