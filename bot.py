import discord
from discord.ext import commands
import asyncpg
import asyncio

from utils import overwrites

import os
from os.path import join, dirname
import dotenv
import logging
import jishaku

path = join(dirname(__file__), 'bot_stuff.env')
dotenv.load_dotenv(path)

class Kono(commands.Bot):

    def __init__(self, token, **kwargs):
        super().__init__(
            command_prefix=kwargs.pop('prefix'), case_insensitive=True,
            status=kwargs.pop('status'), chunk_guilds_at_startup=False, 
            intents=kwargs.pop('intents'), **kwargs,
        ) 
        self.token = token
        self.database = kwargs.pop('db')
        self.database_user = kwargs.pop('db_user')
        self.database_pass = kwargs.pop('db_pass')

        cogs = (
            'useful', 'nospam',
        )

        logging.basicConfig(level=logging.DEBUG)

        for cog in cogs:
            self.load_extension(f'cogs.{cog}')
        self.load_extension('jishaku')

    async def on_message_edit(self, before, after):   
        """copied"""
        if before.author.id == self.owner_id:
            await self.process_commands(after)

    async def on_ready(self):
        
        print('let\'s get rollin')

    def run(self):
        try:
            self.db_pool = self.loop.run_until_complete(
                asyncpg.create_pool(database=self.database,
                                    user=self.database_user,
                                    password=self.database_pass
                )
            )
        except:
            print('failed to connect to database')

        super().run(self.token, reconnect=True)

intents = discord.Intents.default()
intents.voice_states = False
intents.typing = False

kwargs = {
    'status': discord.Status.idle, 'intents': intents,
    'prefix': 'kono ', 'db': os.environ.get('DB'),
    'db_user': os.environ.get('DB_USER'), 'db_pass': os.environ.get('DB_PASS'),
}

Kono(os.environ.get('TOKEN'), **kwargs).run()
