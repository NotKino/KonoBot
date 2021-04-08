import dotenv
import logging
import os

import asyncpg
import discord
import jishaku
from discord.ext import commands

from utils import modles

dotenv.load_dotenv('bot_stuff.env')


class Kono(commands.Bot):

    def __init__(self, token, **kwargs):
        super().__init__(
            command_prefix=kwargs.pop('prefix'), case_insensitive=True,
            status=kwargs.pop('status'), chunk_guilds_at_startup=False,
            intents=kwargs.pop('intents'), **kwargs,
        )
        self.token = token
        self.database, self.database_user, self.database_pass = kwargs.pop('db')

        cogs = (
            'useful', 'nospam',
            'jishaku',
        )

        logging.basicConfig(level=logging.DEBUG)

        for cog in cogs:
            path = f'cogs.{cog}' if cog != 'jishaku' else 'jishaku'
            self.load_extension(path)

    async def on_message_edit(self, before, after):
        if before.author.id == self.owner_id:
            await self.process_commands(after)

    async def on_ready(self):
        print('let\'s get rollin')

    def run(self):
        try:
            self.db_pool = self.loop.run_until_complete(
                asyncpg.create_pool(database=self.database,
                                    user=self.database_user,
                                    password=self.database_pass,
                                    )
            )
        except ConnectionRefusedError:
            print('failed to connect to database')

        super().run(self.token)


intents = discord.Intents.default()
intents.voice_states = False
intents.typing = False
intents.members = True

kwargs = {
    'status': discord.Status.idle, 'intents': intents, 'prefix': 'kono ',
    'db': (os.environ.get('DB'), os.environ.get('DB_USER'), os.environ.get('DB_PASS'))
}

Kono(os.environ.get('TOKEN'), **kwargs).run()
